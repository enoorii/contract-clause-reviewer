# app/schemas/analysis.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RiskLevel


class AnalysisCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = Field(default=None)
    text: str = Field(description="document text")


class ClauseResponse(BaseModel):
    id: int
    clause_type: str
    summary: str
    risk_level: RiskLevel
    key_terms: list[str]
    suggested_actions: list[str]

    model_config = ConfigDict(from_attributes=True)


class AnalysisDetailedResponse(BaseModel):
    id: int
    title: str
    description: str | None
    text: str
    document_summary: str
    document_type: str
    overall_risk_score: int
    recommendations: list[str]
    clauses: list[ClauseResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisSummaryResponse(BaseModel):
    id: int
    title: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    analysis: AnalysisDetailedResponse | None = None
    error: str | None = None
