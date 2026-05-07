from fastapi import FastAPI
from app.routes.api import router

app = FastAPI(title="Generated API")

app.include_router(router, prefix="/api", tags=["Generated"])

@app.get("/")
def root():
    return {"message": "API running 🚀"}
