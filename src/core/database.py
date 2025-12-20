"""
Database connection and session management.

This module provides async database session management using SQLAlchemy 2.0
with PostgreSQL and asyncpg driver. Implements connection pooling.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from core.config import settings

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Database Engine Configuration
# -----------------------------------------------------------------------------


def create_database_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create async database engine with connection pooling.

    Args:
        database_url: Database URL. If None, uses settings.database_url

    Returns:
        Configured AsyncEngine instance

    Connection Pool Configuration:
        - pool_size: Number of permanent connections (default: 5)
        - max_overflow: Additional connections under load (default: 10)
        - pool_pre_ping: Test connection before use (default: True)
        - pool_recycle: Recycle connections after N seconds (default: 3600)
    """
    url = database_url or settings.database_url_str

    logger.info("Initializing database engine...")

    engine = create_async_engine(
        url,
        echo=settings.debug,  # Log SQL queries in debug mode
        echo_pool=settings.debug,  # Log connection pool events in debug mode
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=settings.db_pool_pre_ping,
        pool_recycle=settings.db_pool_recycle,
        poolclass=AsyncAdaptedQueuePool,
        # Additional performance settings
        pool_timeout=settings.db_pool_timeout,  # Wait up for a connection
        connect_args={
            "server_settings": {
                "application_name": f"{settings.app_name} - {settings.environment}",
            },
        },
    )

    logger.info(
        f"Database engine created: pool_size={settings.db_pool_size}, "
        f"max_overflow={settings.db_max_overflow}"
    )

    return engine


# -----------------------------------------------------------------------------
# Lifecycle Management
# -----------------------------------------------------------------------------


async def close_database_connection(engine: AsyncEngine) -> None:
    """
    Close database engine and dispose of connection pool.

    Should be called on application shutdown to gracefully close
    all database connections.

    Args:
        engine: The AsyncEngine to dispose. If None, logs warning and returns.
    """
    try:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")
        # Don't raise - we're shutting down anyway
