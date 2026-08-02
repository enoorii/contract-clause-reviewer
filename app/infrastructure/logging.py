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

from fastapi import Request, Response

from app.core.config import PROJECT_ROOT, setting

# Create logs directory
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Get settings
DEV_MODE = setting.DEV_MODE

# Global listener reference for cleanup
_listener: Optional[QueueListener] = None
_initialized = False

# ===== CREATE HANDLERS (but DON'T add to logger yet) =====

# Formatters
detailed_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

simple_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
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
        LOG_DIR / "access.log", maxBytes=10_485_760, backupCount=5, encoding="utf-8"
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


def setup_logging():
    """Initialize logging with QueueListener - Call this in main.py lifespan"""
    global _listener, _initialized

    if _initialized:
        return _listener

    # Create all handlers
    handlers = _create_handlers()

    # Create and start listener
    _listener = QueueListener(_log_queue, *handlers, respect_handler_level=True)
    _listener.start()

    # Add ONLY the queue handler to the logger
    logger.addHandler(_queue_handler)

    # Register cleanup
    atexit.register(shutdown_logging)

    _initialized = True

    # Suppress third-party logs (do this after setup)
    _suppress_third_party_logs()

    return _listener


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


# ===== CONVENIENCE FUNCTIONS =====
def log_user_action(action: str, username: str, **kwargs):
    """Log user actions to access.log"""
    # Ensure logging is setup (lazy initialization)
    if not _initialized:
        setup_logging()
    logger.info(f"USER_ACTION: {action} - user={username}", extra=kwargs)


def log_security_event(event: str, username: str = "", **kwargs):
    """Log security events (logins, permission changes, etc.)"""
    if not _initialized:
        setup_logging()
    if username:
        logger.warning(f"SECURITY: {event} - user={username}", extra=kwargs)
    else:
        logger.warning(f"SECURITY: {event}", extra=kwargs)


def log_db_query(query: str, duration: float):
    """Log database queries (DEBUG level, only in dev)"""
    if DEV_MODE:
        if not _initialized:
            setup_logging()
        logger.debug(f"DB_QUERY: {duration:.3f}s - {query[:100]}...")


def log_request_start(request: Request):
    """Log the start of a request"""
    if not _initialized:
        setup_logging()

    logger.info(
        f"Request started | "
        f"method={request.method} | "
        f"path={request.url.path} | "
        f"client={request.client.host if request.client else 'unknown'}"
    )


def log_request_completed(request: Request, response: Response, duration: float):
    """Log request completion with timing"""
    if not _initialized:
        setup_logging()

    # Check if response has status code (handle errors)
    status_code = getattr(response, "status_code", None)

    logger.info(
        f"Request completed | "
        f"method={request.method} | "
        f"status={status_code or 'unknown'} | "
        f"duration={duration * 1000:.2f}ms | "
        f"path={request.url.path} | "
        f"client={request.client.host if request.client else 'unknown'}"
    )


def log_request_error(request: Request, error: Exception, duration: float):
    """Log request errors"""
    if not _initialized:
        setup_logging()

    logger.error(
        f"Request failed | "
        f"method={request.method} | "
        f"path={request.url.path} | "
        f"duration={duration * 1000:.2f}ms | "
        f"error={type(error).__name__}: {str(error)}"
    )


# ===== OPTIONAL: Auto-initialize on first use =====
# This ensures logging works even if main.py forgets to call setup_logging()
# But it's better to call setup_logging() explicitly
def get_logger(name: str = "app"):
    """Get a logger instance, ensuring logging is initialized"""
    if not _initialized:
        setup_logging()

    return logging.getLogger(name)
