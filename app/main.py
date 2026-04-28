from fastapi import FastAPI
from app.schemas import UserCreate
from app.service import create_user

app = FastAPI()

@app.post("/users/", response_model=UserCreate)
async def register_user(user: UserCreate):
    return create_user(user)