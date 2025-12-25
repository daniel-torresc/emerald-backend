"""
Unit tests for AccountRepository.

Tests:
- Account creation
- Get account by ID
- Get accounts by user
- Get account by name
- Check name existence
- Count user accounts
- Soft delete filtering
"""

from decimal import Decimal

import pytest

from models.account import Account
from repositories.account_repository import AccountRepository


def create_account_instance(
    user_id,
    financial_institution_id,
    account_name,
    account_type_id,
    currency="USD",
    opening_balance=Decimal("1000.00"),
    current_balance=None,
    created_by=None,
    updated_by=None,
):
    """Helper to create Account instances for tests."""
    if current_balance is None:
        current_balance = opening_balance
    if created_by is None:
        created_by = user_id
    if updated_by is None:
        updated_by = user_id
    return Account(
        user_id=user_id,
        financial_institution_id=financial_institution_id,
        account_name=account_name,
        account_type_id=account_type_id,
        currency=currency,
        opening_balance=opening_balance,
        current_balance=current_balance,
        created_by=created_by,
        updated_by=updated_by,
    )


@pytest.mark.asyncio
class TestAccountRepository:
    """Test suite for AccountRepository."""

    async def test_add_account(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test adding an account."""
        repo = AccountRepository(db_session)

        account = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
        )
        account = await repo.add(account)

        assert account.id is not None
        assert account.account_name == "Test Savings"
        assert account.account_type_id == savings_account_type.id
        assert account.currency == "USD"
        assert account.opening_balance == Decimal("1000.00")
        assert account.current_balance == Decimal("1000.00")
        assert account.deleted_at is None

    async def test_get_by_id(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test getting account by ID."""
        repo = AccountRepository(db_session)

        # Create account
        account = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test Account",
            account_type_id=savings_account_type.id,
            opening_balance=Decimal("500.00"),
        )
        created = await repo.add(account)

        # Retrieve by ID
        found = await repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.account_name == "Test Account"

    async def test_get_by_user(
        self,
        db_session,
        test_user,
        test_financial_institution,
        savings_account_type,
        other_account_type,
    ):
        """Test getting all accounts for a user."""
        repo = AccountRepository(db_session)

        # Create multiple accounts
        account1 = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Savings",
            account_type_id=savings_account_type.id,
        )
        await repo.add(account1)

        account2 = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Credit Card",
            account_type_id=other_account_type.id,
            opening_balance=Decimal("-500.00"),
        )
        await repo.add(account2)

        # Get all accounts for user
        accounts = await repo.get_by_user(user_id=test_user.id)

        assert len(accounts) == 2
        assert all(acc.user_id == test_user.id for acc in accounts)

    async def test_get_by_user_with_filters(
        self,
        db_session,
        test_user,
        test_financial_institution,
        savings_account_type,
        other_account_type,
    ):
        """Test getting accounts with filters."""
        repo = AccountRepository(db_session)

        # Create accounts with different types
        account1 = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Active Savings",
            account_type_id=savings_account_type.id,
        )
        await repo.add(account1)

        account2 = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Inactive Savings",
            account_type_id=savings_account_type.id,
            opening_balance=Decimal("500.00"),
        )
        await repo.add(account2)

        account3 = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Active Other",
            account_type_id=other_account_type.id,
            opening_balance=Decimal("-200.00"),
        )
        await repo.add(account3)

        # Get all accounts
        all_accounts = await repo.get_by_user(user_id=test_user.id)
        assert len(all_accounts) == 3

        # Filter by account_type_id
        savings_accounts = await repo.get_by_user(
            user_id=test_user.id, account_type_id=savings_account_type.id
        )
        assert len(savings_accounts) == 2
        assert all(
            acc.account_type_id == savings_account_type.id for acc in savings_accounts
        )

    async def test_get_by_name(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test getting account by name."""
        repo = AccountRepository(db_session)

        # Create account
        account = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="My Savings",
            account_type_id=savings_account_type.id,
        )
        await repo.add(account)

        # Get by exact name
        found = await repo.get_by_name(user_id=test_user.id, account_name="My Savings")
        assert found is not None
        assert found.account_name == "My Savings"

        # Get by case-insensitive name
        found = await repo.get_by_name(user_id=test_user.id, account_name="my savings")
        assert found is not None
        assert found.account_name == "My Savings"

        # Get non-existent
        found = await repo.get_by_name(
            user_id=test_user.id, account_name="Non Existent"
        )
        assert found is None

    async def test_exists_by_name(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test checking if account name exists."""
        repo = AccountRepository(db_session)

        # Create account
        account = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Existing Account",
            account_type_id=savings_account_type.id,
        )
        await repo.add(account)

        # Check exists
        exists = await repo.exists_by_name(
            user_id=test_user.id, account_name="Existing Account"
        )
        assert exists is True

        # Check case-insensitive
        exists = await repo.exists_by_name(
            user_id=test_user.id, account_name="EXISTING ACCOUNT"
        )
        assert exists is True

        # Check non-existent
        exists = await repo.exists_by_name(
            user_id=test_user.id, account_name="Non Existent"
        )
        assert exists is False

    async def test_exists_by_name_with_exclude(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test checking name existence with exclude_id."""
        repo = AccountRepository(db_session)

        # Create two accounts
        account1 = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Account One",
            account_type_id=savings_account_type.id,
        )
        account1 = await repo.add(account1)

        account2 = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Account Two",
            account_type_id=savings_account_type.id,
            opening_balance=Decimal("2000.00"),
        )
        await repo.add(account2)

        # Check if "Account Two" exists (excluding account1)
        exists = await repo.exists_by_name(
            user_id=test_user.id, account_name="Account Two", exclude_id=account1.id
        )
        assert exists is True

        # Check if "Account One" exists (excluding account1 itself)
        exists = await repo.exists_by_name(
            user_id=test_user.id, account_name="Account One", exclude_id=account1.id
        )
        assert exists is False  # Should not find itself

    async def test_count_user_accounts(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test counting user accounts."""
        repo = AccountRepository(db_session)

        # Initially no accounts
        count = await repo.count_user_accounts(user_id=test_user.id)
        assert count == 0

        # Create accounts
        for i in range(3):
            account = create_account_instance(
                user_id=test_user.id,
                financial_institution_id=test_financial_institution.id,
                account_name=f"Account {i}",
                account_type_id=savings_account_type.id,
                opening_balance=Decimal("100.00"),
            )
            await repo.add(account)

        # Count all accounts
        count = await repo.count_user_accounts(user_id=test_user.id)
        assert count == 3

    async def test_soft_delete_filtering(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test that soft-deleted accounts are filtered out."""
        repo = AccountRepository(db_session)

        # Create account
        account = create_account_instance(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="To Delete",
            account_type_id=savings_account_type.id,
        )
        account = await repo.add(account)

        # Verify it exists
        found = await repo.get_by_id(account.id)
        assert found is not None

        # Soft delete
        await repo.soft_delete(account)

        # Should not be found after soft delete
        found = await repo.get_by_id(account.id)
        assert found is None

        # Should not appear in user's accounts
        accounts = await repo.get_by_user(user_id=test_user.id)
        assert len(accounts) == 0

        # Should not be counted
        count = await repo.count_user_accounts(user_id=test_user.id)
        assert count == 0
