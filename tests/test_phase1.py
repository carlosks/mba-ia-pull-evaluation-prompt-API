"""
Testes da Fase 1: fila de gerações, custo por geração e armazenamento durável.
"""

import io
import json
import zipfile
from concurrent.futures import Future

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
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
from app.services import jobs_service, storage_service


class InlineExecutor:
    """Executa o job na hora, para o teste não depender de threads."""

    def submit(self, fn, *args):
        future = Future()
        future.set_result(fn(*args))
        return future


@pytest.fixture
def env(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(jobs_service, "session_factory", Session)
    monkeypatch.setattr(jobs_service, "executor", InlineExecutor())
    limiter.reset()

    db = Session()
    db.add(
        models.User(
            email="ana@exemplo.com",
            hashed_password=hash_password("senha-forte-123"),
            plan="free",
            monthly_generation_limit=2,
            is_active=True,
            is_admin=False,
        )
    )
    db.commit()
    db.close()

    token = create_access_token({"sub": "ana@exemplo.com"})
    yield TestClient(app), Session, {"Authorization": f"Bearer {token}"}

    app.dependency_overrides.clear()
    limiter.reset()


def _fake_generate_all(bug):
    """Simula o gerador chamando um LLM que reporta 1000 tokens de entrada e 500 de saída."""
    message = AIMessage(
        content="ok",
        usage_metadata={"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
        response_metadata={"model_name": "gpt-4o-mini"},
    )
    GenericFakeChatModel(messages=iter([message])).invoke("oi")
    return {"user_story": f"Como usuário, quero corrigir: {bug}", "acceptance_criteria": ["Dado", "Quando", "Então"]}


def test_job_runs_and_records_cost(env, monkeypatch):
    client, Session, headers = env
    monkeypatch.setattr(projects_routes, "generate_all", _fake_generate_all)

    created = client.post("/jobs", json={"kind": "generate", "bug": "Tela de login em branco"}, headers=headers)
    assert created.status_code == 202

    job = client.get(f"/jobs/{created.json()['id']}", headers=headers).json()
    assert job["status"] == "succeeded"
    assert job["result"]["user_story"].startswith("Como usuário")

    db = Session()
    log = db.query(models.UsageLog).one()
    assert log.status == "success"
    assert (log.input_tokens, log.output_tokens) == (1000, 500)
    assert log.cost_usd == pytest.approx(0.00045)
    db.close()


def test_failed_job_hides_details_and_does_not_consume_quota(env, monkeypatch):
    client, Session, headers = env

    def boom(_bug):
        raise RuntimeError("sk-segredo /srv/app")

    monkeypatch.setattr(projects_routes, "generate_all", boom)

    created = client.post("/jobs", json={"kind": "generate", "bug": "Erro 500 no salvar"}, headers=headers)
    job = client.get(f"/jobs/{created.json()['id']}", headers=headers).json()

    assert job["status"] == "failed"
    assert "sk-segredo" not in job["error_message"]
    assert "código" in job["error_message"]

    me = client.get("/auth/me", headers=headers).json()
    assert me["monthly_usage"] == 0


def test_monthly_quota_counts_pending_jobs(env, monkeypatch):
    client, Session, headers = env

    class HoldingExecutor:
        def submit(self, fn, *args):
            return Future()  # nunca executa: o job fica na fila

    monkeypatch.setattr(jobs_service, "executor", HoldingExecutor())
    monkeypatch.setattr(jobs_service, "MAX_PENDING_JOBS_PER_USER", 10)

    statuses = [
        client.post("/jobs", json={"kind": "generate", "bug": f"Bug número {i}"}, headers=headers).status_code
        for i in range(3)
    ]

    # Limite do usuário = 2 gerações no mês.
    assert statuses == [202, 202, 429]


def test_user_cannot_see_other_users_job(env, monkeypatch):
    client, Session, headers = env
    monkeypatch.setattr(projects_routes, "generate_all", _fake_generate_all)
    job_id = client.post("/jobs", json={"kind": "generate", "bug": "Bug do dashboard"}, headers=headers).json()["id"]

    db = Session()
    db.add(models.User(email="bia@exemplo.com", hashed_password="x", plan="free", monthly_generation_limit=5, is_active=True, is_admin=False))
    db.commit()
    db.close()
    other = {"Authorization": f"Bearer {create_access_token({'sub': 'bia@exemplo.com'})}"}

    assert client.get(f"/jobs/{job_id}", headers=other).status_code == 404


def test_interrupted_jobs_are_recovered_on_startup(env, monkeypatch):
    client, Session, headers = env
    submitted = []

    class RecordingExecutor:
        def submit(self, fn, *args):
            submitted.append(args)
            return Future()

    monkeypatch.setattr(jobs_service, "executor", RecordingExecutor())

    db = Session()
    db.add(models.GenerationJob(id="running-1", user_id=1, kind="generate", status="running", bug="x" * 10))
    db.add(models.GenerationJob(id="queued-1", user_id=1, kind="generate", status="queued", bug="y" * 10))
    db.commit()
    db.close()

    jobs_service.recover_jobs_on_startup()

    db = Session()
    assert db.get(models.GenerationJob, "running-1").status == "failed"
    assert submitted == [("queued-1",)]
    db.close()


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


def test_storage_roundtrip_restores_deleted_project(tmp_path, monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage_service, "GENERATED_PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(storage_service, "STORAGE_BUCKET", "meu-bucket")
    monkeypatch.setattr(storage_service, "_client", fake)

    project = tmp_path / "proj_1"
    (project / "app").mkdir(parents=True)
    (project / "app" / "main.py").write_text("print('oi')", encoding="utf-8")

    assert storage_service.persist_project("proj_1") is True

    # Simula o redeploy apagando o disco.
    import shutil

    shutil.rmtree(project)

    assert storage_service.ensure_local_project("proj_1") is True
    assert (project / "app" / "main.py").read_text(encoding="utf-8") == "print('oi')"


def test_storage_rejects_zip_with_path_traversal(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../../fora.txt", "ataque")

    with pytest.raises(ValueError):
        storage_service._safe_extract(buffer.getvalue(), tmp_path / "proj")

    assert not (tmp_path.parent / "fora.txt").exists()


def test_storage_disabled_is_noop(monkeypatch):
    monkeypatch.setattr(storage_service, "STORAGE_BUCKET", "")
    assert storage_service.persist_project("qualquer") is False


def test_admin_usage_costs_report(env, monkeypatch):
    client, Session, headers = env
    monkeypatch.setattr(projects_routes, "generate_all", _fake_generate_all)
    client.post("/jobs", json={"kind": "generate", "bug": "Bug do relatório"}, headers=headers)

    db = Session()
    db.add(models.User(email="admin@exemplo.com", hashed_password="x", plan="admin", monthly_generation_limit=-1, is_active=True, is_admin=True))
    db.commit()
    db.close()
    admin = {"Authorization": f"Bearer {create_access_token({'sub': 'admin@exemplo.com'})}"}

    report = client.get("/admin/usage-costs", headers=admin).json()

    assert report["plans"]["free"]["generations_success"] == 1
    assert report["plans"]["free"]["avg_cost_per_generation_usd"] == pytest.approx(0.00045)
    assert client.get("/admin/usage-costs", headers=headers).status_code == 403
