from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import Role
from app.schemas.analysis import AnalysisSummaryResponse


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)
    role: Role | None = Field(Role.USER)


class UserUpdate(BaseModel):
    username: str = Field(min_length=3)
    role: Role | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class UserResponse(BaseModel):
    username: str


class UserDetailedResponse(BaseModel):
    id: UUID
    username: str
    analyses: list[AnalysisSummaryResponse]


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class PasswordRest(BaseModel):
    new_password: str = Field(min_length=8)
