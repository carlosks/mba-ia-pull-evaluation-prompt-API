from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router


app = FastAPI(
    title="MBA IA - Bug Evaluation API",
    description=(
        "API para geração de User Stories, soluções técnicas, "
        "ZIPs e testes automatizados a partir de Bugs"
    ),
    version="1.0.0",
)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/static/login.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])