"""
Fila de gerações em segundo plano.

A requisição HTTP cria o job e responde na hora com o id; a geração roda
num pool de threads desta mesma instância. O frontend consulta o status
até o job terminar.

Limitações desta primeira versão (documentadas de propósito):
- A fila vive no processo: com mais de uma instância, cada uma executa
  apenas os jobs que ela mesma recebeu. O estado fica no banco, então a
  consulta de status funciona de qualquer instância.
- Se o servidor reiniciar no meio de uma geração, o job é marcado como
  failed; os que ainda estavam na fila são reenviados no startup.
Para escalar horizontalmente, troque o executor por RQ/Celery com Redis
mantendo a mesma tabela generation_jobs.
"""

from __future__ import annotations

import json
import logging
import uuid
from concurrent.futures import Executor, ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.config import JOB_WORKERS, MAX_PENDING_JOBS_PER_USER
from app.database import SessionLocal
from app.services.usage_service import assert_user_can_generate

logger = logging.getLogger("app.jobs")

JOB_KINDS = {"generate", "generate-full", "generate-solution"}
PENDING_STATUSES = ("queued", "running")

# Substituíveis nos testes.
executor: Executor = ThreadPoolExecutor(
    max_workers=max(JOB_WORKERS, 1),
    thread_name_prefix="generation-job",
)
session_factory = SessionLocal


def _now() -> datetime:
    return datetime.now(timezone.utc)


def count_pending_jobs(db: Session, user_id: int) -> int:
    return (
        db.query(models.GenerationJob)
        .filter(models.GenerationJob.user_id == user_id)
        .filter(models.GenerationJob.status.in_(PENDING_STATUSES))
        .count()
    )


def create_job(db: Session, user: models.User, kind: str, bug: str) -> models.GenerationJob:
    if kind not in JOB_KINDS:
        raise HTTPException(status_code=400, detail="Tipo de geração inválido.")

    summary = assert_user_can_generate(db, user)
    pending = count_pending_jobs(db, user.id)

    if pending >= MAX_PENDING_JOBS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=(
                "Você já tem gerações em andamento. "
                "Aguarde terminarem antes de iniciar outra."
            ),
        )

    # Jobs pendentes também contam para a cota do mês, senão o usuário
    # poderia enfileirar várias gerações com só 1 crédito restante.
    limit = summary["monthly_generation_limit"]
    if limit != -1 and summary["monthly_usage"] + pending >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Limite mensal do plano {summary['plan']} atingido "
                "considerando as gerações em andamento."
            ),
        )

    job = models.GenerationJob(
        id=str(uuid.uuid4()),
        user_id=user.id,
        kind=kind,
        status="queued",
        bug=bug,
        created_at=_now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    executor.submit(run_job, job.id)

    return job


def run_job(job_id: str) -> None:
    """Executa um job. Roda numa thread do pool, com sessão própria."""
    # Import tardio: a lógica de geração vive nas rotas de projetos.
    from app.routes.projects import GENERATION_RUNNERS, execute_generation

    db = session_factory()

    try:
        job = db.get(models.GenerationJob, job_id)

        if job is None or job.status != "queued":
            return

        user = db.get(models.User, job.user_id)

        job.status = "running"
        job.started_at = _now()
        db.commit()

        try:
            result = execute_generation(job.kind, db, user, job.bug)
        except Exception as exc:
            error_id = uuid.uuid4().hex[:12]
            logger.exception("Job %s falhou [erro=%s]: %s", job_id, error_id, exc)

            db.rollback()
            job = db.get(models.GenerationJob, job_id)
            action = GENERATION_RUNNERS[job.kind][1]
            job.status = "failed"
            job.error_message = (
                f"Não foi possível {action}. Tente novamente em instantes. "
                f"Se o problema persistir, informe o código {error_id} ao suporte."
            )
            job.finished_at = _now()
            db.commit()
            return

        job.status = "succeeded"
        job.result_json = json.dumps(result, ensure_ascii=False, default=str)
        job.project_name = result.get("project_name")
        job.finished_at = _now()
        db.commit()

    except Exception:
        logger.exception("Erro inesperado ao processar o job %s", job_id)
    finally:
        db.close()


def recover_jobs_on_startup() -> None:
    """
    Chamado no startup: jobs que estavam rodando quando o servidor caiu
    são marcados como failed; os que estavam na fila são reenviados.
    """
    db = session_factory()

    try:
        interrupted = (
            db.query(models.GenerationJob)
            .filter(models.GenerationJob.status == "running")
            .all()
        )
        for job in interrupted:
            job.status = "failed"
            job.error_message = (
                "A geração foi interrompida por uma reinicialização do servidor. "
                "Ela não foi descontada da sua cota; tente novamente."
            )
            job.finished_at = _now()
        db.commit()

        queued_ids = [
            job_id
            for (job_id,) in db.query(models.GenerationJob.id)
            .filter(models.GenerationJob.status == "queued")
            .order_by(models.GenerationJob.created_at.asc())
            .all()
        ]
    finally:
        db.close()

    for job_id in queued_ids:
        executor.submit(run_job, job_id)

    if interrupted or queued_ids:
        logger.info(
            "Fila recuperada: %s interrompidos, %s reenviados",
            len(interrupted),
            len(queued_ids),
        )


def job_to_dict(job: models.GenerationJob) -> dict:
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "project_name": job.project_name,
        "error_message": job.error_message,
        "result": json.loads(job.result_json) if job.result_json else None,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
