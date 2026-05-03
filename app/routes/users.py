from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.schemas.auth import UserOut
from app.security import get_current_user
from app.deps import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user