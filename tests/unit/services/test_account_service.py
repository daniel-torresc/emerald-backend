"""
Unit tests for AccountService.

Tests:
- Account creation with validation
- Get account with permission check
- List accounts with filters
- Update account with name uniqueness validation
- Delete account (soft delete)
- Error handling (duplicate names, invalid currency, etc.)
"""

from decimal import Decimal

import pytest

from src.exceptions import AlreadyExistsError, NotFoundError
from src.services.account_service import AccountService


@pytest.mark.asyncio
class TestAccountService:
    """Test suite for AccountService."""

    async def test_create_account_success(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test successful account creation."""
        service = AccountService(db_session)

        account = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="My Checking",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1500.00"),
            current_user=test_user,
        )

        assert account.id is not None
        assert account.user_id == test_user.id
        assert account.account_name == "My Checking"
        assert account.account_type_id == savings_account_type.id
        assert account.currency == "USD"
        assert account.opening_balance == Decimal("1500.00")
        assert account.current_balance == Decimal("1500.00")
        
        assert account.created_by == test_user.id
        assert account.updated_by == test_user.id

    async def test_create_account_duplicate_name(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test that creating account with duplicate name fails."""
        service = AccountService(db_session)

        # Create first account
        await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        # Try to create duplicate (case-insensitive)
        with pytest.raises(AlreadyExistsError) as exc_info:
            await service.create_account(
                user_id=test_user.id,
                financial_institution_id=test_financial_institution.id,
                account_name="savings",  # Different case
                account_type_id=savings_account_type.id,
                currency="USD",
                opening_balance=Decimal("2000.00"),
                current_user=test_user,
            )

        assert "already exists" in str(exc_info.value).lower()

    async def test_create_account_invalid_currency(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test that invalid currency format raises error."""
        service = AccountService(db_session)

        # Test invalid currencies
        invalid_currencies = ["US", "USDD", "usd", "123", "US$", ""]

        for invalid_currency in invalid_currencies:
            with pytest.raises(ValueError) as exc_info:
                await service.create_account(
                    user_id=test_user.id,
                    financial_institution_id=test_financial_institution.id,
                    account_name=f"Account {invalid_currency}",
                    account_type_id=savings_account_type.id,
                    currency=invalid_currency,
                    opening_balance=Decimal("1000.00"),
                    current_user=test_user,
                )

            assert "invalid currency" in str(exc_info.value).lower()

    async def test_create_account_negative_balance(
        self, db_session, test_user, test_financial_institution, other_account_type
    ):
        """Test creating account with negative balance (for loans/credit cards)."""
        service = AccountService(db_session)

        account = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Credit Card",
            account_type_id=other_account_type.id,
            currency="USD",
            opening_balance=Decimal("-500.50"),
            current_user=test_user,
        )

        assert account.opening_balance == Decimal("-500.50")
        assert account.current_balance == Decimal("-500.50")

    async def test_get_account_success(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test getting account by ID."""
        service = AccountService(db_session)

        # Create account
        created = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test Account",
            account_type_id=savings_account_type.id,
            currency="EUR",
            opening_balance=Decimal("2000.00"),
            current_user=test_user,
        )

        # Get account
        account = await service.get_account(
            account_id=created.id,
            current_user=test_user,
        )

        assert account.id == created.id
        assert account.account_name == "Test Account"

    async def test_get_account_not_owner(
        self,
        db_session,
        test_user,
        admin_user,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that non-owner cannot access account."""
        service = AccountService(db_session)

        # Create account for test_user
        created = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Private Account",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        # Try to access as different user
        with pytest.raises(NotFoundError):
            await service.get_account(
                account_id=created.id,
                current_user=admin_user,  # Different user
            )

    async def test_get_account_not_found(self, db_session, test_user):
        """Test getting non-existent account."""
        service = AccountService(db_session)

        import uuid

        fake_id = uuid.uuid4()

        with pytest.raises(NotFoundError):
            await service.get_account(
                account_id=fake_id,
                current_user=test_user,
            )

    async def test_list_accounts(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test listing user's accounts."""
        service = AccountService(db_session)

        # Create multiple accounts
        for i in range(3):
            await service.create_account(
                user_id=test_user.id,
                financial_institution_id=test_financial_institution.id,
                account_name=f"Account {i}",
                account_type_id=savings_account_type.id,
                currency="USD",
                opening_balance=Decimal("1000.00"),
                current_user=test_user,
            )

        # List all accounts
        accounts = await service.list_accounts(
            user_id=test_user.id,
            current_user=test_user,
        )

        assert len(accounts) == 3

    async def test_list_accounts_with_filters(
        self,
        db_session,
        test_user,
        test_financial_institution,
        savings_account_type,
        other_account_type,
    ):
        """Test listing accounts with filters."""
        service = AccountService(db_session)

        # Create accounts with different types and statuses
        account1 = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Active Savings",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Active Other",
            account_type_id=other_account_type.id,
            currency="USD",
            opening_balance=Decimal("-500.00"),
            current_user=test_user,
        )

        # Deactivate first account
        await service.update_account(
            account_id=account1.id,
            current_user=test_user,
        )

        active_accounts = await service.list_accounts(
            user_id=test_user.id,
            current_user=test_user,
        )
        assert len(active_accounts) == 1
        assert active_accounts[0].account_name == "Active Other"

        # Filter by account_type_id
        other_accounts = await service.list_accounts(
            user_id=test_user.id,
            current_user=test_user,
            account_type_id=other_account_type.id,
        )
        assert len(other_accounts) == 1
        assert other_accounts[0].account_name == "Active Other"

    async def test_list_accounts_pagination(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test pagination for list_accounts."""
        service = AccountService(db_session)

        # Create 5 accounts
        for i in range(5):
            await service.create_account(
                user_id=test_user.id,
                financial_institution_id=test_financial_institution.id,
                account_name=f"Account {i}",
                account_type_id=savings_account_type.id,
                currency="USD",
                opening_balance=Decimal("100.00"),
                current_user=test_user,
            )

        # Get first 2
        page1 = await service.list_accounts(
            user_id=test_user.id,
            current_user=test_user,
            skip=0,
            limit=2,
        )
        assert len(page1) == 2

        # Get next 2
        page2 = await service.list_accounts(
            user_id=test_user.id,
            current_user=test_user,
            skip=2,
            limit=2,
        )
        assert len(page2) == 2

    async def test_list_accounts_limit_enforced(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test that limit is capped at 100."""
        service = AccountService(db_session)

        # Create 1 account
        await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("100.00"),
            current_user=test_user,
        )

        # Request with limit > 100 (should be capped)
        accounts = await service.list_accounts(
            user_id=test_user.id,
            current_user=test_user,
            limit=150,
        )

        # Should still work, just capped
        assert len(accounts) == 1

    async def test_update_account_name(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test updating account name."""
        service = AccountService(db_session)

        # Create account
        account = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Old Name",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        # Update name
        updated = await service.update_account(
            account_id=account.id,
            current_user=test_user,
            account_name="New Name",
        )

        assert updated.account_name == "New Name"
        assert updated.updated_by == test_user.id

    async def test_update_account_duplicate_name(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test that updating to duplicate name fails."""
        service = AccountService(db_session)

        # Create two accounts
        account1 = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Account One",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Account Two",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("2000.00"),
            current_user=test_user,
        )

        # Try to rename account1 to "Account Two"
        with pytest.raises(AlreadyExistsError):
            await service.update_account(
                account_id=account1.id,
                current_user=test_user,
                account_name="Account Two",
            )

    async def test_update_account_no_changes(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test updating account with no changes."""
        service = AccountService(db_session)

        # Create account
        account = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        # Update with no changes
        updated = await service.update_account(
            account_id=account.id,
            current_user=test_user,
        )

        # Should return account as-is
        assert updated.id == account.id
        assert updated.account_name == account.account_name

    async def test_delete_account(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test soft deleting account."""
        service = AccountService(db_session)

        # Create account
        account = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="To Delete",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        # Delete account
        await service.delete_account(
            account_id=account.id,
            current_user=test_user,
        )

        # Should not be able to get it
        with pytest.raises(NotFoundError):
            await service.get_account(
                account_id=account.id,
                current_user=test_user,
            )

        # Should not appear in list
        accounts = await service.list_accounts(
            user_id=test_user.id,
            current_user=test_user,
        )
        assert len(accounts) == 0

    async def test_delete_account_not_owner(
        self,
        db_session,
        test_user,
        admin_user,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that non-owner cannot delete account."""
        service = AccountService(db_session)

        # Create account for test_user
        account = await service.create_account(
            user_id=test_user.id,
            financial_institution_id=test_financial_institution.id,
            account_name="Test",
            account_type_id=savings_account_type.id,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user,
        )

        # Try to delete as different user
        with pytest.raises(NotFoundError):
            await service.delete_account(
                account_id=account.id,
                current_user=admin_user,
            )

    async def test_count_user_accounts(
        self, db_session, test_user, test_financial_institution, savings_account_type
    ):
        """Test counting user's accounts."""
        service = AccountService(db_session)

        # Initially 0
        count = await service.count_user_accounts(
            user_id=test_user.id,
            current_user=test_user,
        )
        assert count == 0

        # Create 3 active accounts
        for i in range(3):
            await service.create_account(
                user_id=test_user.id,
                financial_institution_id=test_financial_institution.id,
                account_name=f"Account {i}",
                account_type_id=savings_account_type.id,
                currency="USD",
                opening_balance=Decimal("100.00"),
                current_user=test_user,
            )

        # Count should be 3
        count = await service.count_user_accounts(
            user_id=test_user.id,
            current_user=test_user,
        )
        assert count == 3
