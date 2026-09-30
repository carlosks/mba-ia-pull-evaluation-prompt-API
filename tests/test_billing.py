"""
Testes da cobrança (Asaas simulada com httpx.MockTransport).
"""

import json
from datetime import datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, models
from app.database import Base
from app.main import app
from app.rate_limit import limiter
from app.routes.auth import hash_password
from app.security import create_access_token, get_db
from app.services import asaas_client, billing_service

CPF_VALIDO = "529.982.247-25"
WEBHOOK_TOKEN = "token-webhook-teste"


class FakeAsaas:
    """Simula a API da Asaas e registra as chamadas recebidas."""

    def __init__(self):
        self.calls = []
        self.customers = 0
        self.subscriptions = 0
        self.fail_with = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, request.url.path, body, request.headers.get("access_token")))

        if self.fail_with:
            return httpx.Response(400, json={"errors": [{"code": "invalid", "description": self.fail_with}]})

        path = request.url.path
        if request.method == "POST" and path.endswith("/customers"):
            self.customers += 1
            return httpx.Response(200, json={"id": f"cus_{self.customers}"})
        if request.method == "POST" and path.endswith("/subscriptions"):
            self.subscriptions += 1
            return httpx.Response(200, json={"id": f"sub_{self.subscriptions}", "status": "ACTIVE"})
        if request.method == "GET" and path.endswith("/payments"):
            sub_id = path.split("/")[-2]
            return httpx.Response(200, json={"data": [{"id": f"pay_{sub_id}", "invoiceUrl": f"https://sandbox.asaas.com/i/{sub_id}"}]})
        if request.method == "DELETE":
            return httpx.Response(200, json={"deleted": True})
        return httpx.Response(404, json={"errors": [{"description": "não encontrado"}]})


@pytest.fixture
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()

    fake = FakeAsaas()
    monkeypatch.setattr(asaas_client, "transport", httpx.MockTransport(fake.handler))
    monkeypatch.setattr(config, "ASAAS_API_KEY", "chave-sandbox")
    monkeypatch.setattr(config, "ASAAS_WEBHOOK_TOKEN", WEBHOOK_TOKEN)

    db = Session()
    db.add(models.User(email="ana@exemplo.com", hashed_password=hash_password("senha-forte-123"),
                       plan="free", monthly_generation_limit=5, is_active=True, is_admin=False))
    db.commit()
    db.close()

    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'ana@exemplo.com'})}"}
    yield TestClient(app), Session, headers, fake

    app.dependency_overrides.clear()
    limiter.reset()


def _checkout(client, headers, plan="pro"):
    return client.post("/billing/checkout", json={"plan": plan, "name": "Ana Souza", "cpf_cnpj": CPF_VALIDO, "accept_terms": True}, headers=headers)


def _webhook(client, event_id, event, **resource):
    return client.post(
        "/billing/webhook",
        json={"id": event_id, "event": event, "dateCreated": "2026-09-30 10:00:00", **resource},
        headers={"asaas-access-token": WEBHOOK_TOKEN},
    )


def _user(Session):
    db = Session()
    user = db.query(models.User).filter_by(email="ana@exemplo.com").one()
    db.close()
    return user


def test_plans_are_public(env):
    client, *_ = env
    data = client.get("/billing/plans").json()
    assert data["billing_enabled"] is True
    assert [p["plan"] for p in data["plans"]] == ["free", "pro", "team"]


def test_checkout_creates_customer_and_subscription(env):
    client, Session, headers, fake = env

    response = _checkout(client, headers)

    assert response.status_code == 200
    assert response.json()["invoice_url"] == "https://sandbox.asaas.com/i/sub_1"
    assert response.json()["subscription"]["status"] == "pending"

    customer_call = next(c for c in fake.calls if c[1].endswith("/customers"))
    assert customer_call[2]["cpfCnpj"] == "52998224725"
    assert customer_call[3] == "chave-sandbox"
    sub_call = next(c for c in fake.calls if c[0] == "POST" and c[1].endswith("/subscriptions"))
    assert sub_call[2]["billingType"] == "UNDEFINED"
    assert sub_call[2]["value"] == config.PLAN_PRICES["pro"]

    # Antes do pagamento o plano continua free.
    assert _user(Session).plan == "free"


def test_checkout_again_reuses_pending_invoice(env):
    client, Session, headers, fake = env
    _checkout(client, headers)
    second = _checkout(client, headers)

    assert second.json()["invoice_url"] == "https://sandbox.asaas.com/i/sub_1"
    assert fake.subscriptions == 1


def test_checkout_rejects_invalid_cpf(env):
    client, _, headers, fake = env
    response = client.post("/billing/checkout", json={"plan": "pro", "name": "Ana Souza", "cpf_cnpj": "111.111.111-11", "accept_terms": True}, headers=headers)
    assert response.status_code == 400
    assert fake.calls == []


def test_payment_webhook_activates_plan(env):
    client, Session, headers, _ = env
    _checkout(client, headers)

    response = _webhook(client, "evt_1", "PAYMENT_RECEIVED",
                        payment={"id": "pay_1", "subscription": "sub_1", "dueDate": "2026-09-30", "value": 49.9})

    assert response.status_code == 200
    user = _user(Session)
    assert user.plan == "pro"
    assert user.monthly_generation_limit == 100

    me = client.get("/billing/subscription", headers=headers).json()
    assert me["subscription"]["status"] == "active"


def test_duplicate_webhook_is_ignored(env):
    client, Session, headers, _ = env
    _checkout(client, headers)
    payload = {"payment": {"id": "pay_1", "subscription": "sub_1", "dueDate": "2026-09-30"}}

    first = _webhook(client, "evt_dup", "PAYMENT_RECEIVED", **payload)
    second = _webhook(client, "evt_dup", "PAYMENT_RECEIVED", **payload)

    assert first.json()["result"] == "processed"
    assert second.json()["result"] == "duplicate"


def test_webhook_requires_token(env):
    client, *_ = env
    response = client.post("/billing/webhook", json={"id": "evt_x", "event": "PAYMENT_RECEIVED"},
                           headers={"asaas-access-token": "errado"})
    assert response.status_code == 401


def test_expired_subscription_returns_user_to_free(env):
    client, Session, headers, _ = env
    _checkout(client, headers)
    _webhook(client, "evt_1", "PAYMENT_RECEIVED", payment={"subscription": "sub_1", "dueDate": "2026-09-30"})
    _webhook(client, "evt_2", "SUBSCRIPTION_DELETED", subscription={"id": "sub_1"})

    # Cancelada, mas o período pago ainda vale.
    assert _user(Session).plan == "pro"

    db = Session()
    sub = db.query(models.Subscription).one()
    sub.current_period_end = datetime.utcnow() - timedelta(days=1)
    db.commit()
    db.close()

    me = client.get("/auth/me", headers=headers).json()
    assert me["plan"] == "free"
    assert me["monthly_generation_limit"] == 5


def test_refund_revokes_access_immediately(env):
    client, Session, headers, _ = env
    _checkout(client, headers)
    _webhook(client, "evt_1", "PAYMENT_RECEIVED", payment={"subscription": "sub_1", "dueDate": "2026-09-30"})
    _webhook(client, "evt_2", "PAYMENT_REFUNDED", payment={"subscription": "sub_1"})

    assert _user(Session).plan == "free"


def test_cancel_calls_asaas_and_keeps_paid_period(env):
    client, Session, headers, fake = env
    _checkout(client, headers)
    _webhook(client, "evt_1", "PAYMENT_RECEIVED", payment={"subscription": "sub_1", "dueDate": "2026-09-30"})

    response = client.post("/billing/cancel", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"
    assert any(c[0] == "DELETE" and c[1].endswith("/subscriptions/sub_1") for c in fake.calls)
    assert _user(Session).plan == "pro"


def test_admin_plan_is_never_changed_by_billing(env):
    client, Session, headers, _ = env
    db = Session()
    user = db.query(models.User).one()
    user.is_admin = True
    user.plan = "admin"
    db.commit()
    db.close()

    _checkout(client, headers)
    _webhook(client, "evt_1", "PAYMENT_RECEIVED", payment={"subscription": "sub_1", "dueDate": "2026-09-30"})

    assert _user(Session).plan == "admin"


def test_asaas_error_is_reported(env):
    client, _, headers, fake = env
    fake.fail_with = "O CPF/CNPJ informado é inválido."

    response = _checkout(client, headers)

    assert response.status_code == 502
    assert "CPF/CNPJ" in response.json()["detail"]


def test_checkout_unavailable_without_api_key(env, monkeypatch):
    client, _, headers, _ = env
    monkeypatch.setattr(config, "ASAAS_API_KEY", "")
    assert _checkout(client, headers).status_code == 503


def test_cpf_cnpj_validation():
    assert billing_service.valid_cpf_cnpj("529.982.247-25")
    assert billing_service.valid_cpf_cnpj("11.222.333/0001-81")
    assert not billing_service.valid_cpf_cnpj("123.456.789-00")
    assert not billing_service.valid_cpf_cnpj("11.222.333/0001-80")


def test_static_files_are_revalidated(env):
    client, *_ = env
    assert client.get("/static/app.js").headers["Cache-Control"] == "no-cache"
