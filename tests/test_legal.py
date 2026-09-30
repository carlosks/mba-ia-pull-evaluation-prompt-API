"""
Página de vendas, dados do vendedor e aceite dos Termos de Uso /
Política de Privacidade.
"""

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
from app.services import legal_service


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
    monkeypatch.setattr(config, "SELLER_NAME", "Fulano de Tal")
    monkeypatch.setattr(config, "SELLER_DOCUMENT", "52998224725")
    monkeypatch.setattr(config, "CONTACT_EMAIL", "contato@exemplo.com")
    monkeypatch.setattr(config, "TERMS_VERSION", "2026-09-30")
    monkeypatch.setattr(config, "ASAAS_API_KEY", "")

    yield TestClient(app), Session

    app.dependency_overrides.clear()
    limiter.reset()


def _register(client, accept_terms):
    payload = {"email": "novo@exemplo.com", "password": "senha-forte-123"}
    if accept_terms is not None:
        payload["accept_terms"] = accept_terms
    return client.post("/auth/register", json=payload)


def test_root_opens_sales_page(env):
    client, _ = env
    response = client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/static/index.html"

    page = client.get("/static/index.html")
    assert page.status_code == 200
    assert "Criar conta grátis" in page.text
    assert "http-equiv=\"refresh\"" not in page.text


@pytest.mark.parametrize("path", ["/static/termos.html", "/static/privacidade.html"])
def test_legal_pages_are_public(env, path):
    client, _ = env
    assert client.get(path).status_code == 200


def test_legal_info_formats_seller_document(env):
    client, _ = env
    data = client.get("/legal/info").json()

    assert data["seller_name"] == "Fulano de Tal"
    assert data["seller_document"] == "529.982.247-25"
    assert data["seller_document_label"] == "CPF"
    assert data["contact_email"] == "contato@exemplo.com"
    assert data["terms_version"] == "2026-09-30"


def test_format_document_cnpj():
    assert legal_service.format_document("11222333000181") == "11.222.333/0001-81"
    assert legal_service.document_label("11.222.333/0001-81") == "CNPJ"


@pytest.mark.parametrize("accept", [None, False])
def test_register_requires_terms(env, accept):
    client, Session = env
    response = _register(client, accept)

    assert response.status_code == 400
    assert "Termos de Uso" in response.json()["detail"]

    db = Session()
    assert db.query(models.User).count() == 0
    db.close()


def test_register_records_acceptance(env):
    client, Session = env
    response = _register(client, True)

    assert response.status_code == 200
    assert response.json()["terms_accepted"] is True

    db = Session()
    user = db.query(models.User).one()
    assert user.terms_version == "2026-09-30"
    assert user.terms_accepted_at is not None
    db.close()


def _legacy_user(Session):
    """Conta criada antes dos Termos existirem."""
    db = Session()
    db.add(models.User(email="antigo@exemplo.com", hashed_password=hash_password("senha-forte-123"),
                       plan="free", monthly_generation_limit=5, is_active=True, is_admin=False))
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {create_access_token({'sub': 'antigo@exemplo.com'})}"}


def test_checkout_requires_terms_for_old_accounts(env):
    client, Session = env
    headers = _legacy_user(Session)

    assert client.get("/auth/me", headers=headers).json()["terms_accepted"] is False

    payload = {"plan": "pro", "name": "Ana Souza", "cpf_cnpj": "52998224725"}
    refused = client.post("/billing/checkout", json=payload, headers=headers)
    assert refused.status_code == 400
    assert "Termos de Uso" in refused.json()["detail"]

    # Com o aceite, o termo é registrado (a cobrança em si está desligada neste teste).
    accepted = client.post("/billing/checkout", json={**payload, "accept_terms": True}, headers=headers)
    assert accepted.status_code == 503
    assert client.get("/auth/me", headers=headers).json()["terms_accepted"] is True


def test_new_terms_version_requires_new_acceptance(env, monkeypatch):
    client, Session = env
    _register(client, True)
    monkeypatch.setattr(config, "TERMS_VERSION", "2027-01-01")

    token = create_access_token({"sub": "novo@exemplo.com"})
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert me["terms_accepted"] is False
