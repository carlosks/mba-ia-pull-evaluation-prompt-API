from fastapi import HTTPException
from app.schemas import UserCreate

users_db = []

def create_user(user: UserCreate):
    if any(u.email == user.email for u in users_db):
        raise HTTPException(status_code=400, detail="Email already registered")
    users_db.append(user)
    return user