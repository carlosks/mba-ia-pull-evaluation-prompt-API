from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext

from app.database import SessionLocal
from app import models
from app.schemas.auth import UserCreate, UserOut, Token
from app.security import create_access_token


router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str):
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain[:72], hashed)


# REGISTER
@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()

    if user:
        raise HTTPException(status_code=400, detail="Usuário já existe")

    new_user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# LOGIN
@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.email == form_data.username
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Senha inválida")

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }