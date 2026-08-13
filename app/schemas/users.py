from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlmodel import asc, col, desc
from sqlmodel.sql.expression import SelectOfScalar

from app.core.enums import Role
from app.models.models import User
from app.schemas.analysis import AnalysisSummaryResponse
from app.schemas.base import StrongPassword


class Sort(StrEnum):
    ASC = "asc"
    DESC = "desc"


class SortBy(StrEnum):
    CREATED_AT = "created_at"


class UserFilters(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Items per page")
    search: str | None = Field(
        default=None, description="Search for tasks with this string"
    )
    sort: Sort | None = Field(default=Sort.DESC)
    sort_by: SortBy | None = Field(
        default=SortBy.CREATED_AT, description="Field to sort by"
    )
    role: Role | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    from_date: datetime | None = Field(default=None)
    to_date: datetime | None = Field(default=None)

    def apply_to_query(self, stm: SelectOfScalar):
        """Apply all filters to query"""
        if self.search:
            search_pattern = f"%{self.search}%"
            stm = stm.where(col(User.username).ilike(search_pattern))
        if self.from_date:
            from_date = self.from_date
            if from_date.tzinfo is None:
                from_date = from_date.replace(tzinfo=UTC)
            stm = stm.where(User.created_at >= from_date)
        if self.to_date:
            to_date = self.to_date
            if to_date.tzinfo is None:
                to_date = to_date.replace(tzinfo=UTC)
            stm = stm.where(User.created_at <= to_date)
        return stm

    def apply_ordering(self, stm: SelectOfScalar) -> SelectOfScalar:
        """Apply sorting/ordering to query"""
        order_col = User.created_at

        if self.sort == Sort.ASC:
            return stm.order_by(asc(order_col))
        else:
            return stm.order_by(desc(order_col))

    @field_validator("role", "is_active", "sort_by", "sort", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        return None if v == "" else v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    password: StrongPassword
    role: Role = Field(default=Role.USER)


class UserUpdate(BaseModel):
    username: str = Field(min_length=3)
    role: Role | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class UserResponse(BaseModel):
    id: UUID
    username: str


class UserDetailedResponse(BaseModel):
    id: UUID
    username: str
    analyses: list[AnalysisSummaryResponse] | None = Field(default=None)


class PasswordChange(BaseModel):
    old_password: str
    new_password: StrongPassword


class PasswordRest(BaseModel):
    new_password: StrongPassword


class LoginResponse(BaseModel):
    username: str
    access_token: str
    refresh_token: str
    must_change_password: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str
