from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, SECRET_KEY
from app.database import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# TOKEN
def create_access_token(data: dict):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": int(now.timestamp())})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


# USER AUTH
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_error = HTTPException(
        status_code=401,
        detail="Credenciais inválidas ou sessão expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)

    if payload is None:
        raise credentials_error

    email = payload.get("sub")

    if not email:
        raise credentials_error

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise credentials_error

    # Depois de uma troca de senha, tokens emitidos antes dela não valem mais.
    if user.password_changed_at is not None:
        changed_at = user.password_changed_at
        if changed_at.tzinfo is None:
            changed_at = changed_at.replace(tzinfo=timezone.utc)

        issued_at = payload.get("iat")
        if not isinstance(issued_at, (int, float)) or int(issued_at) < int(changed_at.timestamp()):
            raise credentials_error

    # Usuário desativado pelo admin perde o acesso imediatamente,
    # mesmo que ainda tenha um token válido.
    if user.is_active is False:
        raise HTTPException(status_code=403, detail="Usuário inativo.")

    return user
