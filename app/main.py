from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import Base, engine
from app.routes.generate import router as generate_router
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router

from app.routes.projects import router as projects_router
app.include_router(projects_router)


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bug to API SaaS",
    description="Gera APIs completas a partir de bugs",
    version="2.0.0"
)

app.include_router(generate_router)
app.include_router(auth_router)
app.include_router(users_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/ui")
def ui():
    return FileResponse("app/static/index.html")


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "Bug to API SaaS"
    }