"""Swagger (/docs): fechado, aberto ou protegido por usuário e senha."""

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.rate_limit import limiter

PATHS = ["/docs", "/openapi.json", "/redoc"]


@pytest.fixture
def client():
    limiter.reset()
    yield TestClient(app)
    limiter.reset()


def _set(monkeypatch, enabled, user="", password=""):
    monkeypatch.setattr(config, "DOCS_ENABLED", enabled)
    monkeypatch.setattr(config, "DOCS_USERNAME", user)
    monkeypatch.setattr(config, "DOCS_PASSWORD", password)
    monkeypatch.setattr(config, "DOCS_PROTECTED", bool(user and password))
    monkeypatch.setattr(config, "DOCS_AVAILABLE", enabled or bool(user and password))


@pytest.mark.parametrize("path", PATHS)
def test_hidden_in_production_without_credentials(client, monkeypatch, path):
    _set(monkeypatch, enabled=False)
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", PATHS)
def test_open_in_development(client, monkeypatch, path):
    _set(monkeypatch, enabled=True)
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", PATHS)
def test_protected_requires_login(client, monkeypatch, path):
    _set(monkeypatch, enabled=False, user="carlos", password="senha-longa-e-unica")

    anonymous = client.get(path)
    assert anonymous.status_code == 401
    assert anonymous.headers["www-authenticate"].startswith("Basic")

    assert client.get(path, auth=("carlos", "errada")).status_code == 401
    assert client.get(path, auth=("outro", "senha-longa-e-unica")).status_code == 401
    assert client.get(path, auth=("carlos", "senha-longa-e-unica")).status_code == 200


def test_openapi_lists_api_routes(client, monkeypatch):
    _set(monkeypatch, enabled=False, user="carlos", password="senha-longa-e-unica")
    schema = client.get("/openapi.json", auth=("carlos", "senha-longa-e-unica")).json()

    assert "/auth/login" in schema["paths"]
    assert "/jobs" in schema["paths"]
    assert "/docs" not in schema["paths"]


def test_swagger_page_points_to_schema(client, monkeypatch):
    _set(monkeypatch, enabled=True)
    assert "/openapi.json" in client.get("/docs").text
