# app/services/analysis.py
from typing import cast
from uuid import UUID

from celery.result import AsyncResult
from celery.states import FAILURE, PENDING, STARTED, SUCCESS
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.core.celery import celery_app
from app.core.enums import RiskLevel
from app.core.exceptions import OutOfRange
from app.core.filters.analysis import AnalysisFilters
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.models.models import Analysis
from app.repositories.analysis_repositories import (
    create_analysis_repo,
    create_clauses_repo,
    get_analysis_by_id_repo,
    get_analysis_by_task_id_repo,
    get_user_analyses_count_repo,
    get_user_analyses_repo,
)
from app.schemas.analysis import AnalysisCreate
from app.tasks.document_tasks import analyze_legal_document_task

logger = get_logger(__file__)


async def queue_analysis_task(
    user_id: UUID,
    analysis_data: AnalysisCreate,
) -> str:
    """
    Queue the Celery task with the document data.
    Returns the Celery task ID.
    """
    task = analyze_legal_document_task.delay(  # type: ignore
        user_id=str(user_id),
        title=analysis_data.title,
        description=analysis_data.description,
        document_text=analysis_data.text,
    )
    task_id = task.id
    logger.info("Queued analysis task %s for user %s", task_id, user_id)
    return task_id


async def get_analysis_status_and_save_result(
    task_id: str,
    db: DBSession,
) -> tuple[str, Analysis | None]:
    """
    Check Celery task status, and if completed, save result to DB.
    Returns (status, analysis_or_none).
    """
    task = AsyncResult(task_id, app=celery_app)

    # Get the task state
    state = task.state

    if state in (PENDING, STARTED):
        return "pending", None
    elif state == FAILURE:
        logger.error("Task %s failed: %s", task_id, task.info)
        return "failed", None
    elif state == SUCCESS:
        try:
            result = task.result  # This is the dict returned by the task

            # Check if task returned error
            if isinstance(result, dict) and result.get("status") == "failed":
                logger.error(
                    "Task %s failed with error: %s",
                    task_id,
                    result.get("error"),
                )
                return "failed", None

            # Task succeeded, extract data
            analysis_result = (
                result.get("analysis_result") if isinstance(result, dict) else None
            )
            if not analysis_result:
                logger.error("Task %s returned no analysis result", task_id)
                return "failed", None

            # Check if analysis already exists (idempotency)
            existing = await get_analysis_by_task_id_repo(task_id, db)
            if existing:
                logger.info("Analysis already saved for task %s", task_id)
                return "completed", existing

            # Prepare clauses data
            clauses_data = []
            for clause_data in analysis_result.get("clauses", []):
                risk_level = clause_data.get("risk_level", "average")
                # Map to enum
                risk_map = {
                    "low": RiskLevel.LOW,
                    "medium": RiskLevel.AVERAGE,
                    "average": RiskLevel.AVERAGE,
                    "high": RiskLevel.HIGH,
                    "critical": RiskLevel.CRITICAL,
                }
                risk_level_enum = risk_map.get(risk_level.lower(), RiskLevel.AVERAGE)
                clauses_data.append(
                    {
                        "clause_type": clause_data.get("clause_type", ""),
                        "summary": clause_data.get("summary", ""),
                        "risk_level": risk_level_enum,
                        "key_terms": clause_data.get("key_terms", []),
                        "suggested_actions": clause_data.get("suggested_actions", []),
                    }
                )

            # Create Analysis record
            analysis = await create_analysis_repo(
                user_id=UUID(result["user_id"]),
                task_id=task_id,
                title=result["title"],
                description=result.get("description"),
                text=result["document_text"],
                document_summary=analysis_result.get("document_summary", ""),
                document_type=analysis_result.get("document_type", ""),
                overall_risk_score=analysis_result.get("overall_risk_score", 0),
                recommendations=analysis_result.get("recommendations", []),
                db=db,
            )

            # Create Clause records
            if clauses_data:
                await create_clauses_repo(
                    analysis_id=analysis.id,
                    clauses_data=clauses_data,
                    db=db,
                )

            await db.commit()

            logger.info(
                "Saved analysis %d for task %s",
                analysis.id,
                task_id,
            )
            return "completed", analysis

        except Exception as e:
            logger.error(
                "Failed to save analysis result for task %s: %s",
                task_id,
                str(e),
                exc_info=True,
            )
            return "failed", None
    else:
        # Unknown state
        logger.warning("Unknown task state for task %s: %s", task_id, state)
        return "pending", None


async def get_user_analyses(
    user_id: UUID,
    db: DBSession,
    filters: AnalysisFilters,
):
    """
    Get analyses for a user with filtering, sorting, and pagination.
    Returns a paginated response dict.
    """
    # Get total count
    total = await get_user_analyses_count_repo(filters, user_id, db)

    # Validate page
    assert isinstance(filters.size, int) and isinstance(filters.page, int)
    pages = (total + filters.size - 1) // filters.size if total > 0 else 1
    max_page = pages

    if filters.page > max_page and total > 0:
        raise OutOfRange(
            f"Page {filters.page} not found. Max page is {max_page}",
        )

    # Get items
    items = await get_user_analyses_repo(filters=filters, user_id=user_id, db=db)

    return {
        "items": items,
        "total": total,
        "page": filters.page,
        "size": filters.size,
        "pages": pages,
    }


async def get_analysis_detail(
    analysis_id: int,
    db: DBSession,
) -> Analysis | None:
    """Get a single analysis with all clauses."""
    return await get_analysis_by_id_repo(
        analysis_id,
        db,
        options=[selectinload(cast(InstrumentedAttribute, Analysis.clauses))],
    )
