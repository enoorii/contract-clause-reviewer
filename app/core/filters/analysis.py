from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Sort(StrEnum):
    ASC = "asc"
    DESC = "desc"


class AnalysisSortBy(StrEnum):
    CREATED_AT = "created_at"
    TITLE = "title"
    OVERALL_RISK_SCORE = "overall_risk_score"
    DOCUMENT_TYPE = "document_type"


class AnalysisFilters(BaseModel):
    page: int | None = Field(default=1, ge=1, description="Page number")
    size: int | None = Field(default=10, ge=1, le=100, description="Items per page")
    search: str | None = Field(default=None, description="Search for analyses by title")
    sort: Sort | None = Field(default=Sort.DESC)
    sort_by: AnalysisSortBy | None = Field(
        default=AnalysisSortBy.CREATED_AT, description="Field to sort by"
    )
    document_type: str | None = Field(
        default=None, description="Filter by document type"
    )
    min_risk_score: int | None = Field(
        default=None, ge=1, le=10, description="Minimum risk score"
    )
    max_risk_score: int | None = Field(
        default=None, ge=1, le=10, description="Maximum risk score"
    )
    from_date: datetime | None = Field(default=None, description="Filter from date")
    to_date: datetime | None = Field(default=None, description="Filter to date")

    @field_validator("sort", "sort_by", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        return None if v == "" else v
