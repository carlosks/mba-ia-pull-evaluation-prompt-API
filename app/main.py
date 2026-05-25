from app.routes.admin import router as admin_router

from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.services.db_migration_service import run_database_migrations


app = FastAPI(
    title="MBA IA - Bug Evaluation API",
    description=(
        "API para geração de User Stories, soluções técnicas, "
        "ZIPs e testes automatizados a partir de Bugs"
    ),
    version="1.0.0",
)


@app.on_event("startup")
def startup_event():
    """
    Executa migrações simples ao iniciar a aplicação.

    Garante compatibilidade entre:
    - SQLite local
    - PostgreSQL no Render via DATABASE_URL
    """
    run_database_migrations()


@app.get("/")
def root():
    return {
        "msg": "SaaS rodando 🚀",
        "name": "MBA IA - Bug Evaluation API",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])