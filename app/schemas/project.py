from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# =========================
# INPUT (BUG)
# =========================
class BugRequest(BaseModel):
    description: str


# =========================
# OUTPUT PRINCIPAL
# =========================
class ProjectOut(BaseModel):
    id: int
    bug: str
    user_story: str
    code: str
    score: str | None = None
    status: str | None = None

    model_config = {
        "from_attributes": True
    }


# =========================
# DETALHE COMPLETO
# =========================
class ProjectDetail(BaseModel):
    id: int
    bug: str
    user_story: str
    acceptance_criteria: Optional[str]
    code: str
    score: Optional[str]
    status: Optional[str]
    zip_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# HISTÓRICO (LISTAGEM)
# =========================
class ProjectHistory(BaseModel):
    id: int
    bug: str
    score: Optional[str]
    status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True