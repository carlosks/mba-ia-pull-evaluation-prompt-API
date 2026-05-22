from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


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

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    access_token: str
    token_type: str