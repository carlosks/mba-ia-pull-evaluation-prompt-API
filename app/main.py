import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.config import CORS_ORIGINS, DOCS_ENABLED
from app.rate_limit import limiter
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.billing import router as billing_router
from app.routes.jobs import router as jobs_router
from app.routes.projects import router as projects_router
from app.services.jobs_service import recover_jobs_on_startup
from app.services.migration_service import run_startup_migrations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup_migrations()
    recover_jobs_on_startup()
    yield


app = FastAPI(
    title="MBA IA - Bug Evaluation API",
    description=(
        "API para geração de User Stories, soluções técnicas, "
        "critérios de aceitação e projetos gerados por IA."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)

# Limite de requisições (login, cadastro e geração).
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    response = JSONResponse(
        status_code=429,
        content={"detail": "Muitas tentativas em pouco tempo. Aguarde um minuto e tente novamente."},
    )
    return request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)

# CORS só para origens explicitamente configuradas.
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.url.path.startswith("/static/"):
        # Revalida sempre (usa ETag/Last-Modified): após um deploy o navegador
        # baixa a versão nova em vez de usar a cópia antiga do cache.
        response.headers["Cache-Control"] = "no-cache"
    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


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
app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
app.include_router(billing_router, prefix="/billing", tags=["Billing"])
