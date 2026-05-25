from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.security import get_current_user, get_db
from app.schemas.admin import (
    AdminUserOut,
    AdminUsersResponse,
    UpdateUserAdminRequest,
    UpdateUserPlanRequest,
    UpdateUserStatusRequest,
)
from app.services.usage_service import get_plan_limit


router = APIRouter(
    tags=["Admin"],
)


def require_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Garante que apenas usuários administradores acessem rotas /admin.
    """

    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Usuário inativo.",
        )

    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Acesso permitido apenas para administradores.",
        )

    return current_user


@router.get("/users", response_model=AdminUsersResponse)
def list_users(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Lista todos os usuários cadastrados.
    """

    users = db.query(models.User).order_by(models.User.id.asc()).all()

    return {
        "users": users
    }


@router.put("/users/{user_id}/plan", response_model=AdminUserOut)
def update_user_plan(
    user_id: int,
    payload: UpdateUserPlanRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Altera o plano comercial de um usuário.
    """

    allowed_plans = {
        "free",
        "pro",
        "team",
        "admin",
    }

    plan = payload.plan.lower().strip()

    if plan not in allowed_plans:
        raise HTTPException(
            status_code=400,
            detail="Plano inválido. Use: free, pro, team ou admin.",
        )

    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado.",
        )

    user.plan = plan
    user.monthly_generation_limit = get_plan_limit(plan)

    if plan == "admin":
        user.is_admin = True
        user.monthly_generation_limit = -1

    if plan != "admin" and user.is_admin:
        user.is_admin = False

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.put("/users/{user_id}/status", response_model=AdminUserOut)
def update_user_status(
    user_id: int,
    payload: UpdateUserStatusRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Ativa ou desativa um usuário.
    """

    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado.",
        )

    user.is_active = payload.is_active

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.put("/users/{user_id}/admin", response_model=AdminUserOut)
def update_user_admin(
    user_id: int,
    payload: UpdateUserAdminRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Promove ou remove privilégios administrativos de um usuário.
    """

    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado.",
        )

    user.is_admin = payload.is_admin

    if payload.is_admin:
        user.plan = "admin"
        user.monthly_generation_limit = -1
    elif user.plan == "admin":
        user.plan = "free"
        user.monthly_generation_limit = get_plan_limit("free")

    db.add(user)
    db.commit()
    db.refresh(user)

    return user