from pydantic import BaseModel, Field

class UsuarioCreate(BaseModel):
    nome: str
    email: str = Field(..., pattern=r"^.+@.+\..+$")


class Usuario(BaseModel):
    id: int
    nome: str
    email: str

    class Config:
        from_attributes = True