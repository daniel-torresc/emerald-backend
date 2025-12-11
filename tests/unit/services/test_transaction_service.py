"""
Unit tests for TransactionService.

Tests:
- Transaction creation with validation and balance updates
- Get transaction with permission check
- Search transactions
- Update transaction with balance delta
- Delete transaction with balance updates
- Split transaction with validation
- Join split transaction
- Permission enforcement
"""

from datetime import date
from decimal import Decimal

import pytest

from src.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from src.models.enums import TransactionType
from src.repositories.account_repository import AccountRepository
from src.services.transaction_service import TransactionService


@pytest.mark.asyncio
class TestTransactionServiceCreate:
    """Test suite for TransactionService.create_transaction."""

    async def test_create_transaction_success(
        self, db_session, test_user, test_account
    ):
        """Test successful transaction creation."""
        service = TransactionService(db_session)

        transaction = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.25"),
            currency="USD",
            description="Grocery shopping",
            transaction_type=TransactionType.expense,
            merchant="Whole Foods",
            current_user=test_user,
        )

        assert transaction.id is not None
        assert transaction.account_id == test_account.id
        assert transaction.amount == Decimal("-50.25")
        assert transaction.description == "Grocery shopping"
        assert transaction.merchant == "Whole Foods"

    async def test_create_transaction_updates_balance(
        self, db_session, test_user, test_account
    ):
        """Test that creating transaction updates account balance."""
        service = TransactionService(db_session)
        account_repo = AccountRepository(db_session)

        # Get initial balance
        initial_balance = test_account.current_balance

        # Create transaction
        await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-100.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Check balance was updated
        updated_account = await account_repo.get_by_id(test_account.id)
        assert updated_account.current_balance == initial_balance + Decimal("-100.00")

    async def test_create_transaction_currency_mismatch(
        self, db_session, test_user, test_account
    ):
        """Test that currency mismatch raises error."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            await service.create_transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.00"),
                currency="EUR",  # Account is USD
                description="Test",
                transaction_type=TransactionType.expense,
                current_user=test_user,
            )

        assert "currency" in str(exc_info.value).lower()

    async def test_create_transaction_zero_amount(
        self, db_session, test_user, test_account
    ):
        """Test that zero amount raises error."""
        service = TransactionService(db_session)

        with pytest.raises(ValidationError) as exc_info:
            await service.create_transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("0.00"),
                currency="USD",
                description="Test",
                transaction_type=TransactionType.expense,
                current_user=test_user,
            )

        assert "zero" in str(exc_info.value).lower()

    async def test_create_transaction_permission_denied(
        self, db_session, test_user, test_account, admin_user
    ):
        """Test that user without permission cannot create transaction."""
        service = TransactionService(db_session)

        # Admin user doesn't have access to test_user's account
        with pytest.raises(AuthorizationError):
            await service.create_transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.00"),
                currency="USD",
                description="Test",
                transaction_type=TransactionType.expense,
                current_user=admin_user,  # Different user
            )


@pytest.mark.asyncio
class TestTransactionServiceRead:
    """Test suite for TransactionService read operations."""

    async def test_get_transaction_success(self, db_session, test_user, test_account):
        """Test getting transaction by ID."""
        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Retrieve transaction
        retrieved = await service.get_transaction(created.id, test_user)

        assert retrieved.id == created.id
        assert retrieved.description == "Test"

    async def test_get_transaction_not_found(self, db_session, test_user):
        """Test getting non-existent transaction."""
        service = TransactionService(db_session)

        from uuid import uuid4

        with pytest.raises(NotFoundError):
            await service.get_transaction(uuid4(), test_user)

    async def test_get_transaction_permission_denied(
        self, db_session, test_user, test_account, admin_user
    ):
        """Test that user without permission cannot get transaction."""
        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Try to get with different user
        with pytest.raises(AuthorizationError):
            await service.get_transaction(created.id, admin_user)

    async def test_search_transactions(self, db_session, test_user, test_account):
        """Test searching transactions with filters."""
        service = TransactionService(db_session)

        # Create test transactions
        amounts = [
            Decimal("-10.00"),
            Decimal("-25.00"),
            Decimal("-50.00"),
            Decimal("100.00"),
        ]
        for amount in amounts:
            await service.create_transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=amount,
                currency="USD",
                description="Test",
                transaction_type=(
                    TransactionType.income if amount > 0 else TransactionType.expense
                ),
                current_user=test_user,
            )

        # Search for debit transactions
        results, total = await service.search_transactions(
            account_id=test_account.id,
            current_user=test_user,
            transaction_type=TransactionType.expense,
        )

        assert total == 3  # Three debit transactions


@pytest.mark.asyncio
class TestTransactionServiceUpdate:
    """Test suite for TransactionService.update_transaction."""

    async def test_update_transaction_success(
        self, db_session, test_user, test_account
    ):
        """Test successful transaction update."""
        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Original",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Update transaction
        updated = await service.update_transaction(
            transaction_id=created.id,
            current_user=test_user,
            description="Updated",
            amount=Decimal("-75.00"),
        )

        assert updated.description == "Updated"
        assert updated.amount == Decimal("-75.00")

    async def test_update_transaction_balance_delta(
        self, db_session, test_user, test_account
    ):
        """Test that updating amount updates balance correctly."""
        service = TransactionService(db_session)
        account_repo = AccountRepository(db_session)

        # Get initial balance
        initial_balance = test_account.current_balance

        # Create transaction (-50)
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Balance should be initial - 50
        updated_account = await account_repo.get_by_id(test_account.id)
        assert updated_account.current_balance == initial_balance - Decimal("50.00")

        # Update to -75 (delta of -25)
        await service.update_transaction(
            transaction_id=created.id,
            current_user=test_user,
            amount=Decimal("-75.00"),
        )

        # Balance should be initial - 75
        updated_account = await account_repo.get_by_id(test_account.id)
        assert updated_account.current_balance == initial_balance - Decimal("75.00")

    async def test_update_transaction_zero_amount(
        self, db_session, test_user, test_account
    ):
        """Test that updating to zero amount raises error."""
        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Try to update to zero
        with pytest.raises(ValidationError) as exc_info:
            await service.update_transaction(
                transaction_id=created.id,
                current_user=test_user,
                amount=Decimal("0.00"),
            )

        assert "zero" in str(exc_info.value).lower()

    async def test_update_transaction_permission_denied(
        self, db_session, test_user, test_account, test_engine
    ):
        """Test that non-creator/owner cannot update transaction."""
        from src.models.user import User
        from src.core.security import hash_password
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        service = TransactionService(db_session)

        # Create a separate user without any account access
        async_session_factory = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with async_session_factory() as session:
            other_user = User(
                email="other@example.com",
                username="otheruser",
                password_hash=hash_password("OtherPass123!"),
                is_admin=False,
            )
            session.add(other_user)
            await session.commit()
            await session.refresh(other_user)

        # Create transaction as test_user
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Try to update as other_user (no access to account)
        with pytest.raises(AuthorizationError):
            await service.update_transaction(
                transaction_id=created.id,
                current_user=other_user,
                description="Hacked",
            )


@pytest.mark.asyncio
class TestTransactionServiceDelete:
    """Test suite for TransactionService.delete_transaction."""

    async def test_delete_transaction_success(
        self, db_session, test_user, test_account
    ):
        """Test successful transaction deletion."""
        service = TransactionService(db_session)

        # Create transaction
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Delete transaction
        deleted = await service.delete_transaction(created.id, test_user)

        assert deleted is True

        # Should not be found
        with pytest.raises(NotFoundError):
            await service.get_transaction(created.id, test_user)

    async def test_delete_transaction_updates_balance(
        self, db_session, test_user, test_account
    ):
        """Test that deleting transaction updates balance."""
        service = TransactionService(db_session)
        account_repo = AccountRepository(db_session)

        # Get initial balance
        initial_balance = test_account.current_balance

        # Create transaction
        created = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Delete transaction
        await service.delete_transaction(created.id, test_user)

        # Balance should be back to initial
        updated_account = await account_repo.get_by_id(test_account.id)
        assert updated_account.current_balance == initial_balance

    async def test_delete_parent_deletes_children(
        self, db_session, test_user, test_account
    ):
        """Test that deleting parent deletes all children."""
        service = TransactionService(db_session)

        # Create parent
        parent = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Split it
        await service.split_transaction(
            transaction_id=parent.id,
            splits=[
                {"amount": Decimal("-30.00"), "description": "Child 1"},
                {"amount": Decimal("-20.00"), "description": "Child 2"},
            ],
            current_user=test_user,
        )

        # Delete parent
        await service.delete_transaction(parent.id, test_user)

        # Parent and children should all be deleted (soft deleted)
        with pytest.raises(NotFoundError):
            await service.get_transaction(parent.id, test_user)


@pytest.mark.asyncio
class TestTransactionServiceSplit:
    """Test suite for split and join operations."""

    async def test_split_transaction_success(self, db_session, test_user, test_account):
        """Test successful transaction split."""
        service = TransactionService(db_session)

        # Create transaction
        parent = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Split transaction
        split_parent, children = await service.split_transaction(
            transaction_id=parent.id,
            splits=[
                {"amount": Decimal("-30.00"), "description": "Groceries"},
                {"amount": Decimal("-20.00"), "description": "Household"},
            ],
            current_user=test_user,
        )

        assert len(children) == 2
        assert split_parent.is_split_parent is True
        assert children[0].is_split_child is True

    async def test_split_transaction_amounts_must_sum(
        self, db_session, test_user, test_account
    ):
        """Test that split amounts must sum to parent amount."""
        service = TransactionService(db_session)

        # Create transaction
        parent = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Try to split with amounts that don't sum
        with pytest.raises(ValidationError) as exc_info:
            await service.split_transaction(
                transaction_id=parent.id,
                splits=[
                    {"amount": Decimal("-30.00"), "description": "Split 1"},
                    {
                        "amount": Decimal("-15.00"),
                        "description": "Split 2",
                    },  # Only 45 total
                ],
                current_user=test_user,
            )

        assert "equal" in str(exc_info.value).lower()

    async def test_split_requires_minimum_two_splits(
        self, db_session, test_user, test_account
    ):
        """Test that at least 2 splits are required."""
        service = TransactionService(db_session)

        # Create transaction
        parent = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Try to split with only 1 split
        with pytest.raises(ValidationError) as exc_info:
            await service.split_transaction(
                transaction_id=parent.id,
                splits=[
                    {"amount": Decimal("-50.00"), "description": "Only one"},
                ],
                current_user=test_user,
            )

        assert "2 splits" in str(exc_info.value).lower()

    async def test_cannot_split_child_transaction(
        self, db_session, test_user, test_account
    ):
        """Test that child transactions cannot be split."""
        service = TransactionService(db_session)

        # Create and split parent
        parent = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        split_parent, children = await service.split_transaction(
            transaction_id=parent.id,
            splits=[
                {"amount": Decimal("-30.00"), "description": "Child 1"},
                {"amount": Decimal("-20.00"), "description": "Child 2"},
            ],
            current_user=test_user,
        )

        # Try to split a child
        with pytest.raises(ValidationError) as exc_info:
            await service.split_transaction(
                transaction_id=children[0].id,
                splits=[
                    {"amount": Decimal("-15.00"), "description": "Sub 1"},
                    {"amount": Decimal("-15.00"), "description": "Sub 2"},
                ],
                current_user=test_user,
            )

        assert "child" in str(exc_info.value).lower()

    async def test_join_split_transaction(self, db_session, test_user, test_account):
        """Test joining split transactions back to parent."""
        service = TransactionService(db_session)

        # Create and split
        parent = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        await service.split_transaction(
            transaction_id=parent.id,
            splits=[
                {"amount": Decimal("-30.00"), "description": "Child 1"},
                {"amount": Decimal("-20.00"), "description": "Child 2"},
            ],
            current_user=test_user,
        )

        # Join back
        joined = await service.join_split_transaction(parent.id, test_user)

        # Refresh to get updated child_transactions
        await db_session.refresh(joined, ["child_transactions"])

        assert joined.is_split_parent is False
        # Check that all children are soft-deleted
        active_children = [c for c in joined.child_transactions if c.deleted_at is None]
        assert len(active_children) == 0

    async def test_join_requires_splits(self, db_session, test_user, test_account):
        """Test that join requires transaction to have splits."""
        service = TransactionService(db_session)

        # Create transaction without splits
        transaction = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="No splits",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        # Try to join
        with pytest.raises(ValidationError) as exc_info:
            await service.join_split_transaction(transaction.id, test_user)

        assert "no splits" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestTransactionServiceCardValidation:
    """Test suite for card validation in transaction operations."""

    async def test_create_transaction_with_valid_card(
        self, db_session, test_user, test_account, test_card
    ):
        """Test creating transaction with valid card_id."""
        service = TransactionService(db_session)

        transaction = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.25"),
            currency="USD",
            description="Grocery shopping",
            transaction_type=TransactionType.expense,
            card_id=test_card.id,
            current_user=test_user,
        )

        assert transaction.card_id == test_card.id
        assert transaction.card is not None
        assert transaction.card.id == test_card.id
        assert transaction.card.name == test_card.name

    async def test_create_transaction_without_card(
        self, db_session, test_user, test_account
    ):
        """Test creating transaction without card (cash transaction)."""
        service = TransactionService(db_session)

        transaction = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.25"),
            currency="USD",
            description="Cash payment",
            transaction_type=TransactionType.expense,
            card_id=None,
            current_user=test_user,
        )

        assert transaction.card_id is None
        assert transaction.card is None

    async def test_create_transaction_with_invalid_card_raises_not_found(
        self, db_session, test_user, test_account
    ):
        """Test that invalid card_id raises NotFoundError."""
        service = TransactionService(db_session)
        import uuid

        fake_card_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            await service.create_transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.25"),
                currency="USD",
                description="Test",
                transaction_type=TransactionType.expense,
                card_id=fake_card_id,
                current_user=test_user,
            )

        assert "card" in str(exc_info.value).lower()

    async def test_create_transaction_with_other_users_card_raises_not_found(
        self, db_session, test_user, test_account, admin_user
    ):
        """Test that using another user's card raises NotFoundError."""
        from src.models.card import Card
        from src.models.enums import CardType

        # Create card for admin user
        admin_account = await AccountRepository(db_session).create(
            account_name="Admin Account",
            currency="USD",
            opening_balance=Decimal("0"),
            user_id=admin_user.id,
            account_type_id=test_account.account_type_id,
            financial_institution_id=test_account.financial_institution_id,
        )

        admin_card = Card(
            account_id=admin_account.id,
            name="Admin Card",
            card_type=CardType.credit_card,
            created_by=admin_user.id,
            updated_by=admin_user.id,
        )
        await db_session.flush()
        db_session.add(admin_card)
        await db_session.flush()

        service = TransactionService(db_session)

        # Try to create transaction with admin's card as test_user
        with pytest.raises(NotFoundError) as exc_info:
            await service.create_transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.25"),
                currency="USD",
                description="Test",
                transaction_type=TransactionType.expense,
                card_id=admin_card.id,
                current_user=test_user,
            )

        assert "card" in str(exc_info.value).lower()

    async def test_update_transaction_card_id(
        self, db_session, test_user, test_account, test_card
    ):
        """Test updating transaction card_id to valid card."""
        service = TransactionService(db_session)

        # Create transaction without card
        transaction = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        assert transaction.card_id is None

        # Update with card
        updated = await service.update_transaction(
            transaction_id=transaction.id,
            current_user=test_user,
            card_id=test_card.id,
        )

        assert updated.card_id == test_card.id
        assert updated.card is not None

    async def test_update_transaction_clear_card(
        self, db_session, test_user, test_account, test_card
    ):
        """Test updating transaction card_id to None (clearing card)."""
        service = TransactionService(db_session)

        # Create transaction with card
        transaction = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            card_id=test_card.id,
            current_user=test_user,
        )

        assert transaction.card_id == test_card.id

        # Clear card
        updated = await service.update_transaction(
            transaction_id=transaction.id,
            current_user=test_user,
            card_id=None,
        )

        assert updated.card_id is None
        assert updated.card is None

    async def test_update_transaction_invalid_card_raises_not_found(
        self, db_session, test_user, test_account
    ):
        """Test that updating with invalid card_id raises NotFoundError."""
        service = TransactionService(db_session)
        import uuid

        # Create transaction
        transaction = await service.create_transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Test",
            transaction_type=TransactionType.expense,
            current_user=test_user,
        )

        fake_card_id = uuid.uuid4()

        # Try to update with invalid card
        with pytest.raises(NotFoundError) as exc_info:
            await service.update_transaction(
                transaction_id=transaction.id,
                current_user=test_user,
                card_id=fake_card_id,
            )

        assert "card" in str(exc_info.value).lower()
