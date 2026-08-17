# app/tasks/document_tasks.py

import asyncio
import logging
from typing import Optional

from celery import Task

from app.core.celery import celery_app
from app.services.document_analyzer import LegalDocumentAnalyzer

logger = logging.getLogger(__name__)


def run_async_analysis(analyzer, document_text, temperature):
    """Helper to run async analysis in sync context."""
    try:
        _ = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create one
        return asyncio.run(
            analyzer.analyze(
                document_text=document_text,
                temperature=temperature,
            )
        )
    else:
        # Already in async context (unlikely in Celery prefork)
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
    Celery task that runs the document analysis.
    Returns the analysis result dict for the service layer to persist.
    """
    logger.info(
        "Starting analysis task %s for user %s, document: %s",
        self.request.id,
        user_id,
        title,
    )

    try:
        # Initialize analyzer
        analyzer = LegalDocumentAnalyzer()

        # Run async analysis in sync context
        result = run_async_analysis(analyzer, document_text, temperature)

        # Convert result to dict for serialization
        result_dict = result.model_dump()

        logger.info(
            "Analysis task %s completed successfully for user %s",
            self.request.id,
            user_id,
        )

        # Return the result along with metadata
        return {
            "task_id": self.request.id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "document_text": document_text,
            "analysis_result": result_dict,
            "status": "completed",
        }

    except Exception as e:
        logger.error(
            "Analysis task %s failed for user %s: %s",
            self.request.id,
            user_id,
            str(e),
            exc_info=True,
        )
        # Return error info so service can handle it
        return {
            "task_id": self.request.id,
            "user_id": user_id,
            "status": "failed",
            "error": str(e),
        }
