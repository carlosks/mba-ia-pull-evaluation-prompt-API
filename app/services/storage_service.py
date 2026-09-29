"""
Armazenamento durável dos projetos gerados.

O disco local continua sendo a área de trabalho (é onde o gerador escreve
os arquivos), mas em hospedagens como o Render ele é apagado a cada deploy.
Quando STORAGE_BUCKET está configurado, cada projeto é copiado como .zip
para um armazenamento compatível com S3 (AWS S3, Cloudflare R2, MinIO) e
restaurado automaticamente quando alguém o acessa e ele não está no disco.

Sem STORAGE_BUCKET, as funções não fazem nada (modo só disco local).
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

from app.config import (
    GENERATED_PROJECTS_DIR,
    STORAGE_BUCKET,
    STORAGE_ENDPOINT_URL,
    STORAGE_PREFIX,
    STORAGE_REGION,
)

logger = logging.getLogger("app.storage")

_client = None


def storage_enabled() -> bool:
    return bool(STORAGE_BUCKET)


def _get_client():
    global _client

    if _client is None:
        import boto3  # importado só quando o armazenamento está ativo

        _client = boto3.client(
            "s3",
            endpoint_url=STORAGE_ENDPOINT_URL,
            region_name=STORAGE_REGION,
        )

    return _client


def _object_key(project_name: str) -> str:
    return f"{STORAGE_PREFIX}{project_name}.zip"


def _base_dir() -> Path:
    return Path(GENERATED_PROJECTS_DIR).resolve()


def _project_dir(project_name: str) -> Path | None:
    base = _base_dir()
    project_dir = (base / project_name).resolve()

    if project_dir == base or not project_dir.is_relative_to(base):
        return None

    return project_dir


def _zip_directory(directory: Path) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(directory).as_posix())

    return buffer.getvalue()


def _safe_extract(data: bytes, destination: Path) -> None:
    """Extrai o zip recusando caminhos que saiam da pasta de destino."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            target = (root / member.filename).resolve()

            if not target.is_relative_to(root):
                raise ValueError(f"Caminho inválido no pacote: {member.filename}")

            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))


def persist_project(project_name: str | None) -> bool:
    """
    Copia o projeto do disco local para o armazenamento durável.
    Retorna True se enviou. Falhas são registradas e não interrompem
    a geração (o projeto continua disponível no disco local).
    """
    if not storage_enabled() or not project_name:
        return False

    project_dir = _project_dir(project_name)

    if project_dir is None or not project_dir.is_dir():
        logger.warning("Projeto não encontrado para persistir: %s", project_name)
        return False

    try:
        _get_client().put_object(
            Bucket=STORAGE_BUCKET,
            Key=_object_key(project_name),
            Body=_zip_directory(project_dir),
            ContentType="application/zip",
        )
        return True
    except Exception:
        logger.exception("Falha ao enviar projeto %s para o armazenamento", project_name)
        return False


def ensure_local_project(project_name: str) -> bool:
    """
    Garante que o projeto esteja no disco local, baixando do
    armazenamento durável se necessário. Retorna True se está disponível.
    """
    project_dir = _project_dir(project_name)

    if project_dir is None:
        return False

    if project_dir.is_dir():
        return True

    if not storage_enabled():
        return False

    try:
        response = _get_client().get_object(
            Bucket=STORAGE_BUCKET,
            Key=_object_key(project_name),
        )
        _safe_extract(response["Body"].read(), project_dir)
        logger.info("Projeto restaurado do armazenamento: %s", project_name)
        return True
    except Exception:
        logger.exception("Falha ao restaurar projeto %s do armazenamento", project_name)
        return False
