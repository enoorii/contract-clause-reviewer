import logging
from datetime import UTC, datetime

from sqlmodel import col, delete, func, select

from app.core.celery import celery_app
from app.db.database import get_sync_db  # Add this sync session
from app.models.models import RefreshToken

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
