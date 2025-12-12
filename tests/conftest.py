"""
Pytest configuration and fixtures for Emerald Finance Platform tests.

This module provides:
- Database setup and teardown
- Test client fixtures
- User fixtures for testing
- Authentication token fixtures
"""

# Set environment variables BEFORE importing anything from src
import os

os.environ["RATE_LIMIT_DEFAULT"] = "10000 per hour"
os.environ["RATE_LIMIT_LOGIN"] = "10000 per hour"
os.environ["RATE_LIMIT_REGISTER"] = "10000 per hour"
os.environ["RATE_LIMIT_PASSWORD_CHANGE"] = "10000 per hour"
os.environ["RATE_LIMIT_TOKEN_REFRESH"] = "10000 per hour"
os.environ["RATE_LIMIT_API"] = "10000 per hour"

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
from src.models.card import Card
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
        str(settings.test_database_url),
        echo=False,
        future=True,
        poolclass=NullPool,  # Disable connection pooling for tests
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed account_types table with system types (from migration ec9ccafe4320)
    from src.models.account_type import AccountType

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_factory() as session:
        # Check if seed data already exists
        result = await session.execute(text("SELECT COUNT(*) FROM account_types"))
        count = result.scalar()

        if count == 0:
            # Seed 4 default system account types
            system_types = [
                AccountType(
                    key="checking",
                    name="Checking",
                    description="Standard checking account for daily transactions and bill payments",
                    sort_order=1,
                ),
                AccountType(
                    key="savings",
                    name="Savings",
                    description="Savings account for storing money and earning interest",
                    sort_order=2,
                ),
                AccountType(
                    key="investment",
                    name="Investment",
                    description="Investment account for stocks, bonds, mutual funds, and other securities",
                    sort_order=3,
                ),
                AccountType(
                    key="other",
                    name="Other",
                    description="Other account types (credit cards, loans, etc.)",
                    sort_order=4,
                ),
            ]
            session.add_all(system_types)
            await session.commit()

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for a test.

    Each test gets a fresh session with automatic rollback for isolation.
    """
    # Start a transaction that will be rolled back after the test
    connection = await test_engine.connect()
    transaction = await connection.begin()

    # Create session bound to the connection
    async_session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",  # Use savepoints for nested transactions
    )

    async with async_session_factory() as session:
        yield session

    # Rollback the transaction to clean up all changes
    await transaction.rollback()
    await connection.close()


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

    Use this for async tests. Uses TRUNCATE for fast test isolation.
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

    # Clear Redis (used for caching and other purposes) before test
    redis_client = redis.from_url(str(settings.redis_url))
    try:
        await redis_client.flushall()  # Clear ALL Redis databases
        await asyncio.sleep(0.01)  # Give Redis a moment to process
    except Exception as e:
        print(f"Warning: Redis flush failed: {e}")
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

    # Clean up database after each test using TRUNCATE (faster than DELETE)
    # TRUNCATE also resets sequences and is much faster than DELETE
    async with async_session_factory() as session:
        try:
            # Disable foreign key checks temporarily
            await session.execute(text("SET session_replication_role = 'replica'"))

            # Truncate all tables (order doesn't matter with FK checks disabled)
            # Note: account_types and financial_institutions are NOT truncated (master data tables)
            await session.execute(
                text(
                    "TRUNCATE TABLE account_shares, accounts, audit_logs, refresh_tokens, users RESTART IDENTITY CASCADE"
                )
            )

            # Re-enable foreign key checks
            await session.execute(text("SET session_replication_role = 'origin'"))

            await session.commit()
        except Exception as e:
            await session.rollback()
            # Log error but don't fail the test
            print(f"Warning: Database cleanup failed: {e}")

    # Clear Redis after test
    redis_client = redis.from_url(str(settings.redis_url))
    try:
        await redis_client.flushall()  # Clear ALL Redis databases
        await asyncio.sleep(0.01)  # Give Redis a moment to process
    except Exception as e:
        print(f"Warning: Redis cleanup flush failed: {e}")
    finally:
        await redis_client.aclose()


# ============================================================================
# User Fixtures
# ============================================================================
@pytest_asyncio.fixture
async def test_user(test_engine) -> User:
    """
    Create a test user in the database.

    For unit tests using db_session: user is within the transaction and rolled back.
    For integration tests: user is cleaned up via TRUNCATE.

    Returns:
        User instance with known credentials
    """
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Check if user already exists (for test isolation issues)
        result = await session.execute(
            select(User).where(User.username == "testuser", User.deleted_at.is_(None))
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return existing_user

        # Create new user if doesn't exist
        user = User(
            email="testuser@example.com",
            username="testuser",
            password_hash=hash_password("TestPass123!"),
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

    For unit tests using db_session: user is within the transaction and rolled back.
    For integration tests: user is cleaned up via TRUNCATE.

    Returns:
        User instance with admin privileges
    """
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Check if user already exists (for test isolation issues)
        result = await session.execute(
            select(User).where(User.username == "adminuser", User.deleted_at.is_(None))
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return existing_user

        # Create new user if doesn't exist
        user = User(
            email="admin@example.com",
            username="adminuser",
            password_hash=hash_password("AdminPass123!"),
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

    For unit tests using db_session: user is within the transaction and rolled back.
    For integration tests: user is cleaned up via TRUNCATE.

    Returns:
        User instance that is deactivated
    """
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Check if user already exists (for test isolation issues)
        result = await session.execute(
            select(User).where(
                User.username == "inactiveuser", User.deleted_at.is_(None)
            )
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return existing_user

        # Create new user if doesn't exist (soft deleted to make it "inactive")
        from datetime import datetime, timezone

        user = User(
            email="inactive@example.com",
            username="inactiveuser",
            password_hash=hash_password("InactivePass123!"),
            is_admin=False,
            deleted_at=datetime.now(timezone.utc),  # Soft delete to make inactive
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
        "/api/auth/login",
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
        "/api/auth/login",
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


# ============================================================================
# Account & Transaction Fixtures
# ============================================================================
@pytest_asyncio.fixture
async def test_financial_institution(test_engine):
    """
    Create a test financial institution in the database.

    Returns:
        FinancialInstitution instance for testing
    """
    from src.models.financial_institution import FinancialInstitution
    from src.models.enums import InstitutionType

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        institution = FinancialInstitution(
            name="Chase Bank N.A.",
            short_name="Chase",
            swift_code="CHASUS33",
            routing_number="021000021",
            country_code="US",
            institution_type=InstitutionType.bank,
            logo_url="https://example.com/chase-logo.png",
            website_url="https://www.chase.com",
        )

        session.add(institution)
        await session.commit()
        await session.refresh(institution)

        return institution


@pytest_asyncio.fixture
async def savings_account_type(test_engine):
    """
    Get the 'savings' account type from the database.

    Returns:
        AccountType instance for the 'savings' system type
    """
    from src.models.account_type import AccountType
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        result = await session.execute(
            select(AccountType).where(AccountType.key == "savings")
        )
        account_type = result.scalar_one()
        return account_type


@pytest_asyncio.fixture
async def checking_account_type(test_engine):
    """
    Get the 'checking' account type from the database.

    Returns:
        AccountType instance for the 'checking' system type
    """
    from src.models.account_type import AccountType
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        result = await session.execute(
            select(AccountType).where(AccountType.key == "checking")
        )
        account_type = result.scalar_one()
        return account_type


@pytest_asyncio.fixture
async def investment_account_type(test_engine):
    """
    Get the 'investment' account type from the database.

    Returns:
        AccountType instance for the 'investment' system type
    """
    from src.models.account_type import AccountType
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        result = await session.execute(
            select(AccountType).where(AccountType.key == "investment")
        )
        account_type = result.scalar_one()
        return account_type


@pytest_asyncio.fixture
async def other_account_type(test_engine):
    """
    Get the 'other' account type from the database.

    Returns:
        AccountType instance for the 'other' system type
    """
    from src.models.account_type import AccountType
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        result = await session.execute(
            select(AccountType).where(AccountType.key == "other")
        )
        account_type = result.scalar_one()
        return account_type


@pytest_asyncio.fixture
async def inactive_account_type(test_engine):
    """
    Get or create an inactive account type for testing validation.

    Returns:
        AccountType instance that is inactive
    """
    from src.models.account_type import AccountType
    from sqlalchemy import select

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Check if inactive test type already exists
        result = await session.execute(
            select(AccountType).where(AccountType.key == "inactive_test_type")
        )
        account_type = result.scalar_one_or_none()

        if account_type is None:
            # Create if doesn't exist
            # Note: AccountType no longer has is_active field - uses hard delete only
            account_type = AccountType(
                key="inactive_test_type",
                name="Inactive Test Type",
                description="Inactive account type for testing validation",
                sort_order=999,
            )

            session.add(account_type)
            await session.commit()
            await session.refresh(account_type)

        return account_type


@pytest_asyncio.fixture
async def test_account(
    test_engine, test_user, test_financial_institution, savings_account_type
):
    """
    Create a test account in the database.

    Ownership is implicit through account.user_id, no AccountShare needed.

    Returns:
        Account instance for testing transactions
    """
    from decimal import Decimal
    from src.models.account import Account

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        account = Account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_type_id=savings_account_type.id,
            account_name="Test Checking",
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        session.add(account)
        await session.commit()
        await session.refresh(account)

        return account


# ============================================================================
# Card Fixtures
# ============================================================================
@pytest_asyncio.fixture
async def test_card(test_engine, test_account, test_user) -> "Card":
    """
    Create a test card for the test user.

    Returns:
        Card instance linked to test_account
    """
    from src.models.card import Card
    from src.models.enums import CardType
    from decimal import Decimal

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        card = Card(
            account_id=test_account.id,
            card_type=CardType.credit_card,
            name="Test Credit Card",
            last_four_digits="4242",
            card_network="Visa",
            expiry_month=12,
            expiry_year=2027,
            credit_limit=Decimal("10000.00"),
            notes="Test card for integration tests",
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        session.add(card)
        await session.commit()
        await session.refresh(card)

        return card


@pytest_asyncio.fixture
async def test_financial_institution_for_cards(test_engine):
    """Get or create a test financial institution for cards."""
    from src.models.financial_institution import FinancialInstitution

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Try to get existing institution (not soft deleted)
        result = await session.execute(
            text(
                "SELECT * FROM financial_institutions WHERE deleted_at IS NULL LIMIT 1"
            )
        )
        row = result.first()

        if row:
            institution = await session.get(FinancialInstitution, row[0])
            return institution

        # Create new one if none exist
        institution = FinancialInstitution(
            name="Test Bank",
            institution_type="bank",
        )
        session.add(institution)
        await session.commit()
        await session.refresh(institution)

        return institution
