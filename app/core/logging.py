# app/core/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from app.core.config import PROJECT_ROOT, setting

# Create logs directory
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Get settings
DEV_MODE = setting.DEV_MODE

# Create logger instance
logger = logging.getLogger("app")
if logger.hasHandlers():
    logger.handlers.clear()
logger.setLevel(logging.DEBUG)  # Base level always DEBUG (handlers filter)

# Formatters
detailed_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

simple_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
)

# ===== CONSOLE HANDLER =====
console_handler = logging.StreamHandler(sys.stdout)
if DEV_MODE:
    console_handler.setLevel(logging.DEBUG)  # Verbose in dev
else:
    console_handler.setLevel(logging.INFO)  # Clean in production
console_handler.setFormatter(simple_formatter if DEV_MODE else detailed_formatter)
logger.addHandler(console_handler)

# ===== FILE HANDLER - All logs =====
file_handler = RotatingFileHandler(
    LOG_DIR / "app.log",
    maxBytes=10_485_760,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
# In dev: capture everything for debugging
# In prod: capture INFO+ to save space
file_handler.setLevel(logging.DEBUG if DEV_MODE else logging.INFO)
file_handler.setFormatter(detailed_formatter)
logger.addHandler(file_handler)

# ===== ERROR HANDLER - Always capture errors =====
error_handler = TimedRotatingFileHandler(
    LOG_DIR / "error.log",
    when="midnight",
    backupCount=30 if not DEV_MODE else 7,  # Keep less in dev
    encoding="utf-8",
)
error_handler.setLevel(logging.ERROR)  # ERROR and CRITICAL only
error_handler.setFormatter(detailed_formatter)
logger.addHandler(error_handler)

# ===== WARNING HANDLER - Only in production =====
if not DEV_MODE:
    warning_handler = RotatingFileHandler(
        LOG_DIR / "warning.log",
        maxBytes=5_242_880,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(detailed_formatter)
    logger.addHandler(warning_handler)

# ===== ACCESS HANDLER - User actions =====
access_handler = RotatingFileHandler(
    LOG_DIR / "access.log", maxBytes=10_485_760, backupCount=5, encoding="utf-8"
)
access_handler.setLevel(logging.INFO)
access_formatter = logging.Formatter(
    "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
access_handler.setFormatter(access_formatter)
logger.addHandler(access_handler)

# ===== SUPPRESS THIRD-PARTY LOGS =====
if DEV_MODE:
    # In dev: show some SQL for debugging
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
else:
    # In prod: suppress everything
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
    logger.info(f"USER_ACTION: {action} - user={username}", extra=kwargs)


def log_security_event(event: str, username: str = "", **kwargs):
    """Log security events (logins, permission changes, etc.)"""
    if username:
        logger.warning(f"SECURITY: {event} - user={username}", extra=kwargs)
    else:
        logger.warning(f"SECURITY: {event}", extra=kwargs)


def log_db_query(query: str, duration: float):
    """Log database queries (DEBUG level, only in dev)"""
    if DEV_MODE:
        logger.debug(f"DB_QUERY: {duration:.3f}s - {query[:100]}...")
