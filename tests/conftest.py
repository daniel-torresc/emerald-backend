"""
Pytest configuration and fixtures for Emerald Finance Platform tests.

This module provides:
- Database setup and teardown
- Test client fixtures
- User fixtures for testing
- Authentication token fixtures
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.database import get_db
from src.main import app
from src.models.base import Base
from src.models.user import User
from src.core.security import hash_password


# ============================================================================
# Pytest Configuration
# ============================================================================
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create an event loop for the entire test session.

    This is required for async tests to work properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================
@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a test database engine.

    Uses a separate test database to avoid affecting development data.
    """
    # Create test database engine
    engine = create_async_engine(
        str(settings.database_url),
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for a test.

    Each test gets a fresh session with automatic rollback.
    """
    # Create session factory
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # Start a transaction
        await session.begin()

        yield session

        # Rollback the transaction after the test
        await session.rollback()


@pytest_asyncio.fixture
async def db_session_commit(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session that commits changes.

    Use this when you need data to persist across multiple queries in a test.
    """
    # Create session factory
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

        # Clean up: delete all data after the test
        async with session.begin():
            # Delete in reverse order of foreign key dependencies
            await session.execute(text("DELETE FROM audit_logs"))
            await session.execute(text("DELETE FROM refresh_tokens"))
            await session.execute(text("DELETE FROM user_roles"))
            await session.execute(text("DELETE FROM users"))
            await session.execute(text("DELETE FROM roles"))


# ============================================================================
# FastAPI Client Fixtures
# ============================================================================
@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """
    Create a FastAPI test client with database override.

    This is a synchronous client for simple tests.
    """
    # Override the get_db dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async FastAPI test client with database override.

    Use this for async tests.
    """
    # Override the get_db dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clear overrides
    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================
@pytest_asyncio.fixture
async def test_user(db_session_commit: AsyncSession) -> User:
    """
    Create a test user in the database.

    Returns:
        User instance with known credentials
    """
    user = User(
        email="testuser@example.com",
        username="testuser",
        password_hash=hash_password("TestPass123!"),
        is_active=True,
        is_admin=False,
    )

    db_session_commit.add(user)
    await db_session_commit.commit()
    await db_session_commit.refresh(user)

    return user


@pytest_asyncio.fixture
async def admin_user(db_session_commit: AsyncSession) -> User:
    """
    Create an admin user in the database.

    Returns:
        User instance with admin privileges
    """
    user = User(
        email="admin@example.com",
        username="adminuser",
        password_hash=hash_password("AdminPass123!"),
        is_active=True,
        is_admin=True,
    )

    db_session_commit.add(user)
    await db_session_commit.commit()
    await db_session_commit.refresh(user)

    return user


@pytest_asyncio.fixture
async def inactive_user(db_session_commit: AsyncSession) -> User:
    """
    Create an inactive user in the database.

    Returns:
        User instance that is deactivated
    """
    user = User(
        email="inactive@example.com",
        username="inactiveuser",
        password_hash=hash_password("InactivePass123!"),
        is_active=False,
        is_admin=False,
    )

    db_session_commit.add(user)
    await db_session_commit.commit()
    await db_session_commit.refresh(user)

    return user


# ============================================================================
# Authentication Fixtures
# ============================================================================
@pytest_asyncio.fixture
async def user_token(async_client: AsyncClient, test_user: User) -> dict:
    """
    Get authentication tokens for a test user.

    Returns:
        Dictionary with access_token and refresh_token
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "TestPass123!",
        },
    )

    assert response.status_code == 200
    return response.json()


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient, admin_user: User) -> dict:
    """
    Get authentication tokens for an admin user.

    Returns:
        Dictionary with access_token and refresh_token
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPass123!",
        },
    )

    assert response.status_code == 200
    return response.json()


@pytest.fixture
def auth_headers(user_token: dict) -> dict:
    """
    Get authorization headers for a test user.

    Returns:
        Dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {user_token['access_token']}"}


@pytest.fixture
def admin_headers(admin_token: dict) -> dict:
    """
    Get authorization headers for an admin user.

    Returns:
        Dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {admin_token['access_token']}"}