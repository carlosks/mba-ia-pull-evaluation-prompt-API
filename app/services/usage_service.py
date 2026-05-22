from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


PLAN_LIMITS = {
    "free": 5,
    "pro": 100,
    "team": 1000,
    "admin": -1,  # ilimitado
}


def get_plan_limit(plan: str) -> int:
    """
    Retorna o limite mensal de gerações conforme o plano.
    """
    normalized_plan = (plan or "free").lower().strip()
    return PLAN_LIMITS.get(normalized_plan, PLAN_LIMITS["free"])


def get_month_range(reference_date: datetime | None = None) -> tuple[datetime, datetime]:
    """
    Retorna o início e o fim do mês atual.
    """
    now = reference_date or datetime.utcnow()

    start = datetime(
        year=now.year,
        month=now.month,
        day=1,
    )

    if now.month == 12:
        end = datetime(
            year=now.year + 1,
            month=1,
            day=1,
        )
    else:
        end = datetime(
            year=now.year,
            month=now.month + 1,
            day=1,
        )

    return start, end


def count_monthly_usage(
    db: Session,
    user_id: int,
    reference_date: datetime | None = None,
) -> int:
    """
    Conta quantas gerações com sucesso o usuário fez no mês atual.
    """
    start, end = get_month_range(reference_date)

    return (
        db.query(models.UsageLog)
        .filter(models.UsageLog.user_id == user_id)
        .filter(models.UsageLog.status == "success")
        .filter(models.UsageLog.created_at >= start)
        .filter(models.UsageLog.created_at < end)
        .count()
    )


def get_usage_summary(
    db: Session,
    user: models.User,
) -> dict:
    """
    Retorna resumo de uso do usuário autenticado.
    """
    plan = (user.plan or "free").lower().strip()

    if user.is_admin:
        plan = "admin"

    limit = user.monthly_generation_limit

    if limit is None:
        limit = get_plan_limit(plan)

    if user.is_admin:
        limit = -1

    monthly_usage = count_monthly_usage(db, user.id)

    if limit == -1:
        remaining = -1
    else:
        remaining = max(limit - monthly_usage, 0)

    return {
        "plan": plan,
        "monthly_generation_limit": limit,
        "monthly_usage": monthly_usage,
        "remaining_generations": remaining,
    }


def ensure_user_plan_defaults(
    db: Session,
    user: models.User,
) -> models.User:
    """
    Garante valores padrão de plano para usuários antigos.
    """
    changed = False

    if not user.plan:
        user.plan = "free"
        changed = True

    if user.monthly_generation_limit is None:
        user.monthly_generation_limit = get_plan_limit(user.plan)
        changed = True

    if user.is_active is None:
        user.is_active = True
        changed = True

    if user.is_admin is None:
        user.is_admin = False
        changed = True

    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def assert_user_can_generate(
    db: Session,
    user: models.User,
) -> dict:
    """
    Verifica se o usuário ainda pode gerar projetos no mês atual.

    Se o limite for atingido, lança HTTPException 429.
    """
    user = ensure_user_plan_defaults(db, user)

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Usuário inativo.",
        )

    summary = get_usage_summary(db, user)

    limit = summary["monthly_generation_limit"]
    usage = summary["monthly_usage"]

    if limit != -1 and usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Limite mensal do plano {summary['plan']} atingido. "
                f"Uso atual: {usage}/{limit}."
            ),
        )

    return summary


def register_usage(
    db: Session,
    user: models.User,
    endpoint: str,
    project_name: str | None = None,
    status: str = "success",
) -> models.UsageLog:
    """
    Registra uma tentativa de geração.
    """
    usage = models.UsageLog(
        user_id=user.id,
        endpoint=endpoint,
        project_name=project_name,
        status=status,
    )

    db.add(usage)
    db.commit()
    db.refresh(usage)

    return usage