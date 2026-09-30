import hmac
import json
import logging
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import config, models
from app.security import get_current_user, get_db
from app.services import billing_service

router = APIRouter(tags=["Billing"])
logger = logging.getLogger("app.billing")


class PlanOut(BaseModel):
    plan: str
    name: str
    price: float
    monthly_generation_limit: int


class PlansOut(BaseModel):
    billing_enabled: bool
    plans: List[PlanOut]


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    value: float
    invoice_url: Optional[str] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None


class MySubscriptionOut(BaseModel):
    current_plan: str
    subscription: Optional[SubscriptionOut] = None


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "team"]
    name: str = Field(..., min_length=3, max_length=120)
    cpf_cnpj: str = Field(..., min_length=11, max_length=20)


class CheckoutOut(BaseModel):
    invoice_url: Optional[str] = None
    subscription: SubscriptionOut


@router.get("/plans", response_model=PlansOut)
def list_plans():
    """Tabela pública de planos e preços."""
    return {"billing_enabled": config.billing_enabled(), "plans": billing_service.plan_catalog()}


@router.get("/subscription", response_model=MySubscriptionOut)
def my_subscription(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    billing_service.sync_user_plan(db, current_user)
    sub = billing_service.latest_subscription(db, current_user.id)
    return {
        "current_plan": current_user.plan,
        "subscription": billing_service.subscription_to_dict(sub),
    }


@router.post("/checkout", response_model=CheckoutOut)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Cria a assinatura na Asaas e devolve o link da fatura.
    O cliente paga na página da Asaas (Pix, boleto ou cartão); o plano é
    liberado quando o webhook confirma o pagamento.
    """
    return billing_service.start_checkout(
        db, current_user, payload.plan, payload.name, payload.cpf_cnpj
    )


@router.post("/cancel", response_model=SubscriptionOut)
def cancel(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancela a renovação. O acesso continua até o fim do período já pago."""
    return billing_service.cancel_subscription(db, current_user)


@router.post("/webhook")
async def asaas_webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe eventos da Asaas. Autenticado pelo cabeçalho asaas-access-token."""
    if not config.ASAAS_WEBHOOK_TOKEN:
        raise HTTPException(status_code=503, detail="Webhook não configurado.")

    received = request.headers.get("asaas-access-token", "")
    if not hmac.compare_digest(received.encode(), config.ASAAS_WEBHOOK_TOKEN.encode()):
        logger.warning("Webhook recusado: token inválido")
        raise HTTPException(status_code=401, detail="Token inválido.")

    try:
        payload = json.loads(await request.body())
    except ValueError:
        raise HTTPException(status_code=400, detail="JSON inválido.")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Evento inválido.")

    result = billing_service.handle_webhook(db, payload)
    return {"received": True, "result": result}
