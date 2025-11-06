"""
Database configuration and session management.

This module provides database connection setup, session factory,
and configuration for PostgreSQL using SQLAlchemy async.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.infrastructure.adapters.outbound.persistence.postgresql.models.base import Base


class DatabaseConfig:
    """
    Database configuration and session management.

    Provides:
    - Async engine creation with proper connection pooling
    - Session factory for creating database sessions
    - Database initialization (create tables)
    - Session lifecycle management

    Usage:
        # Initialize database
        db_config = DatabaseConfig(database_url)
        await db_config.create_tables()

        # Get a session
        async with db_config.get_session() as session:
            # Use session
            user = await session.get(UserModel, user_id)
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        use_null_pool: bool = False,
    ):
        """
        Initialize database configuration.

        Args:
            database_url: PostgreSQL connection URL (async format)
                         Example: "postgresql+asyncpg://user:pass@localhost/dbname"
            echo: Whether to log SQL statements (useful for debugging)
            pool_size: Number of connections to keep in the pool
            max_overflow: Max number of connections to create beyond pool_size
            pool_timeout: Seconds to wait before giving up on getting a connection
            pool_recycle: Seconds after which to recycle connections
            pool_pre_ping: Test connections before using them
            use_null_pool: Use NullPool (no connection pooling) - useful for testing
        """
        self.database_url = database_url
        self.echo = echo

        # Create async engine with connection pooling
        if use_null_pool:
            # No connection pooling (useful for testing)
            self.engine: AsyncEngine = create_async_engine(
                database_url,
                echo=echo,
                poolclass=NullPool,
            )
        else:
            # Connection pooling (production)
            self.engine: AsyncEngine = create_async_engine(
                database_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                pool_pre_ping=pool_pre_ping,
                poolclass=QueuePool,
            )

        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flush control
            autocommit=False,  # Manual commit control (required for transactions)
        )

    async def create_tables(self) -> None:
        """
        Create all database tables.

        This should be called during application startup in development.
        In production, use Alembic migrations instead.

        Example:
            await db_config.create_tables()
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """
        Drop all database tables.

        Warning: This will delete all data! Only use in development/testing.

        Example:
            await db_config.drop_tables()
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """
        Close database engine and all connections.

        This should be called during application shutdown.

        Example:
            await db_config.close()
        """
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """
        Get a new database session.

        Returns a session that should be used with async context manager.

        Returns:
            AsyncSession instance

        Example:
            async with db_config.get_session() as session:
                user = await session.get(UserModel, user_id)
                session.add(user)
                await session.commit()
        """
        return self.session_factory()

    async def get_session_generator(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Session generator for dependency injection.

        Yields a session and ensures it's closed after use.
        Useful for FastAPI dependency injection.

        Yields:
            AsyncSession instance

        Example:
            # In FastAPI
            async def get_db_session():
                async for session in db_config.get_session_generator():
                    yield session

            @app.get("/users/{user_id}")
            async def get_user(user_id: UUID, session: AsyncSession = Depends(get_db_session)):
                user = await session.get(UserModel, user_id)
                return user
        """
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if connection is healthy, False otherwise

        Example:
            is_healthy = await db_config.health_check()
            if not is_healthy:
                raise RuntimeError("Database is not healthy")
        """
        try:
            async with self.session_factory() as session:
                # Execute a simple query to test connection
                await session.execute("SELECT 1")
                return True
        except Exception:
            return False
