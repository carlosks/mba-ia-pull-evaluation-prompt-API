from pydantic import BaseModel, EmailStr


class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    plan: str
    monthly_generation_limit: int
    is_active: bool
    is_admin: bool

    model_config = {
        "from_attributes": True
    }


class AdminUsersResponse(BaseModel):
    users: list[AdminUserOut]


class UpdateUserPlanRequest(BaseModel):
    plan: str


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class UpdateUserAdminRequest(BaseModel):
    is_admin: bool