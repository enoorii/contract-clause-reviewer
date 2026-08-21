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
from app.services.analysis import (
    get_analysis_detail,
    get_analysis_status,
    get_user_analyses,
    queue_analysis_task,
)

logger = get_logger(__file__)

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


@router.get("/status/{task_id}")
async def get_analysis_status_endpoint(
    task_id: str,
    user: ActiveUserRateLimit,  # your authentication dependency
    db: DBSession,
):
    # (Optional) Verify ownership – check if analysis belongs to user
    analysis = await get_analysis_by_task_id_repo(task_id, db)
    if analysis and analysis.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    status, analysis = await get_analysis_status(task_id, db)

    if status == "pending":
        return {"status": "pending", "task_id": task_id}
    elif status == "failed":
        return {"status": "failed", "task_id": task_id, "error": "Task failed"}
    elif status == "completed" and analysis:
        return AnalysisStatusResponse(
            task_id=task_id,
            status="completed",
            analysis=AnalysisDetailedResponse.model_validate(analysis),
        )
    else:
        return {"status": "unknown", "task_id": task_id}


@router.get("/", response_model=list[AnalysisSummaryResponse])
async def list_analyses(
    user: ActiveUserAnalysisRateLimit,
    db: DBSession,
    filters: Annotated[AnalysisFilters, Query()],
):
    """List all analyses for the current user."""
    result = await get_user_analyses(user_id=user.id, db=db, filters=filters)
    return result["items"]


@router.get("/{analysis_id}", response_model=AnalysisDetailedResponse)
async def get_analysis(
    analysis_id: int,
    user: ActiveUserAnalysisRateLimit,
    db: DBSession,
):
    """Get detailed analysis by ID (only if owned by current user)."""
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return analysis
