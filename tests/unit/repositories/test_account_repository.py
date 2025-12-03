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

from src.repositories.account_repository import AccountRepository


@pytest.mark.asyncio
class TestAccountRepository:
    """Test suite for AccountRepository."""

    async def test_create_account(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test creating an account."""
        repo = AccountRepository(db_session)

        account = await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        assert account.id is not None
        assert account.account_name == "Test Savings"
        assert account.account_type_id == savings_account_type.id
        assert account.currency == "USD"
        assert account.opening_balance == Decimal("1000.00")
        assert account.current_balance == Decimal("1000.00")
        assert account.is_active is True
        assert account.deleted_at is None

    async def test_get_by_id(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test getting account by ID."""
        repo = AccountRepository(db_session)

        # Create account
        created = await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test Account",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("500.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        # Retrieve by ID
        account = await repo.get_by_id(created.id)

        assert account is not None
        assert account.id == created.id
        assert account.account_name == "Test Account"

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
        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Credit Card",
            account_type_id=other_account_type.id,
            currency="USD",
            opening_balance=Decimal("-500.00"),
            current_balance=Decimal("-500.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

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

        # Create accounts with different types and statuses
        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Active Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Inactive Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("500.00"),
            current_balance=Decimal("500.00"),
            is_active=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Active Other",
            account_type_id=other_account_type.id,
            currency="USD",
            opening_balance=Decimal("-200.00"),
            current_balance=Decimal("-200.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        # Filter by is_active=True
        active_accounts = await repo.get_by_user(user_id=test_user.id, is_active=True)
        assert len(active_accounts) == 2
        assert all(acc.is_active for acc in active_accounts)

        # Filter by account_type_id
        savings_accounts = await repo.get_by_user(
            user_id=test_user.id, account_type_id=savings_account_type.id
        )
        assert len(savings_accounts) == 2
        assert all(
            acc.account_type_id == savings_account_type.id for acc in savings_accounts
        )

        # Filter by both
        active_savings = await repo.get_by_user(
            user_id=test_user.id,
            is_active=True,
            account_type_id=savings_account_type.id,
        )
        assert len(active_savings) == 1
        assert active_savings[0].account_name == "Active Savings"

    async def test_get_by_user_pagination(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test pagination for get_by_user."""
        repo = AccountRepository(db_session)

        # Create 5 accounts
        for i in range(5):
            await repo.create(
                user_id=test_user.id,
                financial_institution_id=test_financial_institution.id,
                account_name=f"Account {i}",
                account_type_id=savings_account_type.id,
                currency="USD",
                opening_balance=Decimal("100.00"),
                current_balance=Decimal("100.00"),
                is_active=True,
                created_by=test_user.id,
                updated_by=test_user.id,
            )

        # Get first page
        page1 = await repo.get_by_user(user_id=test_user.id, skip=0, limit=2)
        assert len(page1) == 2

        # Get second page
        page2 = await repo.get_by_user(user_id=test_user.id, skip=2, limit=2)
        assert len(page2) == 2

        # Get third page
        page3 = await repo.get_by_user(user_id=test_user.id, skip=4, limit=2)
        assert len(page3) == 1

    async def test_get_by_name(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test getting account by name."""
        repo = AccountRepository(db_session)

        # Create account
        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="My Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        # Get by exact name
        account = await repo.get_by_name(
            user_id=test_user.id, account_name="My Savings"
        )
        assert account is not None
        assert account.account_name == "My Savings"

        # Get by case-insensitive name
        account = await repo.get_by_name(
            user_id=test_user.id, account_name="my savings"
        )
        assert account is not None
        assert account.account_name == "My Savings"

        # Get non-existent
        account = await repo.get_by_name(
            user_id=test_user.id, account_name="Non Existent"
        )
        assert account is None

    async def test_exists_by_name(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test checking if account name exists."""
        repo = AccountRepository(db_session)

        # Create account
        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Existing Account",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

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
        account1 = await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Account One",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Account Two",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("2000.00"),
            current_balance=Decimal("2000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

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

        # Create active accounts
        for i in range(3):
            await repo.create(
                user_id=test_user.id,
                financial_institution_id=test_financial_institution.id,
                account_name=f"Active {i}",
                account_type_id=savings_account_type.id,
                currency="USD",
                opening_balance=Decimal("100.00"),
                current_balance=Decimal("100.00"),
                is_active=True,
                created_by=test_user.id,
                updated_by=test_user.id,
            )

        # Create inactive account
        await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Inactive",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
            is_active=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        # Count all accounts
        count = await repo.count_user_accounts(user_id=test_user.id)
        assert count == 4

        # Count only active
        count = await repo.count_user_accounts(user_id=test_user.id, is_active=True)
        assert count == 3

        # Count only inactive
        count = await repo.count_user_accounts(user_id=test_user.id, is_active=False)
        assert count == 1

    async def test_soft_delete_filtering(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test that soft-deleted accounts are filtered out."""
        repo = AccountRepository(db_session)

        # Create account
        account = await repo.create(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="To Delete",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

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
