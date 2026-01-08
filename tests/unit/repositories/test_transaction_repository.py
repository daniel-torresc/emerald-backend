"""
Unit tests for TransactionRepository.

Tests:
- Transaction creation
- Get transaction by ID
- List transactions by account
- Search transactions with filters
- Fuzzy text search
- Transaction splitting queries
- Balance calculations
- Soft delete filtering
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from models import Transaction, TransactionType
from repositories import TransactionRepository


@pytest.mark.asyncio
class TestTransactionRepository:
    """Test suite for TransactionRepository."""

    async def test_create_transaction(self, db_session, test_user, test_account):
        """Test creating a transaction."""
        repo = TransactionRepository(db_session)

        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.25"),
            currency="USD",
            description="Grocery shopping",
            merchant="Whole Foods",
            transaction_type=TransactionType.expense,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        created = await repo.create(transaction)

        assert created.id is not None
        assert created.account_id == test_account.id
        assert created.amount == Decimal("-50.25")
        assert created.currency == "USD"
        assert created.description == "Grocery shopping"
        assert created.merchant == "Whole Foods"
        assert created.transaction_type == TransactionType.expense
        assert created.deleted_at is None

    async def test_get_by_id(self, db_session, test_user, test_account):
        """Test getting transaction by ID."""
        repo = TransactionRepository(db_session)

        # Create transaction
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("100.00"),
            currency="USD",
            description="Salary",
            transaction_type=TransactionType.income,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created = await repo.create(transaction)

        # Retrieve by ID
        retrieved = await repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.description == "Salary"

    async def test_get_children(self, db_session, test_user, test_account):
        """Test getting child transactions of a split parent."""
        repo = TransactionRepository(db_session)

        # Create parent transaction
        parent = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        parent = await repo.create(parent)

        # Create child transactions
        for i in range(2):
            child = Transaction(
                account_id=test_account.id,
                parent_transaction_id=parent.id,
                transaction_date=date.today(),
                amount=Decimal(f"-{25}.00"),
                currency="USD",
                description=f"Child {i}",
                transaction_type=TransactionType.expense,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(child)

        # Get children
        children = await repo.get_children(parent.id)

        assert len(children) == 2

    async def test_has_children(self, db_session, test_user, test_account):
        """Test checking if transaction has children."""
        repo = TransactionRepository(db_session)

        # Create parent
        parent = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Parent",
            transaction_type=TransactionType.expense,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        parent = await repo.create(parent)

        # No children yet
        assert await repo.has_children(parent.id) is False

        # Create child
        child = Transaction(
            account_id=test_account.id,
            parent_transaction_id=parent.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Child",
            transaction_type=TransactionType.expense,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        await repo.create(child)

        # Now has children
        assert await repo.has_children(parent.id) is True

    async def test_calculate_account_balance(self, db_session, test_user, test_account):
        """Test calculating account balance from transactions."""
        repo = TransactionRepository(db_session)

        # Create transactions
        amounts = [Decimal("-50.00"), Decimal("100.00"), Decimal("-25.00")]
        for amount in amounts:
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=amount,
                currency="USD",
                description="Transaction",
                transaction_type=TransactionType.expense
                if amount < 0
                else TransactionType.income,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Calculate balance
        balance = await repo.calculate_account_balance(test_account.id)

        assert balance == Decimal("25.00")  # -50 + 100 - 25

    async def test_get_balance_at_date(self, db_session, test_user, test_account):
        """Test getting balance at a specific date."""
        repo = TransactionRepository(db_session)

        # Create transactions on different dates
        today = date.today()
        transactions_data = [
            (today - timedelta(days=3), Decimal("100.00")),
            (today - timedelta(days=2), Decimal("-20.00")),
            (today - timedelta(days=1), Decimal("-30.00")),
            (today, Decimal("50.00")),
        ]

        for txn_date, amount in transactions_data:
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=txn_date,
                amount=amount,
                currency="USD",
                description="Transaction",
                transaction_type=TransactionType.income
                if amount > 0
                else TransactionType.expense,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Get balance as of 2 days ago
        balance = await repo.get_balance_at_date(
            test_account.id, today - timedelta(days=2)
        )

        assert balance == Decimal("80.00")  # 100 - 20
