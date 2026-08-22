import atexit
import logging
import sys
from logging.handlers import (
    QueueHandler,
    QueueListener,
    RotatingFileHandler,
    TimedRotatingFileHandler,
)
from queue import Queue
from typing import Optional, cast
from uuid import UUID

from fastapi import Request

from app.core.config import PROJECT_ROOT, setting

# =============================================================================
# CONFIGURATION
# =============================================================================

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

DEV_MODE = setting.DEV_MODE


# =============================================================================
# GLOBAL STATE
# =============================================================================

_listener: Optional[QueueListener] = None
_initialized = False
_audit_logger: Optional[logging.Logger] = None


# =============================================================================
# FORMATTERS
# =============================================================================

detailed_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

simple_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

audit_formatter = logging.Formatter(
    "%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# =============================================================================
# ENHANCED LOGGER CLASS
# =============================================================================


class AuditLogger(logging.Logger):
    """
    Application logger with additional user/admin audit helpers.

    Normal logging methods such as debug(), info(), warning(), and error()
    behave exactly like standard logging.Logger methods.

    user_action() writes through the normal application logging pipeline
    and therefore goes through the QueueHandler.

    admin_action() writes to the dedicated audit logger.
    """

    def _get_client_ip(
        self,
        request: Optional[Request] = None,
    ) -> Optional[str]:
        """Extract client IP address from a FastAPI request."""
        if request and request.client:
            return request.client.host

        return None

    def admin_action(
        self,
        action: str,
        admin_id: UUID,
        admin_username: str,
        target_user: Optional[str] = None,
        target_user_id: Optional[UUID] = None,
        changes: Optional[dict] = None,
        status: str = "SUCCESS",
        ip_address: Optional[str] = None,
        request: Optional[Request] = None,
        error: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log an admin action to the dedicated audit log.

        Example:
            logger.admin_action(
                action="USER_CREATE",
                admin_id=admin.id,
                admin_username=admin.username,
                target_user=user.username,
                request=request,
            )
        """

        global _audit_logger

        if not _initialized:
            setup_logging()

        # Get IP from request when one wasn't explicitly supplied.
        if ip_address is None and request is not None:
            ip_address = self._get_client_ip(request)

        # Build structured audit message.
        parts = [
            f"ADMIN_ACTION={action}",
            f"admin_id={admin_id}",
            f"admin={admin_username}",
            f"status={status}",
        ]

        if target_user:
            parts.append(f"target={target_user}")

        if target_user_id:
            parts.append(f"target_id={target_user_id}")

        if changes:
            changes_str = ", ".join(f"{key}:{value}" for key, value in changes.items())
            parts.append(f"changes=[{changes_str}]")

        if ip_address:
            parts.append(f"ip={ip_address}")

        if error:
            parts.append(f"error={error}")

        for key, value in kwargs.items():
            parts.append(f"{key}={value}")

        message = " | ".join(parts)

        # Dedicated audit logger.
        if _audit_logger:
            _audit_logger.info(message)

        # Also make audit events visible in the normal application console
        # during development.
        if DEV_MODE:
            self.debug(f"AUDIT: {message}")

    def user_action(
        self,
        action: str,
        username: str,
        request: Optional[Request] = None,
        **kwargs,
    ) -> None:
        """
        Log a user action through the normal application logging pipeline.

        Because this uses self.info(), the message goes through the
        QueueHandler and is eventually written to access.log.
        """

        if not _initialized:
            setup_logging()

        parts = [
            f"USER_ACTION={action}",
            f"user={username}",
        ]

        if request:
            ip = self._get_client_ip(request)

            if ip:
                parts.append(f"ip={ip}")

        for key, value in kwargs.items():
            parts.append(f"{key}={value}")

        self.info(" | ".join(parts))


# =============================================================================
# REGISTER CUSTOM LOGGER CLASS
# =============================================================================
#
# IMPORTANT:
# This MUST happen before any application logger is created.
#
# Previously this was inside setup_logging(), but the module had already
# created the "app" logger before setup_logging() ran. That meant the "app"
# logger was a normal logging.Logger rather than an AuditLogger.
#

logging.setLoggerClass(AuditLogger)


# =============================================================================
# QUEUE SETUP
# =============================================================================

_log_queue = Queue(maxsize=10_000)
_queue_handler = QueueHandler(_log_queue)


# =============================================================================
# HANDLER CREATION
# =============================================================================


def _create_handlers() -> list[logging.Handler]:
    """
    Create handlers for the normal application logging pipeline.

    These handlers are consumed by QueueListener.
    """

    # -------------------------------------------------------------------------
    # 1. CONSOLE
    # -------------------------------------------------------------------------

    console_handler = logging.StreamHandler(sys.stdout)

    if DEV_MODE:
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(simple_formatter)
    else:
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)

    # -------------------------------------------------------------------------
    # 2. APP LOG
    # -------------------------------------------------------------------------

    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8",
    )

    file_handler.setLevel(logging.DEBUG if DEV_MODE else logging.INFO)
    file_handler.setFormatter(detailed_formatter)

    # -------------------------------------------------------------------------
    # 3. ERROR LOG
    # -------------------------------------------------------------------------

    error_handler = TimedRotatingFileHandler(
        LOG_DIR / "error.log",
        when="midnight",
        backupCount=30 if not DEV_MODE else 7,
        encoding="utf-8",
    )

    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # -------------------------------------------------------------------------
    # 4. WARNING LOG
    # -------------------------------------------------------------------------

    warning_handler = None

    if not DEV_MODE:
        warning_handler = RotatingFileHandler(
            LOG_DIR / "warning.log",
            maxBytes=5_242_880,
            backupCount=3,
            encoding="utf-8",
        )

        warning_handler.setLevel(logging.WARNING)
        warning_handler.setFormatter(detailed_formatter)

    # -------------------------------------------------------------------------
    # 5. ACCESS LOG
    # -------------------------------------------------------------------------

    access_handler = RotatingFileHandler(
        LOG_DIR / "access.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8",
    )

    access_handler.setLevel(logging.INFO)

    access_formatter = logging.Formatter(
        "%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    access_handler.setFormatter(access_formatter)

    # -------------------------------------------------------------------------
    # COLLECT HANDLERS
    # -------------------------------------------------------------------------

    handlers = [
        console_handler,
        file_handler,
        error_handler,
        access_handler,
    ]

    if warning_handler:
        handlers.append(warning_handler)

    return handlers


def _create_audit_handler() -> RotatingFileHandler:
    """Create the dedicated audit log handler."""

    audit_handler = RotatingFileHandler(
        LOG_DIR / "audit.log",
        maxBytes=10_485_760,
        backupCount=10,
        encoding="utf-8",
    )

    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(audit_formatter)

    return audit_handler


# =============================================================================
# FLUSH / SHUTDOWN
# =============================================================================


def flush_logs() -> None:
    """Wait for queued log messages to be processed and flush handlers."""

    global _listener

    if not _listener:
        return

    # QueueListener calls task_done() after processing each record.
    _log_queue.join()

    for handler in _listener.handlers:
        if hasattr(handler, "flush"):
            handler.flush()


def shutdown_logging() -> None:
    """Gracefully stop the logging system."""

    global _listener, _initialized, _audit_logger

    if not _listener:
        return

    flush_logs()

    _listener.stop()
    _listener = None

    # Close audit handlers as well.
    if _audit_logger:
        for handler in _audit_logger.handlers:
            handler.flush()
            handler.close()

        _audit_logger.handlers.clear()

    _audit_logger = None
    _initialized = False


# =============================================================================
# THIRD-PARTY LOGGING
# =============================================================================


def _suppress_third_party_logs() -> None:
    """Configure logging levels for third-party libraries."""

    if DEV_MODE:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(
        logging.INFO if DEV_MODE else logging.WARNING
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)


# =============================================================================
# SETUP
# =============================================================================


def setup_logging():
    """
    Initialize the application logging system.

    This function is safe to call multiple times.
    """

    global _listener, _initialized, _audit_logger

    if _initialized:
        return _listener

    # -------------------------------------------------------------------------
    # 1. Configure root logger
    # -------------------------------------------------------------------------

    root_logger = logging.getLogger()

    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)

    # -------------------------------------------------------------------------
    # 2. Configure APP logger
    # -------------------------------------------------------------------------
    #
    # Because logging.setLoggerClass(AuditLogger) was executed at module
    # import time, this logger is an AuditLogger.
    #

    app_logger = logging.getLogger("app")

    app_logger.setLevel(logging.DEBUG)
    app_logger.handlers.clear()
    app_logger.propagate = False

    app_logger.addHandler(_queue_handler)

    # -------------------------------------------------------------------------
    # 3. Create and start QueueListener
    # -------------------------------------------------------------------------

    handlers = _create_handlers()

    _listener = QueueListener(
        _log_queue,
        *handlers,
        respect_handler_level=True,
    )

    _listener.start()

    # -------------------------------------------------------------------------
    # 4. Configure dedicated AUDIT logger
    # -------------------------------------------------------------------------

    _audit_logger = logging.getLogger("audit")

    _audit_logger.setLevel(logging.INFO)
    _audit_logger.handlers.clear()
    _audit_logger.propagate = False

    audit_handler = _create_audit_handler()

    _audit_logger.addHandler(audit_handler)

    # Console visibility for audit events in development.
    if DEV_MODE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(audit_formatter)
        console_handler.setLevel(logging.INFO)

        _audit_logger.addHandler(console_handler)

    # -------------------------------------------------------------------------
    # 5. Configure third-party loggers
    # -------------------------------------------------------------------------

    _suppress_third_party_logs()

    # -------------------------------------------------------------------------
    # 6. Register shutdown
    # -------------------------------------------------------------------------

    atexit.register(shutdown_logging)

    _initialized = True

    return _listener


# =============================================================================
# LOGGER FACTORY
# =============================================================================


def get_logger(name: str = "app") -> AuditLogger:
    """
    Return a registered application logger.

    Use __name__ when creating a module logger:

        logger = get_logger(__name__)

    For example:

        app.api.users

    becomes:

        app.api.users

    while:

        get_logger("app")

    returns:

        app

    All application loggers inherit from the "app" logger and therefore
    use the QueueHandler / QueueListener pipeline.

    Because AuditLogger is registered as the logger class, the returned
    logger also provides:

        logger.user_action(...)
        logger.admin_action(...)
    """

    if not _initialized:
        setup_logging()

    # Avoid creating "app.app".
    if name == "app" or name.startswith("app."):
        logger_name = name
    else:
        logger_name = f"app.{name}"

    return cast(AuditLogger, logging.getLogger(logger_name))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def log_user_action(
    action: str,
    username: str,
    **kwargs,
) -> None:
    """Backward-compatible user action logger."""

    logger_obj = get_logger("app")

    logger_obj.user_action(
        action,
        username,
        **kwargs,
    )


def log_security_event(
    event: str,
    username: str = "",
    **kwargs,
) -> None:
    """Log a security event."""

    logger_obj = get_logger("app")

    if username:
        logger_obj.warning(
            f"SECURITY: {event} - user={username}",
            extra=kwargs,
        )
    else:
        logger_obj.warning(
            f"SECURITY: {event}",
            extra=kwargs,
        )


def log_db_query(
    query: str,
    duration: float,
) -> None:
    """Log database queries in development mode."""

    if DEV_MODE:
        logger_obj = get_logger("app")

        logger_obj.debug(f"DB_QUERY: {duration:.3f}s - {query[:100]}...")


def log_request_start(request: Request) -> None:
    """Log the start of an HTTP request."""

    logger_obj = get_logger("app")

    logger_obj.info(
        f"Request started | "
        f"method={request.method} | "
        f"path={request.url.path} | "
        f"client={request.client.host if request.client else 'unknown'}"
    )


def log_request_completed(
    request: Request,
    response,
    duration: float,
) -> None:
    """Log successful HTTP request completion."""

    logger_obj = get_logger("app")

    status_code = getattr(response, "status_code", None)

    logger_obj.info(
        f"Request completed | "
        f"method={request.method} | "
        f"status={status_code or 'unknown'} | "
        f"duration={duration * 1000:.2f}ms | "
        f"path={request.url.path} | "
        f"client={request.client.host if request.client else 'unknown'}"
    )


def log_request_error(
    request: Request,
    error: Exception,
    duration: float,
) -> None:
    """Log an HTTP request error."""

    logger_obj = get_logger("app")

    logger_obj.error(
        f"Request failed | "
        f"method={request.method} | "
        f"path={request.url.path} | "
        f"duration={duration * 1000:.2f}ms | "
        f"error={type(error).__name__}: {str(error)}"
    )
