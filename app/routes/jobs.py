from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.config import RATE_LIMIT_GENERATE
from app.rate_limit import limiter
from app.security import get_current_user, get_db
from app.services import jobs_service

router = APIRouter(tags=["Jobs"])


class JobCreateRequest(BaseModel):
    kind: Literal["generate", "generate-full", "generate-solution"] = "generate-solution"
    bug: str = Field(..., min_length=5, max_length=20000)


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    project_name: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class JobListOut(BaseModel):
    jobs: List[JobOut]


@router.post("", response_model=JobOut, status_code=202)
@limiter.limit(RATE_LIMIT_GENERATE)
def create_job(
    request: Request,
    payload: JobCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Enfileira uma geração e responde imediatamente com o id do job.
    Consulte GET /jobs/{id} até o status ser succeeded ou failed.
    """
    job = jobs_service.create_job(db, current_user, payload.kind, payload.bug)
    return jobs_service.job_to_dict(job)


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    job = db.get(models.GenerationJob, job_id)

    # 404 também para job de outro usuário, para não revelar que existe.
    if job is None or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Geração não encontrada.")

    return jobs_service.job_to_dict(job)


@router.get("", response_model=JobListOut)
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jobs = (
        db.query(models.GenerationJob)
        .filter(models.GenerationJob.user_id == current_user.id)
        .order_by(models.GenerationJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"jobs": [jobs_service.job_to_dict(job) for job in jobs]}
