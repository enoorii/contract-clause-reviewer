# app/api/v1/endpoints/analysis.py

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.filters.analysis import AnalysisFilters
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.infrastructure.redis.dependencies import (
    ActiveUserAnalysisRateLimit,
    ActiveUserRateLimit,
)
from app.repositories.analysis_repositories import get_analysis_by_task_id_repo
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisDetailedResponse,
    AnalysisStatusResponse,
    AnalysisSummaryResponse,
)
from app.schemas.base import PaginatedResponse, TaskStatus
from app.services.analysis import (
    delete_analysis_by_id,
    get_analysis_detail,
    get_analysis_status,
    get_user_analyses,
    queue_analysis_task,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/analyze", response_model=dict)
async def analyze_document(
    *,
    user: ActiveUserAnalysisRateLimit,
    analysis_data: AnalysisCreate,
    request: Request,
):
    """Queue document analysis as Celery task."""
    client_ip = request.client.host if request.client else None
    logger.info(
        "User %s from %s queued analysis for document: %s",
        user.username,
        client_ip,
        analysis_data.title,
    )

    try:
        task_id = await queue_analysis_task(
            user_id=user.id, analysis_data=analysis_data
        )

        logger.user_action(
            action="DOCUMENT_ANALYZE",
            username=user.username,
            request=request,
            metadata={"task_id": task_id, "title": analysis_data.title},
        )

        return {"task_id": task_id, "status": "queued"}

    except Exception as e:
        logger.error("Failed to queue analysis for user %s: %s", user.username, str(e))
        logger.user_action(
            action="DOCUMENT_ANALYZE",
            username=user.username,
            request=request,
            status="FAILED",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue analysis",
        )


@router.get("/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status_endpoint(
    task_id: str,
    user: ActiveUserRateLimit,
    db: DBSession,
):
    # Verify ownership
    analysis = await get_analysis_by_task_id_repo(task_id, db)
    if analysis and analysis.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    status, analysis_data = await get_analysis_status(task_id, db)

    # ✅ Unified return through response_model validation
    if status == TaskStatus.COMPLETED and analysis_data:
        return AnalysisStatusResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            analysis=AnalysisDetailedResponse.model_validate(analysis_data),
        )
    elif status == TaskStatus.FAILED:
        return AnalysisStatusResponse(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error="Task failed",
        )
    elif status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
        return AnalysisStatusResponse(
            task_id=task_id,
            status=status,
        )

    elif status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
        return AnalysisStatusResponse(
            task_id=task_id,
            status=status,
        )
    else:
        return AnalysisStatusResponse(
            task_id=task_id,
            status=TaskStatus.UNKNOWN,
        )


@router.get("", response_model=PaginatedResponse[AnalysisSummaryResponse])
async def list_analyses(
    user: ActiveUserRateLimit,
    db: DBSession,
    filters: Annotated[AnalysisFilters, Query()],
):
    """List all analyses for the current user."""
    result = await get_user_analyses(user_id=user.id, db=db, filters=filters)
    return result


@router.get("/{analysis_id}", response_model=AnalysisDetailedResponse)
async def get_analysis(
    analysis_id: int,
    user: ActiveUserRateLimit,
    db: DBSession,
):
    """Get detailed analysis by ID (only if owned by current user)."""
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return analysis


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: int,
    user: ActiveUserRateLimit,
    db: DBSession,
):
    """Delete analysis by ID (only if owned by current user)."""
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await delete_analysis_by_id(analysis_id=analysis.id, db=db)
