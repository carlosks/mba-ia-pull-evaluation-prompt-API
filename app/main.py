from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.routes.auth import router as auth_router
from app.routes.generate import router as generate_router


# ✅ criar app primeiro
app = FastAPI(
    title="Bug → User Story SaaS",
    version="1.0.0"
)


# rotas API
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(generate_router, prefix="/api", tags=["Generate"])


# root
@app.get("/")
def root():
    return {"msg": "SaaS rodando 🚀"}


# health
@app.get("/health")
def health():
    return {"status": "ok"}


# UI
@app.get("/ui")
def ui():
    return FileResponse("app/static/index.html")