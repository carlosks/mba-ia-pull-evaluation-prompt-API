from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


# =========================
# USER
# =========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


# =========================
# AUTH
# =========================

class Token(BaseModel):
    access_token: str
    token_type: str


# =========================
# BUG INPUT
# =========================

class BugRequest(BaseModel):
    description: str


# =========================
# PROJECT RESPONSE
# =========================

class ProjectResponse(BaseModel):
    id: int
    bug: str
    user_story: str
    score: Optional[str]
    status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# FULL PROJECT (DETALHADO)
# =========================

class ProjectDetail(BaseModel):
    id: int
    bug: str
    user_story: str
    acceptance_criteria: Optional[str]
    code: str
    score: Optional[str]
    status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# HISTORY
# =========================

class ProjectHistory(BaseModel):
    id: int
    bug: str
    score: Optional[str]
    status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True