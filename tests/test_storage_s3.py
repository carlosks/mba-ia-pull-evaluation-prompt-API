"""
Teste do armazenamento contra um servidor S3 real (moto em modo servidor),
usando o mesmo cliente boto3 configurado para produção.
"""

import shutil
import threading

import boto3
import pytest

moto_server = pytest.importorskip("moto.server")

from app.services import storage_service  # noqa: E402


@pytest.fixture
def s3_endpoint(monkeypatch):
    server = moto_server.ThreadedMotoServer(ip_address="127.0.0.1", port=0)
    server.start()
    host, port = server.get_host_and_port()
    endpoint = f"http://{host}:{port}"

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "teste")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "teste")
    boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1").create_bucket(Bucket="projetos")

    yield endpoint
    server.stop()


def test_projeto_sobrevive_ao_redeploy_via_s3(s3_endpoint, tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "GENERATED_PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(storage_service, "STORAGE_BUCKET", "projetos")
    monkeypatch.setattr(storage_service, "STORAGE_ENDPOINT_URL", s3_endpoint)
    monkeypatch.setattr(storage_service, "STORAGE_REGION", "us-east-1")
    monkeypatch.setattr(storage_service, "_client", None)
    monkeypatch.setattr(storage_service, "_missing_projects", set())

    project = tmp_path / "proj_solution_1"
    (project / "app").mkdir(parents=True)
    (project / "metadata.json").write_text('{"validation": {"status": "valid"}}', encoding="utf-8")
    (project / "app" / "main.py").write_text("print('oi')", encoding="utf-8")

    assert storage_service.persist_project("proj_solution_1") is True

    shutil.rmtree(project)  # simula o redeploy apagando o disco

    assert storage_service.ensure_local_project("proj_solution_1") is True
    assert '"valid"' in (project / "metadata.json").read_text(encoding="utf-8")
    assert (project / "app" / "main.py").read_text(encoding="utf-8") == "print('oi')"


def test_projeto_antigo_inexistente_nao_e_consultado_de_novo(s3_endpoint, tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "GENERATED_PROJECTS_DIR", str(tmp_path))
    monkeypatch.setattr(storage_service, "STORAGE_BUCKET", "projetos")
    monkeypatch.setattr(storage_service, "STORAGE_ENDPOINT_URL", s3_endpoint)
    monkeypatch.setattr(storage_service, "STORAGE_REGION", "us-east-1")
    monkeypatch.setattr(storage_service, "_client", None)
    monkeypatch.setattr(storage_service, "_missing_projects", set())

    calls = {"n": 0}
    real_client = storage_service._get_client()
    original = real_client.get_object

    def counting_get_object(**kwargs):
        calls["n"] += 1
        return original(**kwargs)

    monkeypatch.setattr(real_client, "get_object", counting_get_object)

    assert storage_service.ensure_local_project("projeto_antigo") is False
    assert storage_service.ensure_local_project("projeto_antigo") is False
    assert calls["n"] == 1
