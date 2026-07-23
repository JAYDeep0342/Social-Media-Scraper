"""FastAPI startup/shutdown lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.core.logging import get_logger, setup_logging
from app.network.session_manager import SessionManager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    settings = get_settings()
    logger.info(
        "Starting %s v%s [env=%s, debug=%s, max_concurrency=%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENV,
        settings.DEBUG,
        settings.MAX_CONCURRENCY,
    )

    session_manager = SessionManager.get_instance()
    await session_manager.startup()

    yield

    await session_manager.shutdown()
    logger.info("Shutting down %s", settings.APP_NAME)
