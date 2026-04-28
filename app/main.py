from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app import models, schemas, service

# 🔥 cria tabelas automaticamente
models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# 🔹 dependência de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔹 criar usuário
@app.post("/usuarios", response_model=schemas.Usuario)
def criar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    return service.criar_usuario(db, usuario)


# 🔹 listar usuários
@app.get("/usuarios", response_model=list[schemas.Usuario])
def listar_usuarios(db: Session = Depends(get_db)):
    return service.listar_usuarios(db)