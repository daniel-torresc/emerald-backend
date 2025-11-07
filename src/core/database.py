"""
Database connection and session management.

This module provides async database session management using SQLAlchemy 2.0
with PostgreSQL and asyncpg driver. Implements connection pooling and
dependency injection for FastAPI routes.
"""

import logging
from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.core.config import settings

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
    url = database_url or str(settings.database_url)

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


# Engine and sessionmaker are now managed via FastAPI app.state
# No global instances - use get_db() dependency for sessions


# -----------------------------------------------------------------------------
# Dependency Injection for FastAPI
# -----------------------------------------------------------------------------

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to provide database session to FastAPI routes.

    Gets the sessionmaker from app state and yields a session.
    Ensures proper session cleanup with commit/rollback handling.

    Args:
        request: FastAPI request object (provides access to app.state)

    Usage in FastAPI routes:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Use db session here
            ...

    Yields:
        AsyncSession: Database session for the request

    Raises:
        Exception: Re-raises any exception after rolling back transaction
    """
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# -----------------------------------------------------------------------------
# Database Health Check
# -----------------------------------------------------------------------------

async def check_database_connection(sessionmaker: async_sessionmaker) -> bool:
    """
    Check if database connection is healthy.

    Used for health check endpoints to verify database connectivity.

    Args:
        sessionmaker: AsyncSessionMaker from app.state

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        async with sessionmaker() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# -----------------------------------------------------------------------------
# Lifecycle Management
# -----------------------------------------------------------------------------

async def close_database_connection(engine: AsyncEngine | None) -> None:
    """
    Close database engine and dispose of connection pool.

    Should be called on application shutdown to gracefully close
    all database connections.

    Args:
        engine: The AsyncEngine to dispose. If None, logs warning and returns.
    """
    if engine is None:
        logger.warning("close_database_connection called with None engine")
        return

    try:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")
        # Don't raise - we're shutting down anyway
