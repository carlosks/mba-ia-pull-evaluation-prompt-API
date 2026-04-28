from sqlalchemy.orm import Session
from app import models, schemas

def criar_usuario(db: Session, usuario: schemas.UsuarioCreate):
    db_usuario = models.Usuario(
        nome=usuario.nome,
        email=usuario.email
    )

    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)

    return db_usuario


def listar_usuarios(db: Session):
    return db.query(models.Usuario).all()