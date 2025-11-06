"""Unit tests for RegisterUserUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.application.dto.auth_dto import RegisterUserInput
from app.application.exceptions import AlreadyExistsError
from app.application.use_cases.auth.register_user import RegisterUserUseCase
from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.value_objects.username import Username


@pytest.fixture
def mock_uow():
    """Create a mock Unit of Work."""
    uow = Mock()
    uow.users = Mock()
    uow.commit = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)  # Don't suppress exceptions
    return uow


@pytest.fixture
def password_hasher():
    """Create a mock password hasher."""
    return lambda password: f"hashed_{password}"


@pytest.fixture
def register_input():
    """Create sample registration input."""
    return RegisterUserInput(
        email="test@example.com",
        username="testuser",
        password="SecurePass123",
        full_name="Test User",
    )


class TestRegisterUserUseCase:
    """Test RegisterUserUseCase."""

    @pytest.mark.asyncio
    async def test_register_user_success(
        self, mock_uow, password_hasher, register_input
    ):
        """Test successful user registration."""
        # Arrange
        mock_uow.users.exists_by_email = AsyncMock(return_value=False)
        mock_uow.users.exists_by_username = AsyncMock(return_value=False)

        created_user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("hashed_SecurePass123"),
            full_name="Test User",
            is_active=True,
            is_admin=False,
            roles=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None,
        )
        mock_uow.users.add = AsyncMock(return_value=created_user)

        use_case = RegisterUserUseCase(mock_uow)

        # Act
        result = await use_case.execute(register_input, password_hasher)

        # Assert
        assert result.email == "test@example.com"
        assert result.username == "testuser"
        assert result.full_name == "Test User"
        assert result.is_active is True
        assert result.is_admin is False

        # Verify interactions
        mock_uow.users.exists_by_email.assert_called_once()
        mock_uow.users.exists_by_username.assert_called_once()
        mock_uow.users.add.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_email_already_exists(
        self, mock_uow, password_hasher, register_input
    ):
        """Test registration fails when email already exists."""
        # Arrange
        mock_uow.users.exists_by_email = AsyncMock(return_value=True)
        mock_uow.users.add = AsyncMock()
        use_case = RegisterUserUseCase(mock_uow)

        # Act & Assert
        with pytest.raises(AlreadyExistsError) as exc_info:
            await use_case.execute(register_input, password_hasher)

        assert "email" in str(exc_info.value).lower()
        mock_uow.users.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_user_username_already_exists(
        self, mock_uow, password_hasher, register_input
    ):
        """Test registration fails when username already exists."""
        # Arrange
        mock_uow.users.exists_by_email = AsyncMock(return_value=False)
        mock_uow.users.exists_by_username = AsyncMock(return_value=True)
        mock_uow.users.add = AsyncMock()
        use_case = RegisterUserUseCase(mock_uow)

        # Act & Assert
        with pytest.raises(AlreadyExistsError) as exc_info:
            await use_case.execute(register_input, password_hasher)

        assert "username" in str(exc_info.value).lower()
        mock_uow.users.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_user_password_is_hashed(
        self, mock_uow, password_hasher, register_input
    ):
        """Test that password is properly hashed before storage."""
        # Arrange
        mock_uow.users.exists_by_email = AsyncMock(return_value=False)
        mock_uow.users.exists_by_username = AsyncMock(return_value=False)

        created_user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            username=Username("testuser"),
            password_hash=PasswordHash("hashed_SecurePass123"),
            full_name="Test User",
            is_active=True,
            is_admin=False,
            roles=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None,
        )
        mock_uow.users.add = AsyncMock(return_value=created_user)

        use_case = RegisterUserUseCase(mock_uow)

        # Act
        await use_case.execute(register_input, password_hasher)

        # Assert
        call_args = mock_uow.users.add.call_args
        user_entity = call_args[0][0]
        assert user_entity.password_hash.value == "hashed_SecurePass123"
        assert user_entity.password_hash.value != register_input.password
