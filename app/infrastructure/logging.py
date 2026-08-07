# app/core/logging.py
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
from typing import Optional
from uuid import UUID

from fastapi import Request

from app.core.config import PROJECT_ROOT, setting

# Create logs directory
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Get settings
DEV_MODE = setting.DEV_MODE

# Global listener reference for cleanup
_listener: Optional[QueueListener] = None
_initialized = False
_audit_logger: Optional[logging.Logger] = None

# ===== CREATE HANDLERS (but DON'T add to logger yet) =====

# Formatters
detailed_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

simple_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
)

audit_formatter = logging.Formatter(
    "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)


def _create_handlers():
    """Create all handlers but don't attach them yet"""

    # 1. CONSOLE HANDLER
    console_handler = logging.StreamHandler(sys.stdout)
    if DEV_MODE:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter if DEV_MODE else detailed_formatter)

    # 2. FILE HANDLER - All logs
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if DEV_MODE else logging.INFO)
    file_handler.setFormatter(detailed_formatter)

    # 3. ERROR HANDLER - Always capture errors
    error_handler = TimedRotatingFileHandler(
        LOG_DIR / "error.log",
        when="midnight",
        backupCount=30 if not DEV_MODE else 7,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # 4. WARNING HANDLER - Only in production
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

    # 5. ACCESS HANDLER - User actions
    access_handler = RotatingFileHandler(
        LOG_DIR / "access.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8",
    )
    access_handler.setLevel(logging.INFO)
    access_formatter = logging.Formatter(
        "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    access_handler.setFormatter(access_formatter)

    # Collect all handlers
    handlers = [console_handler, file_handler, error_handler, access_handler]
    if warning_handler:
        handlers.append(warning_handler)

    return handlers


def _create_audit_handler():
    """Create audit handler with its own rotation"""
    audit_handler = RotatingFileHandler(
        LOG_DIR / "audit.log",
        maxBytes=10_485_760,
        backupCount=10,  # Keep more audit logs
        encoding="utf-8",
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(audit_formatter)
    return audit_handler


# ===== QUEUE SETUP =====
_log_queue = Queue(maxsize=10000)
_queue_handler = QueueHandler(_log_queue)

# ===== MAIN LOGGER =====
# Get the logger but DON'T add handlers yet
logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)  # Base level always DEBUG

# Clear any existing handlers (from other imports)
if logger.hasHandlers():
    logger.handlers.clear()


def shutdown_logging():
    """Gracefully shutdown the queue listener"""
    global _listener, _initialized
    if _listener:
        _listener.stop()
        _listener = None
        _initialized = False


def _suppress_third_party_logs():
    """Configure third-party log levels"""
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


# ===== ENHANCED LOGGER CLASS =====


class AuditLogger(logging.Logger):
    """
    Enhanced logger with audit capabilities.
    Subclasses logging.Logger for full compatibility.
    All standard logging methods work out of the box.
    """

    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)

    def _get_client_ip(self, request: Optional[Request] = None) -> Optional[str]:
        """Extract client IP from request"""
        if request and hasattr(request, "client") and request.client:
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
    ):
        """
        Log admin actions to dedicated audit log.
        Uses the same queue system for performance.

        Args:
            action: The action being performed (e.g., "USER_CREATE", "ROLE_CHANGE")
            admin_id: ID of the admin performing the action
            admin_username: Username of the admin
            target_user: Username of the target user (if applicable)
            target_user_id: ID of the target user (if applicable)
            changes: Dictionary of changes made
            status: "SUCCESS" or "FAILED"
            ip_address: Client IP address (optional, can use request instead)
            request: FastAPI Request object (optional, used to get IP)
            error: Error message if status is "FAILED"
            **kwargs: Additional key-value pairs to log
        """
        global _audit_logger

        if not _initialized:
            setup_logging()

        # Get IP from request if provided and not explicitly set
        if ip_address is None and request is not None:
            ip_address = self._get_client_ip(request)

        # Build structured message parts
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
            # Convert changes to string representation
            changes_str = ", ".join(f"{k}:{v}" for k, v in changes.items())
            parts.append(f"changes=[{changes_str}]")
        if ip_address:
            parts.append(f"ip={ip_address}")
        if error:
            parts.append(f"error={error}")

        # Add any extra kwargs
        for key, value in kwargs.items():
            parts.append(f"{key}={value}")

        # Log to audit logger
        if _audit_logger:
            _audit_logger.info(" | ".join(parts))

        # Also log to main logger in dev mode for visibility
        if DEV_MODE:
            self.debug(f"AUDIT: {' | '.join(parts)}")

    def user_action(
        self, action: str, username: str, request: Optional[Request] = None, **kwargs
    ):
        """
        Log user actions to access log.

        Args:
            action: The action being performed (e.g., "LOGIN", "LOGOUT")
            username: Username of the user
            request: FastAPI Request object (optional, used to get IP)
            **kwargs: Additional key-value pairs to log
        """
        if not _initialized:
            setup_logging()

        # Build message parts
        parts = [f"USER_ACTION={action}", f"user={username}"]

        # Add IP if request is provided
        if request:
            ip = self._get_client_ip(request)
            if ip:
                parts.append(f"ip={ip}")

        # Add any extra kwargs
        for key, value in kwargs.items():
            parts.append(f"{key}={value}")

        # Log to access logger (info level)
        self.info(" | ".join(parts))


# ===== SETUP LOGGING =====


def setup_logging():
    """Initialize logging with QueueListener - Call this in main.py lifespan"""
    global _listener, _initialized, _audit_logger

    if _initialized:
        return _listener

    # 1. Clean up root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)

    # 2. IMPORTANT: Set our custom logger class as the default
    # This is the key! All loggers created after this will be AuditLogger
    logging.setLoggerClass(AuditLogger)

    # 3. Setup APP logger (main logger with queue)
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.DEBUG)
    app_logger.handlers.clear()
    app_logger.propagate = False
    app_logger.addHandler(_queue_handler)

    # 4. Create handlers and start queue listener
    handlers = _create_handlers()
    _listener = QueueListener(_log_queue, *handlers, respect_handler_level=True)
    _listener.start()

    # 5. Setup AUDIT logger (direct writes, no queue)
    _audit_logger = logging.getLogger("audit")
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.handlers.clear()
    _audit_logger.propagate = False

    # Add handler directly (no queue - good for low volume)
    audit_handler = _create_audit_handler()
    _audit_logger.addHandler(audit_handler)

    # Add console in dev mode for visibility
    if DEV_MODE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(audit_formatter)
        _audit_logger.addHandler(console_handler)

    # 6. Suppress third-party logs
    _suppress_third_party_logs()

    # 7. Register cleanup
    atexit.register(shutdown_logging)

    _initialized = True
    return _listener


# ===== LOGGER FACTORY =====


def get_logger(name: str = "app"):
    """
    Get a logger instance with enhanced audit capabilities.

    Args:
        name: Logger name - typically use __file__ or module name

    Returns:
        AuditLogger: Enhanced logger with audit methods

    Example:
        logger = get_logger(__file__)
        logger.info("Application started")
        logger.admin_action("USER_CREATE", admin_id=1, admin_username="admin", ...)
        logger.user_action("LOGIN", username="john", request=request)
    """
    if not _initialized:
        setup_logging()

    # Wrap it with audit capabilities
    return AuditLogger(name)


# ===== CONVENIENCE FUNCTIONS (Backward Compatibility) =====


def log_user_action(action: str, username: str, **kwargs):
    """Legacy function - use logger.user_action() instead"""
    logger_obj = get_logger("app")
    logger_obj.user_action(action, username, **kwargs)


def log_security_event(event: str, username: str = "", **kwargs):
    """Log security events (logins, permission changes, etc.)"""
    logger_obj = get_logger("app")
    if username:
        logger_obj.warning(f"SECURITY: {event} - user={username}", extra=kwargs)
    else:
        logger_obj.warning(f"SECURITY: {event}", extra=kwargs)


def log_db_query(query: str, duration: float):
    """Log database queries (DEBUG level, only in dev)"""
    if DEV_MODE:
        logger_obj = get_logger("app")
        logger_obj.debug(f"DB_QUERY: {duration:.3f}s - {query[:100]}...")


def log_request_start(request: Request):
    """Log the start of a request"""
    logger_obj = get_logger("app")
    logger_obj.info(
        f"Request started | "
        f"method={request.method} | "
        f"path={request.url.path} | "
        f"client={request.client.host if request.client else 'unknown'}"
    )


def log_request_completed(request: Request, response, duration: float):
    """Log request completion with timing"""
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


def log_request_error(request: Request, error: Exception, duration: float):
    """Log request errors"""
    logger_obj = get_logger("app")
    logger_obj.error(
        f"Request failed | "
        f"method={request.method} | "
        f"path={request.url.path} | "
        f"duration={duration * 1000:.2f}ms | "
        f"error={type(error).__name__}: {str(error)}"
    )


# Create default logger instance
logger = get_logger("app")
