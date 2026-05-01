from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# IMPORT DAS ROTAS
from app.routes.generate import router as generate_router

# =========================
# APP
# =========================
app = FastAPI(
    title="Bug to API SaaS",
    description="Gera APIs completas a partir de bugs",
    version="2.0.0"
)

# =========================
# ROTAS
# =========================
app.include_router(generate_router)

# =========================
# STATIC (UI)
# =========================
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# =========================
# UI
# =========================
@app.get("/ui")
def ui():
    return FileResponse("app/static/index.html")

# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "Bug to API SaaS"
    }