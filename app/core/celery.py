from celery import Celery
from celery.schedules import crontab

from app.core.config import setting

celery_app = Celery(
    "app",
    broker=setting.celery_broker_url,
    backend=setting.celery_backend_url,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.cleanup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    # Retry configuration
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Periodic tasks (Beat schedule)
celery_app.conf.beat_schedule = {
    "cleanup_expired_tokens_daily": {
        "task": "cleanup_expired_refresh_tokens",  # Must match task name
        "schedule": crontab(hour=0, minute=0),  # Run at midnight every day
        "options": {
            "expires": 3600,  # Task expires after 1 hour if not run
        },
    },
}

# Optional: Route tasks to different queues
celery_app.conf.task_routes = {
    "analyze_legal_document": {"queue": "analysis"},
    "cleanup_expired_refresh_tokens": {"queue": "cleanup"},
}
