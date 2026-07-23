"""Production logging setup: console handler + rotating file handler.

Call `setup_logging()` once at startup (done via the FastAPI lifespan).
`get_logger(name)` is the standard way for any module to obtain a logger.
"""

import logging
import logging.handlers
import os
import sys

from app.config.constants import LOG_DATE_FORMAT, LOG_FORMAT_CONSOLE, LOG_FORMAT_FILE
from app.config.settings import get_settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    level = logging.DEBUG if settings.DEBUG else getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT_CONSOLE, datefmt=LOG_DATE_FORMAT))
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    file_path = os.path.join(settings.LOG_DIR, settings.LOG_FILE_NAME)
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT_FILE, datefmt=LOG_DATE_FORMAT))
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    # Uvicorn's access logger is noisy at INFO in production; keep app logs readable.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if settings.DEBUG else logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        setup_logging()
    return logging.getLogger(name)
