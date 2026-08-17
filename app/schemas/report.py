from pydantic import BaseModel, ConfigDict


class ReportStatusResponse(BaseModel):
    """Status response for report generation task."""

    task_id: str
    status: str  # pending, processing, completed, failed
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)
