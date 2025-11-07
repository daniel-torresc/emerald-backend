"""
Dependency injection helpers for infrastructure components.

This module provides dependency injection factories that can be used
throughout the application without relying on global state.

Usage in FastAPI:
    # In main.py, create DatabaseConfig instance
    db_config = DatabaseConfig(settings.DATABASE_URL)

    # Create dependency factory
    get_db_session = create_session_dependency(db_config)
    get_uow = create_uow_dependency(db_config)

    # Use in routes
    @app.get("/users/{user_id}")
    async def get_user(
        user_id: UUID,
        session: AsyncSession = Depends(get_db_session)
    ):
        ...
"""

from collections.abc import AsyncGenerator
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.adapters.outbound.persistence.postgresql.unit_of_work import (
    PostgresUnitOfWork,
)
from app.infrastructure.config.database import DatabaseConfig


def create_session_dependency(
    db_config: DatabaseConfig,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """
    Create a session dependency factory for FastAPI.

    This returns a callable that can be used as a FastAPI dependency
    to inject database sessions into route handlers.

    Args:
        db_config: DatabaseConfig instance

    Returns:
        Async generator function for dependency injection

    Example:
        # In main.py
        db_config = DatabaseConfig(settings.DATABASE_URL)
        get_db_session = create_session_dependency(db_config)

        # In routes
        @app.get("/users")
        async def list_users(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(UserModel))
            return result.scalars().all()
    """

    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        async for session in db_config.get_session_generator():
            yield session

    return get_session


def create_uow_dependency(
    db_config: DatabaseConfig,
) -> Callable[[], AsyncGenerator[PostgresUnitOfWork, None]]:
    """
    Create a Unit of Work dependency factory for FastAPI.

    This returns a callable that can be used as a FastAPI dependency
    to inject Unit of Work instances into route handlers.

    Args:
        db_config: DatabaseConfig instance

    Returns:
        Async generator function for dependency injection

    Example:
        # In main.py
        db_config = DatabaseConfig(settings.DATABASE_URL)
        get_uow = create_uow_dependency(db_config)

        # In routes or use cases
        @app.post("/users")
        async def create_user(
            user_data: UserCreate,
            uow: PostgresUnitOfWork = Depends(get_uow)
        ):
            async with uow:
                user = User(...)
                await uow.users.add(user)
                await uow.commit()
            return user
    """

    async def get_uow() -> AsyncGenerator[PostgresUnitOfWork, None]:
        async with db_config.get_session() as session:
            uow = PostgresUnitOfWork(session)
            try:
                yield uow
            finally:
                await session.close()

    return get_uow
