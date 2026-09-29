from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models
from app.config import RATE_LIMIT_LOGIN, RATE_LIMIT_REGISTER
from app.rate_limit import limiter
from app.schemas.auth import UserCreate, UserOut, Token
from app.security import create_access_token, get_current_user, get_db
from app.services.usage_service import (
    ensure_user_plan_defaults,
    get_usage_summary,
    get_plan_limit,
)


router = APIRouter()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)


# Hash usado quando o e-mail não existe, para que o tempo de resposta do
# login seja o mesmo e não revele quais e-mails estão cadastrados.
_DUMMY_HASH = pwd_context.hash("senha-inexistente-para-equalizar-tempo")

INVALID_LOGIN_MESSAGE = "E-mail ou senha inválidos."


def build_user_out(db: Session, user: models.User) -> dict:
    """
    Monta a resposta pública do usuário com plano e uso mensal.
    """
    user = ensure_user_plan_defaults(db, user)
    usage = get_usage_summary(db, user)

    return {
        "id": user.id,
        "email": user.email,
        "plan": usage["plan"],
        "monthly_generation_limit": usage["monthly_generation_limit"],
        "monthly_usage": usage["monthly_usage"],
        "remaining_generations": usage["remaining_generations"],
        "is_active": bool(user.is_active),
        "is_admin": bool(user.is_admin),
    }


@router.post("/register", response_model=UserOut)
@limiter.limit(RATE_LIMIT_REGISTER)
def register(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Usuário já existe",
        )

    default_plan = "free"

    new_user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password),
        plan=default_plan,
        monthly_generation_limit=get_plan_limit(default_plan),
        is_active=True,
        is_admin=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return build_user_out(db, new_user)


@router.post("/login", response_model=Token)
@limiter.limit(RATE_LIMIT_LOGIN)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()

    if not user:
        verify_password(form_data.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail=INVALID_LOGIN_MESSAGE)

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail=INVALID_LOGIN_MESSAGE)

    # Só informamos que a conta está inativa depois de a senha ser validada.
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Usuário inativo.",
        )

    ensure_user_plan_defaults(db, user)

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserOut)
def me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(
        models.User.id == current_user.id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado.",
        )

    return build_user_out(db, user)