from pydantic import BaseModel


class BugInput(BaseModel):
    bug: str


class UserStoryInput(BaseModel):
    user_story: str