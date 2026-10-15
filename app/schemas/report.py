from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.base import TaskStatus


class ReportStatusResponse(BaseModel):
    """Status response for report generation task."""

    task_id: str
    status: TaskStatus
    download_url: str | None = None  # ✅ Only present when completed
    error: str | None = None  # ✅ Only present when failed

    model_config = ConfigDict(from_attributes=True)


class ReportGenerateResponse(BaseModel):
    """Response for POST /reports/{analysis_id}.

    A report is either already available, or was queued for generation.
    The `status` field is the discriminant; the other fields are populated
    accordingly.
    """

    status: Literal["queued", "ready"]
    task_id: str | None = None  # set iff status == "queued"
    status_url: str | None = None  # set iff status == "queued"
    download_url: str | None = None  # set iff status == "ready"

    model_config = ConfigDict(from_attributes=True)
