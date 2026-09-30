from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # Aceite dos Termos de Uso e da Política de Privacidade (obrigatório).
    accept_terms: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr

    plan: str = "free"
    monthly_generation_limit: int = 5
    monthly_usage: int = 0
    remaining_generations: int = 5

    is_active: bool = True
    is_admin: bool = False

    # True quando o usuário já aceitou a versão vigente dos termos.
    terms_accepted: bool = False

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    access_token: str
    token_type: str