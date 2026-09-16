from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from starlette.responses import RedirectResponse

from app.api.deps import DBSession
from app.infrastructure.logging import get_logger
from app.infrastructure.redis.dependencies import ActiveUserAnalysisRateLimit
from app.repositories.analysis_repositories import get_analysis_by_report_task_id
from app.schemas.base import TaskStatus
from app.schemas.report import ReportStatusResponse
from app.services.analysis import get_analysis_detail
from app.services.reports import (
    get_report_status,
    queue_report_generation,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/{analysis_id}", response_model=dict)
async def generate_report(
    analysis_id: int,
    user: ActiveUserAnalysisRateLimit,
    db: DBSession,
    request: Request,
):
    """Queue report generation for a specific analysis."""
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )
    if analysis.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Check if report already exists
    if (
        analysis.report_stored
        and analysis.report_path
        and Path(analysis.report_path).exists()
    ):
        logger.info("Report already exists for analysis %d", analysis_id)
        # Redirect to download endpoint
        return RedirectResponse(
            url=f"/api/v1/reports/download/{analysis_id}",
            status_code=303,  # See Other - forces GET to the download endpoint
        )

    # Queue new generation
    task_id = await queue_report_generation(
        analysis_id=analysis_id, user_id=user.id, db=db
    )

    logger.user_action(
        action="REPORT_GENERATE",
        username=user.username,
        request=request,
        metadata={"analysis_id": analysis_id, "task_id": task_id},
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "status_url": f"/api/reports/status/{task_id}",
    }


@router.get(
    "/status/{task_id}",
    response_model=ReportStatusResponse,  # ✅ Critical for accurate OpenAPI spec
)
async def get_report_status_endpoint(
    task_id: str,
    user: ActiveUserAnalysisRateLimit,
    db: DBSession,
):
    """Check status of report generation task."""
    # Verify ownership
    analysis = await get_analysis_by_report_task_id(task_id, db)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    if analysis.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    status_result = await get_report_status(task_id=task_id, db=db)
    current_status = status_result["status"]

    # ✅ Unified return through response_model - NO redirects
    if current_status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
        return ReportStatusResponse(
            task_id=task_id,
            status=current_status,
        )

    if current_status == "failed":
        return ReportStatusResponse(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=status_result.get("error", "Report generation failed"),
        )

    if current_status == "completed":
        file_path = status_result.get("file_path")
        if not file_path or not Path(file_path).exists():
            return ReportStatusResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error="Report file not found after completion",
            )

        # ✅ Return URL instead of redirecting
        return ReportStatusResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            download_url=f"/api/v1/reports/download/{analysis.id}",
        )

    # Unknown/fallback state
    return ReportStatusResponse(
        task_id=task_id,
        status=TaskStatus.UNKNOWN,
    )


@router.get("/download/{analysis_id}")
async def download_report(
    analysis_id: int,
    user: ActiveUserAnalysisRateLimit,
    db: DBSession,
):
    """
    Download an already generated report.
    """
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )
    if analysis.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if not analysis.report_stored or not analysis.report_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not generated yet",
        )
    file_path = Path(analysis.report_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file missing on server",
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"report_{analysis_id}.pdf",
    )
