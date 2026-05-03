from fastapi import FastAPI, Request
from app.routes import auth, users

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)