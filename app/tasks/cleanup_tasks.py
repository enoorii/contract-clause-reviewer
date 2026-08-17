import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import col, delete, func, select

from app.core.celery import celery_app
from app.core.config import setting
from app.db.database import get_sync_db
from app.models.models import Analysis, RefreshToken

logger = logging.getLogger(__name__)


@celery_app.task(
    name="cleanup_expired_refresh_tokens",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def cleanup_expired_refresh_tokens(self):
    """Delete expired refresh tokens from database."""
    try:
        with get_sync_db() as db:
            now = datetime.now(UTC)

            # Count expired tokens
            count_stmt = (
                select(func.count())
                .select_from(RefreshToken)
                .where(RefreshToken.expires_at < now)
            )
            total_expired = db.exec(count_stmt).first() or 0

            if total_expired == 0:
                return {"deleted_count": 0, "status": "no_expired_tokens"}

            # Delete expired tokens
            del_stmt = delete(RefreshToken).where(col(RefreshToken.expires_at) < now)
            result = db.exec(del_stmt)

            deleted_count = result.rowcount

            logger.info(f"Deleted {deleted_count} expired refresh tokens")

            return {
                "deleted_count": deleted_count,
                "total_expired": total_expired,
                "status": "success",
            }

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        self.retry(exc=e)


@celery_app.task(
    name="cleanup_old_report_files",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def cleanup_old_report_files(self, days_to_keep: int = 30):
    """
    Delete report PDF files older than specified days.

    Args:
        days_to_keep: Number of days to keep reports (default: 30)

    Returns:
        dict: Summary of cleanup operation
    """
    try:
        # Determine reports directory
        reports_dir = (
            Path(setting.REPORTS_DIR)
            if hasattr(setting, "REPORTS_DIR")
            else Path("reports")
        )

        if not reports_dir.exists():
            logger.warning(f"Reports directory {reports_dir} does not exist")
            return {"deleted_count": 0, "status": "directory_not_found"}

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Find all report files
        report_files = list(reports_dir.glob("report_*.pdf"))

        if not report_files:
            logger.info("No report files found")
            return {"deleted_count": 0, "status": "no_files_found"}

        # Separate old and new files
        old_files = []
        for file_path in report_files:
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_date:
                    old_files.append(file_path)
            except (OSError, ValueError) as e:
                logger.warning(f"Could not read file stats for {file_path}: {e}")
                continue

        if not old_files:
            logger.info(f"No report files older than {days_to_keep} days found")
            return {"deleted_count": 0, "status": "no_old_files"}

        # Delete old files
        deleted_count = 0
        deleted_files = []
        failed_files = []

        for file_path in old_files:
            try:
                file_path.unlink()
                deleted_count += 1
                deleted_files.append(str(file_path))
                logger.debug(f"Deleted old report: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")
                failed_files.append(str(file_path))

        # Also clean up database references to deleted files
        with get_sync_db() as db:
            # Find analyses that reference deleted files
            stmt = select(Analysis).where(
                col(Analysis.report_stored).is_(True),
                col(Analysis.report_path).isnot(None),
            )
            analyses = db.exec(stmt).all()

            db_updated = 0
            for analysis in analyses:
                if analysis.report_path and not Path(analysis.report_path).exists():
                    # File doesn't exist, update DB
                    analysis.report_stored = False
                    analysis.report_path = None
                    db_updated += 1

            if db_updated > 0:
                db.commit()
                logger.info(
                    f"Updated {db_updated} database records to remove missing file references"
                )

        result = {
            "deleted_count": deleted_count,
            "failed_count": len(failed_files),
            "total_files_found": len(report_files),
            "old_files_count": len(old_files),
            "db_updated_count": db_updated,
            "days_to_keep": days_to_keep,
            "deleted_files": deleted_files[:10],  # First 10 for summary
            "failed_files": failed_files[:10],
            "status": "success" if deleted_count > 0 else "no_files_deleted",
        }

        logger.info(
            f"Cleanup completed: deleted {deleted_count} report files, "
            f"failed {len(failed_files)}, DB updates {db_updated}"
        )

        return result

    except Exception as e:
        logger.error(f"Report cleanup task failed: {e}", exc_info=True)
        self.retry(exc=e)


@celery_app.task(
    name="cleanup_orphaned_report_references",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def cleanup_orphaned_report_references(self):
    """
    Clean up database records that reference non-existent report files.
    This handles cases where files were manually deleted or lost.
    """
    try:
        with get_sync_db() as db:
            # Find analyses with stored reports
            stmt = select(Analysis).where(
                col(Analysis.report_stored).is_(True),
                col(Analysis.report_path).isnot(None),
            )
            analyses = db.exec(stmt).all()

            if not analyses:
                return {"updated_count": 0, "status": "no_references_found"}

            updated_count = 0
            missing_files = []

            for analysis in analyses:
                if analysis.report_path and not Path(analysis.report_path).exists():
                    analysis.report_stored = False
                    analysis.report_path = None
                    updated_count += 1
                    missing_files.append(
                        {
                            "analysis_id": analysis.id,
                            "missing_path": analysis.report_path,
                        }
                    )

            if updated_count > 0:
                db.commit()
                logger.info(f"Cleaned up {updated_count} orphaned report references")

            return {
                "updated_count": updated_count,
                "missing_files_count": len(missing_files),
                "missing_files": missing_files[:20],  # First 20
                "status": "success",
            }

    except Exception as e:
        logger.error(f"Orphaned references cleanup failed: {e}", exc_info=True)
        self.retry(exc=e)
