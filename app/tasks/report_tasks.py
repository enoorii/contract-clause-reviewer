import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from celery import Task
from weasyprint import HTML

from app.core.celery import celery_app
from app.core.config import PROJECT_ROOT, setting
from app.services.reports import generate_report_html

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
    Generate PDF report from analysis data and save to disk immediately.
    Returns dict with file_path and analysis_id.
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
            raise ValueError("Invalid analysis")

        # Save to disk immediately
        reports_dir = (
            Path(setting.REPORTS_DIR)
            if hasattr(setting, "REPORTS_DIR")
            else Path(PROJECT_ROOT / "reports")
        )
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Use task_id in filename for uniqueness, but analysis_id for readability
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{analysis_id}_{timestamp}.pdf"
        file_path = reports_dir / filename

        # Synchronous write (Celery is sync)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info(
            "Report PDF generated and saved for analysis %d at %s (size: %d bytes)",
            analysis_id,
            file_path,
            len(pdf_bytes),
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
