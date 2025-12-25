import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core import settings
from core.database import close_database_connection, create_database_engine

logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Context Manager
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database engine creation and storage in app.state
    - Session factory creation
    - Resource cleanup on shutdown
    """
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Environment: {settings.environment}")

    # Create database engine
    engine = create_database_engine()

    # Create sessionmaker and store in app state
    app.state.sessionmaker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Sessionmaker created successfully")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")
    await close_database_connection(engine)
    app.state.sessionmaker = None
