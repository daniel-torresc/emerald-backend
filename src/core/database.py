"""
Database connection and session management.

This module provides async database session management using SQLAlchemy 2.0
with PostgreSQL and asyncpg driver. Implements connection pooling and
dependency injection for FastAPI routes.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

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
    url = database_url or settings.database_url_str

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
        pool_timeout=30,  # Wait up to 30 seconds for a connection
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


# Global engine instance
engine: AsyncEngine = create_database_engine()


# -----------------------------------------------------------------------------
# Session Factory
# -----------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


# -----------------------------------------------------------------------------
# Dependency Injection for FastAPI
# -----------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to provide database session to FastAPI routes.

    Yields an async database session and ensures it's properly closed
    after the request completes. Handles rollback on exceptions.

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
    async with AsyncSessionLocal() as session:
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

async def check_database_connection() -> bool:
    """
    Check if database connection is healthy.

    Used for health check endpoints to verify database connectivity.

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# -----------------------------------------------------------------------------
# Lifecycle Management
# -----------------------------------------------------------------------------

async def close_database_connection() -> None:
    """
    Close database engine and dispose of connection pool.

    Should be called on application shutdown to gracefully close
    all database connections.
    """
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
