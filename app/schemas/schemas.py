from typing import Generic, List, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.models import Risk

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    size: int
    total: int
    page: int
    pages: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    username: str


class UserDetailedResponse(BaseModel):
    id: UUID
    username: str
    analyses: List["AnalysisSummaryResponse"]


class AnalysisCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = Field(default=None)

    text: str = Field(description="document text")


class AnalysisSummaryResponse:
    id: int
    title: str


class AnalysisDetailedResponse:
    id: int
    title: str
    description: str | None = Field(default=None)

    text: str = Field(description="document text")

    risks: List[Risk]
