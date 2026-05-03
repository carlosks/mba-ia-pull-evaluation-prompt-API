from fastapi import APIRouter, Depends

from app.schemas.auth import UserOut
from app.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return current_user