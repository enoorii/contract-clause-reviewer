# app/tasks/report_tasks.py (updated)

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

from celery import Task
from weasyprint import HTML

from app.core.celery import celery_app
from app.core.config import PROJECT_ROOT, setting
from app.db.database import get_sync_db
from app.models.models import Analysis
from app.services.report_generator import generate_report_html

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="create_report_pdf",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
)
def create_report_pdf(
    self: Task,
    analysis_data: Dict[str, Any],
) -> dict:
    """
    Generate PDF report from analysis data, save to disk, and update DB.
    Uses a fixed filename: report_{analysis_id}.pdf (overwrites previous).
    """
    try:
        analysis_id = analysis_data.get("id")
        if not analysis_id:
            raise ValueError("analysis_id is required")

        logger.info(
            "Generating report for analysis %d (task: %s)", analysis_id, self.request.id
        )

        # Generate HTML and PDF
        html_content = generate_report_html(analysis_data)
        pdf_bytes = HTML(string=html_content).write_pdf()
        if pdf_bytes is None:
            raise ValueError("PDF generation returned None")

        # Determine reports directory
        reports_dir = (
            Path(setting.REPORTS_DIR)
            if hasattr(setting, "REPORTS_DIR")
            else Path(PROJECT_ROOT / "reports")
        )
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Use fixed filename (overwrites previous)
        filename = f"report_{analysis_id}.pdf"
        file_path = reports_dir / filename

        # Write PDF synchronously
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info(
            "PDF written for analysis %d at %s (%d bytes)",
            analysis_id,
            file_path,
            len(pdf_bytes),
        )

        # --- Update database ---
        with get_sync_db() as session:
            analysis = (
                session.query(Analysis).filter(Analysis.id == analysis_id).first()
            )
            if not analysis:
                error_msg = f"Analysis {analysis_id} not found in DB"
                logger.error(error_msg)
                return {
                    "analysis_id": analysis_id,
                    "task_id": self.request.id,
                    "status": "failed",
                    "error": error_msg,
                }

            # Update report fields
            analysis.report_stored = True
            analysis.report_path = str(file_path)
            analysis.report_generated_at = datetime.now(UTC)
            session.commit()
            logger.info(
                "Successfully updated analysis %d with report path", analysis_id
            )

        return {
            "analysis_id": analysis_id,
            "file_path": str(file_path),
            "task_id": self.request.id,
            "status": "completed",
        }

    except Exception as e:
        logger.error(
            "Report generation failed for analysis %s: %s",
            analysis_data.get("id"),
            str(e),
            exc_info=True,
        )
        return {
            "analysis_id": analysis_data.get("id"),
            "task_id": self.request.id,
            "status": "failed",
            "error": str(e),
        }
