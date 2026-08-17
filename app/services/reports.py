from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, cast
from uuid import UUID

from celery.result import AsyncResult
from celery.states import FAILURE, PENDING, STARTED, SUCCESS
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.core.celery import celery_app
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.models.models import Analysis
from app.repositories.analysis_repositories import (
    get_analysis_by_id_repo,
)
from app.services.analysis import get_analysis_detail
from app.tasks.report_tasks import create_report_pdf

logger = get_logger(__file__)


async def queue_report_generation(
    analysis_id: int, user_id: UUID, db: DBSession
) -> str:
    """Queue report generation and store task ID."""
    analysis = await get_analysis_detail(analysis_id=analysis_id, db=db)
    if not analysis:
        raise ValueError("Analysis not found")

    # Check if report already exists (redundant but safe)
    if (
        analysis.report_stored
        and analysis.report_path
        and Path(analysis.report_path).exists()
    ):
        logger.info("Report already exists for analysis %d", analysis_id)
        return "already_exists"

    # Convert to dict and queue task
    analysis_data = analysis.model_dump()
    task = create_report_pdf.delay(analysis_data=analysis_data)
    task_id = task.id

    # Store task ID for tracking
    analysis.report_task_id = task_id
    await db.commit()

    logger.info("Queued report task %s for analysis %d", task_id, analysis_id)
    return task_id


async def get_report_status_and_save_result(
    task_id: str,
    db: DBSession,
) -> dict:
    """
    Check Celery task status.
    If completed, update DB with file path (already saved by task).
    Returns dict with status, file_path, analysis_id, and error if any.
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

        # Check if task returned error
        if not isinstance(result, dict) or result.get("status") == "failed":
            error = (
                result.get("error", "Unknown error")
                if isinstance(result, dict)
                else "Invalid result"
            )
            logger.error("Report task %s returned failure: %s", task_id, error)
            return {"status": "failed", "error": error}

        # Extract data
        analysis_id = result.get("analysis_id")
        file_path = result.get("file_path")

        if not analysis_id or not file_path:
            logger.error("Task %s result missing analysis_id or file_path", task_id)
            return {"status": "failed", "error": "Incomplete result from task"}

        # Verify file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.error("Report file %s not found for task %s", file_path, task_id)
            return {"status": "failed", "error": "Report file missing"}

        # Update analysis record
        analysis = await get_analysis_by_id_repo(
            analysis_id,
            db,
            options=[selectinload(cast(InstrumentedAttribute, Analysis.clauses))],
        )
        if not analysis:
            logger.error(
                "Analysis %d not found for report task %s", analysis_id, task_id
            )
            return {"status": "failed", "error": "Analysis not found"}

        # Update DB (idempotent)
        if not analysis.report_stored:
            analysis.report_stored = True
            analysis.report_path = str(file_path)
            analysis.report_generated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(analysis)
            logger.info(
                "Updated analysis %d with report path: %s", analysis_id, file_path
            )

        return {
            "status": "completed",
            "file_path": str(file_path),
            "analysis_id": analysis_id,
        }

    # Unknown state
    logger.warning("Unknown task state for task %s: %s", task_id, state)
    return {"status": "pending"}


def generate_report_html(analysis_data: Dict[str, Any]) -> str:
    """
    Generate a styled HTML document from analysis data for PDF rendering.
    """
    # Extract data
    title = analysis_data.get("title", "Contract Analysis Report")
    document_summary = analysis_data.get("document_summary", "")
    document_type = analysis_data.get("document_type", "")
    overall_risk_score = analysis_data.get("overall_risk_score", 0)
    recommendations = analysis_data.get("recommendations", [])
    clauses = analysis_data.get("clauses", [])
    created_at = analysis_data.get("created_at")
    if created_at:
        created_at = (
            created_at.strftime("%Y-%m-%d %H:%M")
            if hasattr(created_at, "strftime")
            else str(created_at)
        )

    # Risk level mapping for colors
    risk_colors = {
        "low": "#28a745",  # green
        "average": "#ffc107",  # yellow
        "high": "#fd7e14",  # orange
        "critical": "#dc3545",  # red
    }

    # Build clauses table rows
    clauses_rows = ""
    for clause in clauses:
        risk_level = clause.get("risk_level", "average").lower()
        color = risk_colors.get(risk_level, "#6c757d")
        key_terms = ", ".join(clause.get("key_terms", []))
        suggested_actions = "<br>".join(clause.get("suggested_actions", []))
        clauses_rows += f"""
        <tr>
            <td>{clause.get("clause_type", "")}</td>
            <td>{clause.get("summary", "")}</td>
            <td style="background-color:{color}; color:white; text-align:center;">{risk_level.capitalize()}</td>
            <td>{key_terms}</td>
            <td>{suggested_actions}</td>
        </tr>
        """

    # Recommendations list
    rec_items = "".join(f"<li>{rec}</li>" for rec in recommendations)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #6c757d;
            }}
        }}
        body {{
            font-family: 'Helvetica', 'Arial', sans-serif;
            line-height: 1.6;
            color: #212529;
        }}
        h1, h2, h3 {{
            color: #1a1a2e;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #0d6efd;
            padding-bottom: 10px;
        }}
        .meta {{
            text-align: center;
            margin-bottom: 20px;
            color: #6c757d;
            font-size: 12pt;
        }}
        .score-box {{
            background: #f8f9fa;
            border-left: 5px solid #0d6efd;
            padding: 10px 15px;
            margin: 20px 0;
        }}
        .score-value {{
            font-size: 24pt;
            font-weight: bold;
            color: #0d6efd;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 10pt;
        }}
        th {{
            background: #e9ecef;
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: left;
        }}
        td {{
            border: 1px solid #dee2e6;
            padding: 8px;
            vertical-align: top;
        }}
        .recommendations {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .recommendations ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .footer {{
            text-align: center;
            font-size: 9pt;
            color: #6c757d;
            margin-top: 30px;
            border-top: 1px solid #dee2e6;
            padding-top: 10px;
        }}
        /* Page breaks */
        .page-break {{
            page-break-before: always;
        }}
        /* Avoid breaking inside table rows */
        tr {{
            page-break-inside: avoid;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="meta">
        <span>Document Type: {document_type}</span>
        {f"<span> | Generated: {created_at}</span>" if created_at else ""}
    </div>

    <div class="score-box">
        <strong>Overall Risk Score:</strong>
        <span class="score-value">{overall_risk_score}</span> / 100
    </div>

    <h2>Document Summary</h2>
    <p>{document_summary}</p>

    <h2>Clause Analysis</h2>
    <table>
        <thead>
            <tr>
                <th>Clause Type</th>
                <th>Summary</th>
                <th>Risk Level</th>
                <th>Key Terms</th>
                <th>Suggested Actions</th>
            </tr>
        </thead>
        <tbody>
            {clauses_rows}
        </tbody>
    </table>

    <div class="recommendations">
        <h3>Recommendations</h3>
        <ul>
            {rec_items}
        </ul>
    </div>

    <div class="footer">
        Generated by Contract Clause Reviewer
    </div>
</body>
</html>
    """
    return html
