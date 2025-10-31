"""
Pytest configuration and fixtures for Emerald Finance Platform tests.

This module provides:
- Database setup and teardown
- Test client fixtures
- User fixtures for testing
- Authentication token fixtures
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import redis.asyncio as redis
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

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
def event_loop():
    """
    Create an event loop for the entire test session.

    This is required for async tests to work properly.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================
@pytest_asyncio.fixture(scope="session")
async def test_engine(event_loop):
    """
    Create a test database engine.

    Uses a separate test database to avoid affecting development data.
    """
    # Create test database engine with NullPool to avoid connection issues
    engine = create_async_engine(
        str(settings.database_url),
        echo=False,
        future=True,
        poolclass=NullPool,  # Disable connection pooling for tests
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for a test.

    Each test gets a fresh session with automatic cleanup.
    """
    # Create session factory
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session

        # Rollback any uncommitted changes
        await session.rollback()


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
async def async_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async FastAPI test client with database override.

    Use this for async tests.
    """
    # Create a session factory
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Override the get_db dependency
    async def override_get_db():
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Clear Redis (used for rate limiting) before test
    redis_client = redis.from_url(str(settings.redis_url))
    try:
        await redis_client.flushdb()
    except Exception:
        pass  # Redis might not be available
    finally:
        await redis_client.aclose()

    # Use AsyncClient with proper transport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clear overrides
    app.dependency_overrides.clear()

    # Clean up database after each test
    async with async_session_factory() as session:
        try:
            await session.execute(text("DELETE FROM audit_logs"))
            await session.execute(text("DELETE FROM refresh_tokens"))
            await session.execute(text("DELETE FROM users"))
            await session.commit()
        except Exception:
            await session.rollback()

    # Clear Redis after test
    redis_client = redis.from_url(str(settings.redis_url))
    try:
        await redis_client.flushdb()
    except Exception:
        pass
    finally:
        await redis_client.aclose()


# ============================================================================
# User Fixtures
# ============================================================================
@pytest_asyncio.fixture
async def test_user(test_engine) -> User:
    """
    Create a test user in the database.

    Returns:
        User instance with known credentials
    """
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        user = User(
            email="testuser@example.com",
            username="testuser",
            password_hash=hash_password("TestPass123!"),
            is_active=True,
            is_admin=False,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user


@pytest_asyncio.fixture
async def admin_user(test_engine) -> User:
    """
    Create an admin user in the database.

    Returns:
        User instance with admin privileges
    """
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        user = User(
            email="admin@example.com",
            username="adminuser",
            password_hash=hash_password("AdminPass123!"),
            is_active=True,
            is_admin=True,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user


@pytest_asyncio.fixture
async def inactive_user(test_engine) -> User:
    """
    Create an inactive user in the database.

    Returns:
        User instance that is deactivated
    """
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        user = User(
            email="inactive@example.com",
            username="inactiveuser",
            password_hash=hash_password("InactivePass123!"),
            is_active=False,
            is_admin=False,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

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
