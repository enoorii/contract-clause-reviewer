# app/services/analysis.py
from typing import cast
from uuid import UUID

from celery.result import AsyncResult
from celery.states import FAILURE, PENDING, STARTED, SUCCESS
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.core.celery import celery_app
from app.core.exceptions import OutOfRange
from app.core.filters.analysis import AnalysisFilters
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.infrastructure.storage import delete_file_async
from app.models.models import Analysis
from app.repositories.analysis_repositories import (
    get_analysis_by_id_repo,
    get_analysis_by_task_id_repo,
    get_user_analyses_count_repo,
    get_user_analyses_repo,
)
from app.schemas.analysis import AnalysisCreate
from app.tasks.document_tasks import analyze_legal_document_task

logger = get_logger(__name__)


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


async def get_analysis_status(
    task_id: str,
    db: DBSession,
) -> tuple[str, Analysis | None]:
    """
    Check Celery task status and retrieve saved analysis if completed.
    Returns (status, analysis_or_none).
    """
    task = AsyncResult(task_id, app=celery_app)
    state = task.state

    if state in (PENDING, STARTED):
        return "pending", None
    elif state == FAILURE:
        logger.error("Task %s failed: %s", task_id, task.info)
        return "failed", None
    elif state == SUCCESS:
        # The task itself saved the data; retrieve it from DB.
        analysis = await get_analysis_by_task_id_repo(
            task_id,
            db,
            options=[selectinload(cast(InstrumentedAttribute, Analysis.clauses))],
        )

        if analysis:
            return "completed", analysis
        else:
            # Should not happen if the task saved correctly, but handle gracefully.
            logger.warning("Task %s succeeded but no analysis found in DB", task_id)
            return "failed", None
    else:
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


async def delete_analysis_by_id(
    analysis_id: int,
    db: DBSession,
) -> bool:
    """
    Delete analysis and its associated resources.

    Args:
        analysis_id: ID of the analysis to delete
        db: Database session

    Returns:
        bool: True if analysis was deleted, False if not found

    Note:
        - Clauses are cascade-deleted by the database (passive_deletes=True)
        - Report file is deleted asynchronously before DB deletion
        - If file deletion fails, DB deletion still proceeds (fail-soft approach)
    """
    # Fetch the analysis
    analysis = await get_analysis_by_id_repo(analysis_id=analysis_id, db=db)

    if not analysis:
        return False

    # Clean up report file
    if analysis.report_stored and analysis.report_path:
        await delete_file_async(analysis.report_path)

    # Delete the analysis - database will cascade delete clauses
    await db.delete(analysis)

    logger.info(f"Successfully deleted analysis {analysis_id}")
    return True
