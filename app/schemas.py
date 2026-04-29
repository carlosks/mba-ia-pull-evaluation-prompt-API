from pydantic import BaseModel, EmailStr

class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr

class Usuario(BaseModel):
    id: int
    nome: str
    email: EmailStr