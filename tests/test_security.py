"""
Testes da Fase 0 (segurança): login sem enumeração de usuários,
senha mínima, bloqueio de usuário inativo, erros genéricos e rate limit.
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.main import app
from app.rate_limit import limiter
from app.routes import projects as projects_routes
from app.routes.auth import hash_password
from app.security import create_access_token, get_db


def _make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()
    return TestClient(app), TestingSession


def _add_user(Session, email="ana@exemplo.com", password="senha-forte-123", active=True):
    db = Session()
    user = models.User(
        email=email,
        hashed_password=hash_password(password),
        plan="free",
        monthly_generation_limit=5,
        is_active=active,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.close()


def teardown_function():
    app.dependency_overrides.clear()
    limiter.reset()


def test_login_does_not_reveal_whether_email_exists():
    client, Session = _make_client()
    _add_user(Session)

    unknown = client.post("/auth/login", data={"username": "ninguem@exemplo.com", "password": "x"})
    wrong = client.post("/auth/login", data={"username": "ana@exemplo.com", "password": "errada"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_login_success_returns_token():
    client, Session = _make_client()
    _add_user(Session)

    response = client.post(
        "/auth/login",
        data={"username": "ana@exemplo.com", "password": "senha-forte-123"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_register_rejects_short_password():
    client, _ = _make_client()

    response = client.post("/auth/register", json={"email": "novo@exemplo.com", "password": "123"})

    assert response.status_code == 422


def test_inactive_user_token_is_rejected():
    client, Session = _make_client()
    _add_user(Session, active=False)
    token = create_access_token({"sub": "ana@exemplo.com"})

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_forged_token_is_rejected():
    client, Session = _make_client()
    _add_user(Session)
    from jose import jwt

    forged = jwt.encode({"sub": "ana@exemplo.com"}, "super-secret-key-change-this", algorithm="HS256")

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_generation_error_does_not_leak_internal_details(monkeypatch):
    client, Session = _make_client()
    _add_user(Session)
    token = create_access_token({"sub": "ana@exemplo.com"})

    def boom(_bug):
        raise RuntimeError("OPENAI_API_KEY=sk-segredo caminho=/srv/app")

    monkeypatch.setattr(projects_routes, "generate_all", boom)

    response = client.post(
        "/projects/generate",
        json={"bug": "Tela de login não carrega"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 500
    assert "sk-segredo" not in response.text
    assert "/srv/app" not in response.text
    assert "código" in response.json()["detail"]


def test_login_is_rate_limited():
    client, Session = _make_client()
    _add_user(Session)

    statuses = [
        client.post("/auth/login", data={"username": "ana@exemplo.com", "password": "errada"}).status_code
        for _ in range(12)
    ]

    assert statuses[:10] == [401] * 10
    assert statuses[-1] == 429


def test_security_headers_present():
    client, _ = _make_client()

    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
