from fastapi import FastAPI, HTTPException
from app.schemas import UsuarioCreate, Usuario
from app.service import criar_usuario

app = FastAPI(
    title="API de Usuários",
    description="API gerada automaticamente via pipeline de IA",
    version="1.0.0"
)


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/usuarios", response_model=Usuario)
def criar(usuario: UsuarioCreate):
    try:
        return criar_usuario(usuario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))