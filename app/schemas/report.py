from pydantic import BaseModel, ConfigDict

from app.schemas.base import TaskStatus


class ReportStatusResponse(BaseModel):
    """Status response for report generation task."""

    task_id: str
    status: TaskStatus
    download_url: str | None = None  # ✅ Only present when completed
    error: str | None = None  # ✅ Only present when failed

    model_config = ConfigDict(from_attributes=True)
