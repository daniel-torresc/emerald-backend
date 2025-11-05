"""Unit tests for CreateAccountUseCase."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.application.dto.account_dto import CreateAccountInput
from app.application.exceptions import AlreadyExistsError
from app.application.use_cases.accounts.create_account import CreateAccountUseCase
from app.domain.entities.account import Account
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.money import Money


@pytest.fixture
def mock_uow():
    """Create a mock Unit of Work."""
    uow = Mock()
    uow.accounts = Mock()
    uow.commit = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)  # Don't suppress exceptions
    return uow


@pytest.fixture
def create_account_input():
    """Create sample account creation input."""
    return CreateAccountInput(
        name="Checking Account", description="Main checking account"
    )


class TestCreateAccountUseCase:
    """Test CreateAccountUseCase."""

    @pytest.mark.asyncio
    async def test_create_account_success(self, mock_uow, create_account_input):
        """Test successful account creation."""
        # Arrange
        user_id = uuid4()
        mock_uow.accounts.find_by_user_and_name = AsyncMock(return_value=None)

        created_account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Checking Account",
            description="Main checking account",
            balance=Money(amount=Decimal("0.00"), currency=Currency.USD),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None,
            shared_with_user_ids=[],
        )
        mock_uow.accounts.add = AsyncMock(return_value=created_account)

        use_case = CreateAccountUseCase(mock_uow)

        # Act
        result = await use_case.execute(create_account_input, user_id)

        # Assert
        assert result.name == "Checking Account"
        assert result.description == "Main checking account"
        assert result.balance == Decimal("0.00")
        assert result.currency == "USD"
        assert result.is_active is True
        assert result.user_id == user_id

        # Verify interactions
        mock_uow.accounts.find_by_user_and_name.assert_called_once_with(
            user_id=user_id, name="Checking Account"
        )
        mock_uow.accounts.add.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_account_duplicate_name(self, mock_uow, create_account_input):
        """Test account creation fails when name already exists for user."""
        # Arrange
        user_id = uuid4()
        existing_account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Checking Account",
            description="Existing account",
            balance=Money(amount=Decimal("100.00"), currency=Currency.USD),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None,
            shared_with_user_ids=[],
        )
        mock_uow.accounts.find_by_user_and_name = AsyncMock(
            return_value=existing_account
        )

        use_case = CreateAccountUseCase(mock_uow)

        # Act & Assert
        with pytest.raises(AlreadyExistsError) as exc_info:
            await use_case.execute(create_account_input, user_id)

        assert "already exists" in str(exc_info.value).lower()
        mock_uow.accounts.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_account_starts_with_zero_balance(
        self, mock_uow, create_account_input
    ):
        """Test that new accounts start with zero balance."""
        # Arrange
        user_id = uuid4()
        mock_uow.accounts.find_by_user_and_name = AsyncMock(return_value=None)

        created_account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Checking Account",
            description="Main checking account",
            balance=Money(amount=Decimal("0.00"), currency=Currency.USD),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None,
            shared_with_user_ids=[],
        )
        mock_uow.accounts.add = AsyncMock(return_value=created_account)

        use_case = CreateAccountUseCase(mock_uow)

        # Act
        await use_case.execute(create_account_input, user_id)

        # Assert
        call_args = mock_uow.accounts.add.call_args
        account_entity = call_args[0][0]
        assert account_entity.balance.amount == Decimal("0.00")
        assert account_entity.balance.currency == Currency.USD

    @pytest.mark.asyncio
    async def test_create_account_is_active_by_default(
        self, mock_uow, create_account_input
    ):
        """Test that new accounts are active by default."""
        # Arrange
        user_id = uuid4()
        mock_uow.accounts.find_by_user_and_name = AsyncMock(return_value=None)

        created_account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Checking Account",
            description="Main checking account",
            balance=Money(amount=Decimal("0.00"), currency=Currency.USD),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None,
            shared_with_user_ids=[],
        )
        mock_uow.accounts.add = AsyncMock(return_value=created_account)

        use_case = CreateAccountUseCase(mock_uow)

        # Act
        result = await use_case.execute(create_account_input, user_id)

        # Assert
        assert result.is_active is True
