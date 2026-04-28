from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')