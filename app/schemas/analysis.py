from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RiskLevel


class AnalysisCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = Field(default=None)

    text: str = Field(description="document text")


class AnalysisSummaryResponse(BaseModel):
    id: int
    title: str


class RiskResponse(BaseModel):
    """API response model for a risk."""

    id: int
    description: str
    risk_level: RiskLevel

    model_config = ConfigDict(from_attributes=True)


class AnalysisDetailedResponse(BaseModel):
    """Detailed analysis response for API consumers."""

    id: int
    title: str
    description: str | None = Field(default=None)
    text: str = Field(description="document text")
    risks: list[RiskResponse]  # ✅ Uses schema, not model
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
