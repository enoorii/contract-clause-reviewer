# app/api/v1/endpoints/analysis.py

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.deps import ActiveUser
from app.core.filters.analysis import AnalysisFilters
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisDetailedResponse,
    AnalysisStatusResponse,
    AnalysisSummaryResponse,
)
from app.services.analysis import (
    get_analysis_detail,
    get_analysis_status_and_save_result,
    get_user_analyses,
    queue_analysis_task,
)

logger = get_logger(__file__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/analyze", response_model=dict)
async def analyze_document(
    *,
    user: ActiveUser,
    analysis_data: AnalysisCreate,
    db: DBSession,
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


@router.get("/analyze/{task_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    task_id: str,
    db: DBSession,
    request: Request,
):
    """Get status of analysis task and retrieve result when completed."""
    client_ip = request.client.host if request.client else None
    logger.debug("Status check for task %s from %s", task_id, client_ip)

    try:
        status_str, analysis = await get_analysis_status_and_save_result(
            task_id=task_id, db=db
        )

        if status_str in ("pending", "processing"):
            return AnalysisStatusResponse(task_id=task_id, status=status_str)

        if status_str == "failed":
            return AnalysisStatusResponse(
                task_id=task_id,
                status="failed",
                error="Analysis task failed",
            )

        # Completed
        if analysis is None:
            return AnalysisStatusResponse(
                task_id=task_id,
                status="failed",
                error="No analysis found for this task",
            )

        detailed = AnalysisDetailedResponse.model_validate(analysis)
        return AnalysisStatusResponse(
            task_id=task_id,
            status="completed",
            analysis=detailed,
        )

    except Exception as e:
        logger.error("Error checking status for task %s: %s", task_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task status",
        )


@router.get("/", response_model=list[AnalysisSummaryResponse])
async def list_analyses(
    user: ActiveUser, db: DBSession, filters: Annotated[AnalysisFilters, Query()]
):
    """List all analyses for the current user."""
    result = await get_user_analyses(user_id=user.id, db=db, filters=filters)
    return result["items"]


@router.get("/{analysis_id}", response_model=AnalysisDetailedResponse)
async def get_analysis(
    analysis_id: int,
    user: ActiveUser,
    db: DBSession,
):
    """Get detailed analysis by ID (only if owned by current user)."""
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return analysis
