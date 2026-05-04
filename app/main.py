from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router

from app.database import engine
from app import models

models.Base.metadata.create_all(bind=engine)


# 🔥 CRIAR APP PRIMEIRO
app = FastAPI(
    title="Bug → User Story SaaS",
    version="1.0.0"
)


# 🔗 ROTAS
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])


# ROOT
@app.get("/")
def root():
    return {"msg": "SaaS rodando 🚀"}


# HEALTH
@app.get("/health")
def health():
    return {"status": "ok"}


# UI
@app.get("/ui")
def ui():
    return FileResponse("app/static/index.html")