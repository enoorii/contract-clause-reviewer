# app/tasks/document_tasks.py

import asyncio
import logging
from typing import Optional
from uuid import UUID

from celery import Task

from app.core.celery import celery_app
from app.core.enums import RiskLevel
from app.db.database import get_sync_db
from app.models.models import Analysis, Clause
from app.services.document_analyzer import LegalDocumentAnalyzer

logger = logging.getLogger(__name__)


def run_async_analysis(analyzer, document_text, temperature):
    """Helper to run async analysis in sync context."""
    try:
        _ = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            analyzer.analyze(
                document_text=document_text,
                temperature=temperature,
            )
        )
    else:
        raise RuntimeError("Cannot run async task in async context")


@celery_app.task(
    bind=True,
    name="analyze_legal_document",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
)
def analyze_legal_document_task(
    self: Task,
    user_id: str,
    title: str,
    description: Optional[str],
    document_text: str,
    temperature: float = 0.3,
) -> dict:
    """
    Celery task that runs the document analysis and persists results to DB.
    Returns a dict with status and metadata.
    """
    task_id = self.request.id
    logger.info(
        "Starting analysis task %s for user %s, document: %s",
        task_id,
        user_id,
        title,
    )

    try:
        # 1. Run the analysis
        analyzer = LegalDocumentAnalyzer()
        result = run_async_analysis(analyzer, document_text, temperature)
        result_dict = result.model_dump()

        # 2. Persist to database (synchronously)
        with get_sync_db() as session:
            # Idempotency: check if analysis already exists for this task
            existing = (
                session.query(Analysis).filter(Analysis.task_id == task_id).first()
            )
            if existing:
                logger.info("Analysis already saved for task %s, skipping", task_id)
                analysis_id = existing.id
            else:
                # Create Analysis record (without clauses first)
                analysis = Analysis(
                    user_id=UUID(user_id),
                    task_id=task_id,
                    title=title,
                    description=description,
                    text=document_text,
                    document_summary=result_dict.get("document_summary", ""),
                    document_type=result_dict.get("document_type", ""),
                    overall_risk_score=result_dict.get("overall_risk_score", 0),
                    recommendations=result_dict.get("recommendations", []),
                )
                session.add(analysis)
                session.commit()  # Get analysis.id
                session.refresh(analysis)
                analysis_id = analysis.id

                # Create Clause records with the analysis_id
                for clause_data in result_dict.get("clauses", []):
                    risk_level_str = clause_data.get("risk_level", "average")
                    risk_map = {
                        "low": RiskLevel.LOW,
                        "medium": RiskLevel.AVERAGE,
                        "average": RiskLevel.AVERAGE,
                        "high": RiskLevel.HIGH,
                        "critical": RiskLevel.CRITICAL,
                    }
                    risk_level = risk_map.get(risk_level_str.lower(), RiskLevel.AVERAGE)
                    clause = Clause(
                        analysis_id=analysis_id,
                        clause_type=clause_data.get("clause_type", ""),
                        summary=clause_data.get("summary", ""),
                        risk_level=risk_level,
                        key_terms=clause_data.get("key_terms", []),
                        suggested_actions=clause_data.get("suggested_actions", []),
                    )
                    session.add(clause)

                session.commit()
                logger.info(
                    "Saved analysis %d with clauses for task %s", analysis_id, task_id
                )

        # 3. Return success with metadata
        return {
            "task_id": task_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "document_text": document_text,
            "analysis_result": result_dict,
            "analysis_id": analysis_id,
            "status": "completed",
        }

    except Exception as e:
        logger.error(
            "Analysis task %s failed for user %s: %s",
            task_id,
            user_id,
            str(e),
            exc_info=True,
        )
        return {
            "task_id": task_id,
            "user_id": user_id,
            "status": "failed",
            "error": str(e),
        }
