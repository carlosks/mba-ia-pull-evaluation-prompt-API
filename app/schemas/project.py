from pydantic import BaseModel
from typing import Optional


class ProjectOut(BaseModel):
    id: int
    bug: str
    user_story: str
    code: str
    owner_id: Optional[int] = None

    model_config = {
        "from_attributes": True
    }