from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models
from app.routes.projects import router as projects_router
from app.routes.auth import router as auth_router


# Cria as tabelas automaticamente no SQLite app.db
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="MBA IA - Prompt Evaluation API",
    description="API para geração de User Stories, soluções técnicas, ZIPs e testes automatizados a partir de Bugs",
    version="1.0.0",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restringir para o domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rotas
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(projects_router)


@app.get("/")
def root():
    return {"msg": "SaaS rodando 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}