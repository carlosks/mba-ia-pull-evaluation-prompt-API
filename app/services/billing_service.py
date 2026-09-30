"""
Regras de cobrança: checkout, webhook, cancelamento e plano efetivo do usuário.

Fluxo:
1. O usuário escolhe um plano -> start_checkout cria (ou reaproveita) o cliente
   e a assinatura na Asaas e devolve o link da fatura (Pix, boleto ou cartão).
2. A Asaas avisa o pagamento pelo webhook -> handle_webhook ativa o plano.
3. Cada pagamento estende o acesso até o vencimento seguinte + tolerância.
4. Cancelamento ou falta de pagamento: o acesso segue até o fim do período
   pago e depois o usuário volta ao plano free (sync_user_plan).
"""

from __future__ import annotations

import calendar
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config, models
from app.services import asaas_client
from app.services.usage_service import get_plan_limit

logger = logging.getLogger("app.billing")

BR_TZ = ZoneInfo("America/Sao_Paulo")

PAID_EVENTS = {"PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"}
REVOKE_EVENTS = {"PAYMENT_REFUNDED", "PAYMENT_CHARGEBACK_REQUESTED"}
SUBSCRIPTION_END_EVENTS = {"SUBSCRIPTION_DELETED", "SUBSCRIPTION_INACTIVATED"}
ACCESS_STATUSES = ("active", "past_due", "canceled")

PLAN_NAMES = {"pro": "Pro", "team": "Team"}


# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------

def _now() -> datetime:
    """UTC sem fuso (padrão das colunas DateTime deste banco)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _add_one_month(value: date) -> date:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _period_end_from_due_date(due_date: str | None) -> datetime:
    """Fim do acesso pago: próximo vencimento + dias de tolerância."""
    try:
        due = date.fromisoformat((due_date or "")[:10])
    except ValueError:
        due = datetime.now(BR_TZ).date()

    end = _add_one_month(due) + timedelta(days=config.BILLING_GRACE_DAYS)
    # Fim do dia em Brasília, convertido para UTC sem fuso.
    end_local = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=BR_TZ)
    return end_local.astimezone(timezone.utc).replace(tzinfo=None)


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _valid_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(cpf[i]) * (size + 1 - i) for i in range(size))
        digit = (total * 10) % 11 % 10
        if digit != int(cpf[size]):
            return False
    return True


def _valid_cnpj(cnpj: str) -> bool:
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6] + weights_1
    for weights, position in ((weights_1, 12), (weights_2, 13)):
        total = sum(int(cnpj[i]) * weights[i] for i in range(len(weights)))
        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder
        if digit != int(cnpj[position]):
            return False
    return True


def valid_cpf_cnpj(value: str) -> bool:
    digits = only_digits(value)
    return _valid_cpf(digits) if len(digits) == 11 else _valid_cnpj(digits)


def plan_catalog() -> list[dict]:
    return [
        {
            "plan": "free",
            "name": "Free",
            "price": 0.0,
            "monthly_generation_limit": get_plan_limit("free"),
        },
        *[
            {
                "plan": plan,
                "name": PLAN_NAMES.get(plan, plan.title()),
                "price": price,
                "monthly_generation_limit": get_plan_limit(plan),
            }
            for plan, price in config.PLAN_PRICES.items()
        ],
    ]


def latest_subscription(db: Session, user_id: int) -> models.Subscription | None:
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == user_id)
        .order_by(models.Subscription.id.desc())
        .first()
    )


def subscription_to_dict(sub: models.Subscription | None) -> dict | None:
    if sub is None:
        return None
    return {
        "plan": sub.plan,
        "status": sub.status,
        "value": sub.value,
        "invoice_url": sub.invoice_url,
        "current_period_end": sub.current_period_end,
        "canceled_at": sub.canceled_at,
    }


# ------------------------------------------------------------
# Plano efetivo
# ------------------------------------------------------------

def _set_user_plan(user: models.User, plan: str) -> None:
    user.plan = plan
    user.monthly_generation_limit = get_plan_limit(plan)


def sync_user_plan(db: Session, user: models.User) -> None:
    """
    Alinha o plano do usuário com a assinatura:
    - período pago vigente -> plano da assinatura;
    - período encerrado -> volta ao free (só se o plano atual veio da assinatura,
      para não desfazer uma alteração manual feita pelo admin).
    Admins não são alterados.
    """
    if user.is_admin:
        return

    sub = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == user.id)
        .filter(models.Subscription.status.in_(ACCESS_STATUSES))
        .filter(models.Subscription.current_period_end.isnot(None))
        .order_by(models.Subscription.current_period_end.desc())
        .first()
    )

    if sub is None:
        return

    changed = False

    if sub.current_period_end >= _now():
        if user.plan != sub.plan:
            _set_user_plan(user, sub.plan)
            changed = True
    elif user.plan == sub.plan:
        _set_user_plan(user, "free")
        changed = True

    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)


# ------------------------------------------------------------
# Checkout
# ------------------------------------------------------------

def start_checkout(
    db: Session,
    user: models.User,
    plan: str,
    name: str,
    cpf_cnpj: str,
) -> dict:
    if not config.billing_enabled():
        raise HTTPException(status_code=503, detail="Pagamentos ainda não estão disponíveis.")

    if plan not in config.PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Plano inválido.")

    if not valid_cpf_cnpj(cpf_cnpj):
        raise HTTPException(status_code=400, detail="CPF ou CNPJ inválido.")

    sub = latest_subscription(db, user.id)

    if sub and sub.status in ("active", "past_due") and sub.current_period_end and sub.current_period_end >= _now():
        if sub.plan == plan:
            raise HTTPException(status_code=409, detail="Você já possui este plano ativo.")
        raise HTTPException(
            status_code=409,
            detail="Cancele a assinatura atual antes de trocar de plano.",
        )

    if sub and sub.status == "pending":
        if sub.plan == plan and sub.invoice_url:
            # Evita criar assinaturas duplicadas se o usuário clicar de novo.
            return {"invoice_url": sub.invoice_url, "subscription": subscription_to_dict(sub)}
        _cancel_at_provider(sub)
        sub.status = "canceled"
        sub.canceled_at = _now()
        db.commit()

    customer_id = next(
        (
            s.provider_customer_id
            for s in db.query(models.Subscription)
            .filter(models.Subscription.user_id == user.id)
            .filter(models.Subscription.provider_customer_id.isnot(None))
            .order_by(models.Subscription.id.desc())
        ),
        None,
    )

    try:
        if not customer_id:
            customer = asaas_client.create_customer(
                name=name.strip(),
                cpf_cnpj=only_digits(cpf_cnpj),
                email=user.email,
                external_reference=f"user:{user.id}",
            )
            customer_id = customer["id"]

        value = config.PLAN_PRICES[plan]
        created = asaas_client.create_subscription(
            customer_id=customer_id,
            value=value,
            next_due_date=datetime.now(BR_TZ).date().isoformat(),
            description=f"Assinatura MBA IA - Plano {PLAN_NAMES.get(plan, plan)}",
            external_reference=f"user:{user.id}",
        )
        payments = asaas_client.list_subscription_payments(created["id"])
    except asaas_client.AsaasError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível iniciar o pagamento: {exc}",
        ) from exc

    invoice_url = next((p.get("invoiceUrl") for p in payments if p.get("invoiceUrl")), None)

    sub = models.Subscription(
        user_id=user.id,
        provider="asaas",
        provider_customer_id=customer_id,
        provider_subscription_id=created["id"],
        plan=plan,
        status="pending",
        value=value,
        invoice_url=invoice_url,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    logger.info("Assinatura criada: user=%s plano=%s sub=%s", user.id, plan, created["id"])

    return {"invoice_url": invoice_url, "subscription": subscription_to_dict(sub)}


# ------------------------------------------------------------
# Cancelamento
# ------------------------------------------------------------

def _cancel_at_provider(sub: models.Subscription) -> None:
    if not sub.provider_subscription_id:
        return
    try:
        asaas_client.delete_subscription(sub.provider_subscription_id)
    except asaas_client.AsaasError as exc:
        if exc.status_code == 404:
            return  # já removida na Asaas
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível cancelar no provedor de pagamento: {exc}",
        ) from exc


def cancel_subscription(db: Session, user: models.User) -> dict:
    sub = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == user.id)
        .filter(models.Subscription.status.in_(("pending", "active", "past_due")))
        .order_by(models.Subscription.id.desc())
        .first()
    )

    if sub is None:
        raise HTTPException(status_code=404, detail="Nenhuma assinatura ativa.")

    _cancel_at_provider(sub)

    if sub.status == "pending":
        sub.current_period_end = None
    sub.status = "canceled"
    sub.canceled_at = _now()
    db.commit()
    db.refresh(sub)

    logger.info("Assinatura cancelada pelo usuário: user=%s sub=%s", user.id, sub.provider_subscription_id)
    return subscription_to_dict(sub)


# ------------------------------------------------------------
# Webhook
# ------------------------------------------------------------

def _find_subscription(db: Session, provider_subscription_id: str | None) -> models.Subscription | None:
    if not provider_subscription_id:
        return None
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.provider_subscription_id == provider_subscription_id)
        .first()
    )


def _apply_event(db: Session, event_type: str, payload: dict) -> None:
    payment = payload.get("payment") or {}
    subscription = payload.get("subscription") or {}

    sub = _find_subscription(db, payment.get("subscription") or subscription.get("id"))

    if sub is None:
        # Cobranças avulsas ou de outra integração: nada a fazer.
        return

    if event_type in PAID_EVENTS:
        period_end = _period_end_from_due_date(payment.get("dueDate"))
        if sub.current_period_end is None or period_end > sub.current_period_end:
            sub.current_period_end = period_end
        if sub.status in ("pending", "past_due"):
            sub.status = "active"

    elif event_type == "PAYMENT_OVERDUE":
        if sub.status == "active":
            sub.status = "past_due"

    elif event_type == "PAYMENT_CREATED":
        if payment.get("invoiceUrl") and sub.status != "canceled":
            sub.invoice_url = payment["invoiceUrl"]

    elif event_type in REVOKE_EVENTS:
        sub.status = "canceled"
        sub.canceled_at = _now()
        sub.current_period_end = _now()

    elif event_type in SUBSCRIPTION_END_EVENTS:
        if sub.status != "canceled":
            sub.status = "canceled"
            sub.canceled_at = _now()

    db.flush()

    user = db.get(models.User, sub.user_id)
    if user is not None:
        sync_user_plan(db, user)


def handle_webhook(db: Session, payload: dict) -> str:
    """
    Registra e processa um evento. Retorna "processed", "duplicate" ou "error".
    Eventos repetidos (mesmo id) são ignorados.
    """
    event_id = str(payload.get("id") or "").strip()
    event_type = str(payload.get("event") or "").strip()

    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Evento inválido.")

    event = models.BillingEvent(
        id=event_id,
        provider="asaas",
        event_type=event_type,
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return "duplicate"

    try:
        _apply_event(db, event_type, payload)
        event = db.get(models.BillingEvent, event_id)
        event.processed = True
        db.commit()
        return "processed"
    except Exception as exc:
        # O evento fica registrado com o erro para reprocessamento manual;
        # respondemos 200 para a Asaas não pausar a fila de webhooks.
        db.rollback()
        logger.exception("Falha ao processar evento %s (%s)", event_id, event_type)
        event = db.get(models.BillingEvent, event_id)
        if event is not None:
            event.error = str(exc)[:2000]
            db.commit()
        return "error"
