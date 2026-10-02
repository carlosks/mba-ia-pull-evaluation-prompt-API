"""
"Esqueci minha senha": pedido sem revelar contas, link de uso único com
validade, troca de senha e encerramento das sessões antigas.
"""

import re
import time
from datetime import datetime, timedelta

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
from app.security import get_db
from app.services import email_service, password_reset_service

EMAIL = "ana@exemplo.com"
OLD_PASSWORD = "senha-antiga-123"
NEW_PASSWORD = "senha-nova-456"


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

    sent = []
    monkeypatch.setattr(email_service, "sender", sent.append)
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setattr(config, "EMAIL_FROM", "nao-responda@exemplo.com")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://app.exemplo.com")

    db = Session()
    db.add(models.User(email=EMAIL, hashed_password=hash_password(OLD_PASSWORD),
                       plan="free", monthly_generation_limit=5, is_active=True, is_admin=False))
    db.commit()
    db.close()

    yield TestClient(app), Session, sent

    app.dependency_overrides.clear()
    limiter.reset()


def _forgot(client, email=EMAIL):
    return client.post("/auth/forgot-password", json={"email": email})


def _token_from(message) -> str:
    body = message.get_body(preferencelist=("plain",)).get_content()
    match = re.search(r"https://app\.exemplo\.com/static/nova-senha\.html#token=([\w-]+)", body)
    assert match, body
    return match.group(1)


def _login(client, password):
    return client.post("/auth/login", data={"username": EMAIL, "password": password})


def test_same_answer_for_existing_and_unknown_email(env):
    client, _, sent = env

    known = _forgot(client)
    unknown = _forgot(client, "ninguem@exemplo.com")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(sent) == 1
    assert sent[0]["To"] == EMAIL


def test_token_is_stored_only_as_hash(env):
    client, Session, sent = env
    _forgot(client)
    token = _token_from(sent[0])

    db = Session()
    record = db.query(models.PasswordResetToken).one()
    assert record.token_hash != token
    assert len(record.token_hash) == 64
    db.close()


def test_reset_changes_password_and_link_is_single_use(env):
    client, _, sent = env
    _forgot(client)
    token = _token_from(sent[0])

    ok = client.post("/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert ok.status_code == 200

    assert _login(client, OLD_PASSWORD).status_code == 401
    assert _login(client, NEW_PASSWORD).status_code == 200

    again = client.post("/auth/reset-password", json={"token": token, "password": "outra-senha-789"})
    assert again.status_code == 400


def test_reset_invalidates_other_pending_links(env):
    client, _, sent = env
    _forgot(client)
    _forgot(client)
    first, second = _token_from(sent[0]), _token_from(sent[1])

    assert client.post("/auth/reset-password", json={"token": second, "password": NEW_PASSWORD}).status_code == 200
    assert client.post("/auth/reset-password", json={"token": first, "password": "outra-senha-789"}).status_code == 400


def test_expired_link_is_rejected(env):
    client, Session, sent = env
    _forgot(client)
    token = _token_from(sent[0])

    db = Session()
    record = db.query(models.PasswordResetToken).one()
    record.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    db.close()

    response = client.post("/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert response.status_code == 400
    assert _login(client, OLD_PASSWORD).status_code == 200


def test_invalid_token_and_short_password(env):
    client, _, _ = env
    assert client.post("/auth/reset-password", json={"token": "x" * 43, "password": NEW_PASSWORD}).status_code == 400
    assert client.post("/auth/reset-password", json={"token": "x" * 43, "password": "123"}).status_code == 422


def test_old_sessions_end_after_reset(env):
    client, _, sent = env
    old_token = _login(client, OLD_PASSWORD).json()["access_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 200

    time.sleep(1.1)  # o "iat" do token tem resolução de segundos
    _forgot(client)
    client.post("/auth/reset-password", json={"token": _token_from(sent[0]), "password": NEW_PASSWORD})

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401

    new_token = _login(client, NEW_PASSWORD).json()["access_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200


def test_inactive_user_gets_no_email(env):
    client, Session, sent = env
    db = Session()
    db.query(models.User).filter_by(email=EMAIL).update({"is_active": False})
    db.commit()
    db.close()

    assert _forgot(client).status_code == 200
    assert sent == []


def test_hourly_limit_per_account(env, monkeypatch):
    client, _, sent = env
    monkeypatch.setattr(config, "PASSWORD_RESET_MAX_PER_HOUR", 2)

    for _ in range(3):
        assert _forgot(client).status_code == 200

    assert len(sent) == 2


def test_email_contains_html_button_and_escaped_link(env):
    client, _, sent = env
    _forgot(client)
    html = sent[0].get_body(preferencelist=("html",)).get_content()

    assert "Criar nova senha" in html
    assert "https://app.exemplo.com/static/nova-senha.html#token=" in html


def test_without_smtp_nothing_is_sent(env, monkeypatch):
    client, _, sent = env
    monkeypatch.setattr(config, "SMTP_HOST", "")

    assert _forgot(client).status_code == 200
    assert sent == []


def test_reset_pages_are_public(env):
    client, _, _ = env
    assert client.get("/static/esqueci-senha.html").status_code == 200
    assert client.get("/static/nova-senha.html").status_code == 200
    assert "esqueci-senha.html" in client.get("/static/login.html").text
