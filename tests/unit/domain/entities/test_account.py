"""Unit tests for Account entity."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.account import Account
from app.domain.exceptions import (
    CurrencyMismatchError,
    InsufficientBalanceError,
    InvalidAccountStateError,
)
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.money import Money


class TestAccountCreation:
    """Test Account entity creation."""

    def test_create_account_minimal(self):
        """Test creating account with minimal data."""
        account_id = uuid4()
        user_id = uuid4()
        balance = Money(amount=Decimal("0"), currency=Currency.USD)

        account = Account(
            id=account_id,
            user_id=user_id,
            name="Checking",
            description="Main checking account",
            balance=balance
        )

        assert account.id == account_id
        assert account.user_id == user_id
        assert account.name == "Checking"
        assert account.balance == balance
        assert account.is_active is True

    def test_empty_name_raises_error(self):
        """Test empty name raises error."""
        with pytest.raises(ValueError):
            Account(
                id=uuid4(),
                user_id=uuid4(),
                name="",
                description=None,
                balance=Money(amount=0, currency=Currency.USD)
            )

    def test_name_too_long_raises_error(self):
        """Test name exceeding max length raises error."""
        with pytest.raises(ValueError):
            Account(
                id=uuid4(),
                user_id=uuid4(),
                name="x" * 101,
                description=None,
                balance=Money(amount=0, currency=Currency.USD)
            )

    def test_description_too_long_raises_error(self):
        """Test description exceeding max length raises error."""
        with pytest.raises(ValueError):
            Account(
                id=uuid4(),
                user_id=uuid4(),
                name="Test",
                description="x" * 501,
                balance=Money(amount=0, currency=Currency.USD)
            )


class TestAccountOwnership:
    """Test Account ownership methods."""

    def test_is_owned_by_true(self):
        """Test is_owned_by returns True for owner."""
        user_id = uuid4()
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        assert account.is_owned_by(user_id) is True

    def test_is_owned_by_false(self):
        """Test is_owned_by returns False for non-owner."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        assert account.is_owned_by(uuid4()) is False

    def test_is_shared_with_true(self):
        """Test is_shared_with returns True when shared."""
        shared_user_id = uuid4()
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            shared_with_user_ids=[shared_user_id]
        )
        assert account.is_shared_with(shared_user_id) is True

    def test_is_shared_with_false(self):
        """Test is_shared_with returns False when not shared."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        assert account.is_shared_with(uuid4()) is False

    def test_can_be_accessed_by_owner(self):
        """Test can_be_accessed_by returns True for owner."""
        user_id = uuid4()
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        assert account.can_be_accessed_by(user_id) is True

    def test_can_be_accessed_by_shared_user(self):
        """Test can_be_accessed_by returns True for shared user."""
        shared_user_id = uuid4()
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            shared_with_user_ids=[shared_user_id]
        )
        assert account.can_be_accessed_by(shared_user_id) is True


class TestAccountActivation:
    """Test Account activation/deactivation."""

    def test_activate_inactive_account(self):
        """Test activating an inactive account."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            is_active=False
        )
        account.activate()
        assert account.is_active is True

    def test_activate_already_active_raises_error(self):
        """Test activating already active account raises error."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            is_active=True
        )
        with pytest.raises(InvalidAccountStateError):
            account.activate()

    def test_deactivate_active_account(self):
        """Test deactivating an active account."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            is_active=True
        )
        account.deactivate()
        assert account.is_active is False

    def test_deactivate_already_inactive_raises_error(self):
        """Test deactivating already inactive account raises error."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            is_active=False
        )
        with pytest.raises(InvalidAccountStateError):
            account.deactivate()


class TestAccountUpdates:
    """Test Account update methods."""

    def test_update_name(self):
        """Test updating account name."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Old Name",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        account.update_name("New Name")
        assert account.name == "New Name"

    def test_update_name_strips_whitespace(self):
        """Test update_name strips whitespace."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        account.update_name("  New Name  ")
        assert account.name == "New Name"

    def test_update_description(self):
        """Test updating account description."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description="Old",
            balance=Money(amount=0, currency=Currency.USD)
        )
        account.update_description("New description")
        assert account.description == "New description"


class TestAccountBalanceOperations:
    """Test Account balance operations."""

    def test_add_funds(self):
        """Test adding funds to account."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        account.add_funds(Money(amount=50, currency=Currency.USD))
        assert account.balance.amount == Decimal("150.00")

    def test_add_funds_currency_mismatch_raises_error(self):
        """Test adding funds with different currency raises error."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        with pytest.raises(CurrencyMismatchError):
            account.add_funds(Money(amount=50, currency=Currency.EUR))

    def test_add_negative_funds_raises_error(self):
        """Test adding negative amount raises error."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        with pytest.raises(ValueError):
            account.add_funds(Money(amount=-50, currency=Currency.USD))

    def test_subtract_funds(self):
        """Test subtracting funds from account."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        account.subtract_funds(Money(amount=30, currency=Currency.USD))
        assert account.balance.amount == Decimal("70.00")

    def test_subtract_funds_insufficient_balance_raises_error(self):
        """Test subtracting more than balance raises error."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=50, currency=Currency.USD)
        )
        with pytest.raises(InsufficientBalanceError):
            account.subtract_funds(Money(amount=100, currency=Currency.USD))

    def test_set_balance(self):
        """Test setting balance directly."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        account.set_balance(Money(amount=500, currency=Currency.USD))
        assert account.balance.amount == Decimal("500.00")

    def test_has_sufficient_balance_true(self):
        """Test has_sufficient_balance returns True when sufficient."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        assert account.has_sufficient_balance(Money(amount=50, currency=Currency.USD)) is True

    def test_has_sufficient_balance_false(self):
        """Test has_sufficient_balance returns False when insufficient."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=50, currency=Currency.USD)
        )
        assert account.has_sufficient_balance(Money(amount=100, currency=Currency.USD)) is False


class TestAccountSharing:
    """Test Account sharing methods."""

    def test_share_with_user(self):
        """Test sharing account with user."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        user_id = uuid4()
        account.share_with_user(user_id)
        assert user_id in account.shared_with_user_ids

    def test_share_with_owner_raises_error(self):
        """Test sharing with owner raises error."""
        user_id = uuid4()
        account = Account(
            id=uuid4(),
            user_id=user_id,
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        with pytest.raises(ValueError):
            account.share_with_user(user_id)

    def test_unshare_with_user(self):
        """Test unsharing account with user."""
        shared_user_id = uuid4()
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD),
            shared_with_user_ids=[shared_user_id]
        )
        account.unshare_with_user(shared_user_id)
        assert shared_user_id not in account.shared_with_user_ids


class TestAccountDeletion:
    """Test Account soft deletion."""

    def test_soft_delete(self):
        """Test soft deleting account."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        account.soft_delete()
        assert account.is_deleted() is True
        assert account.deleted_at is not None
        assert account.is_active is False

    def test_soft_delete_already_deleted_raises_error(self):
        """Test soft deleting already deleted account raises error."""
        account = Account(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            description=None,
            balance=Money(amount=0, currency=Currency.USD)
        )
        account.soft_delete()
        with pytest.raises(InvalidAccountStateError):
            account.soft_delete()


class TestAccountEquality:
    """Test Account equality."""

    def test_accounts_with_same_id_are_equal(self):
        """Test accounts with same ID are equal."""
        account_id = uuid4()
        account1 = Account(
            id=account_id,
            user_id=uuid4(),
            name="Account1",
            description=None,
            balance=Money(amount=100, currency=Currency.USD)
        )
        account2 = Account(
            id=account_id,
            user_id=uuid4(),
            name="Account2",
            description=None,
            balance=Money(amount=200, currency=Currency.EUR)
        )
        assert account1 == account2
