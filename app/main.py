from fastapi import FastAPI
from app.schemas import UsuarioCreate, Usuario
from app.service import criar_usuario

app = FastAPI()

@app.post("/usuarios", response_model=Usuario)
def criar(usuario: UsuarioCreate):
    return criar_usuario(usuario)