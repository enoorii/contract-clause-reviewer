# app/services/reports.py (updated)

from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from celery.result import AsyncResult
from celery.states import FAILURE, PENDING, STARTED, SUCCESS
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.core.celery import celery_app
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.models.models import Analysis
from app.repositories.analysis_repositories import (
    get_analysis_by_id_repo,
)
from app.services.analysis import get_analysis_detail
from app.tasks.report_tasks import create_report_pdf

logger = get_logger(__name__)


async def queue_report_generation(
    analysis_id: int, user_id: UUID, db: DBSession
) -> str:
    """Queue report generation and store task ID."""
    # Load analysis with clauses
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if not analysis:
        raise ValueError("Analysis not found")

    # Check if report already exists (optional)
    if (
        analysis.report_stored
        and analysis.report_path
        and Path(analysis.report_path).exists()
    ):
        logger.info("Report already exists for analysis %d", analysis_id)
        return "already_exists"

    # Build analysis data dictionary explicitly, including clauses
    analysis_data = {
        "id": analysis.id,
        "title": analysis.title,
        "description": analysis.description,
        "text": analysis.text,
        "document_summary": analysis.document_summary,
        "document_type": analysis.document_type,
        "overall_risk_score": analysis.overall_risk_score,
        "recommendations": analysis.recommendations,
        "clauses": [
            {
                "clause_type": clause.clause_type,
                "summary": clause.summary,
                "risk_level": clause.risk_level.value,  # e.g., "low", "average"
                "key_terms": clause.key_terms,
                "suggested_actions": clause.suggested_actions,
            }
            for clause in analysis.clauses
        ],
        "created_at": analysis.created_at,
    }

    # Queue the task
    task = create_report_pdf.delay(analysis_data=analysis_data)
    task_id = task.id

    # Store task ID immediately so status endpoint can find the analysis
    analysis.report_task_id = task_id
    await db.commit()

    logger.info("Queued report task %s for analysis %d", task_id, analysis_id)
    return task_id


async def get_report_status(
    task_id: str,
    db: DBSession,
) -> dict:
    """
    Check Celery task status and retrieve analysis from DB if completed.
    If task is SUCCESS but DB not updated (e.g., due to a race), we update it now.
    """
    task = AsyncResult(task_id, app=celery_app)
    state = task.state

    if state in (PENDING, STARTED):
        logger.debug("Task %s is %s", task_id, state)
        return {"status": state.lower()}

    if state == FAILURE:
        logger.error("Report task %s failed: %s", task_id, task.info)
        return {"status": "failed", "error": str(task.info)}

    if state == SUCCESS:
        result = task.result
        if not isinstance(result, dict) or result.get("status") == "failed":
            error = (
                result.get("error", "Unknown error")
                if isinstance(result, dict)
                else "Invalid result"
            )
            logger.error("Report task %s returned failure: %s", task_id, error)
            return {"status": "failed", "error": error}

        # Task succeeded; get analysis_id from result
        analysis_id = result.get("analysis_id")
        if not analysis_id:
            logger.error("Task %s result missing analysis_id", task_id)
            return {"status": "failed", "error": "Incomplete result"}

        # Retrieve analysis from DB (with clauses)
        analysis = await get_analysis_by_id_repo(
            analysis_id,
            db,
            options=[selectinload(cast(InstrumentedAttribute, Analysis.clauses))],
        )
        if not analysis:
            logger.error("Analysis %d not found for task %s", analysis_id, task_id)
            return {"status": "failed", "error": "Analysis not found"}

        # If DB already updated, great
        if analysis.report_stored and analysis.report_path:
            file_path = Path(analysis.report_path)
            if file_path.exists():
                return {
                    "status": "completed",
                    "file_path": str(file_path),
                    "analysis_id": analysis_id,
                }
            else:
                logger.error("Report file %s missing", file_path)
                return {"status": "failed", "error": "Report file missing"}

        # DB not updated – fallback: update from task result
        logger.warning(
            "Task %s succeeded but DB not updated; performing fallback update", task_id
        )
        file_path = result.get("file_path")
        if not file_path:
            return {"status": "failed", "error": "No file_path in result"}

        # Update DB now

        analysis.report_stored = True
        analysis.report_path = str(file_path)
        analysis.report_generated_at = datetime.now(UTC)  # ensure import
        await db.commit()
        await db.refresh(analysis)

        logger.info("Fallback update: analysis %d set with report path", analysis_id)
        return {
            "status": "completed",
            "file_path": str(file_path),
            "analysis_id": analysis_id,
        }

    # Unknown state
    logger.warning("Unknown task state for task %s: %s", task_id, state)
    return {"status": "pending"}
