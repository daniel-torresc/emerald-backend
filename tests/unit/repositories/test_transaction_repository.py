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

from src.models.enums import TransactionType
from src.models.transaction import Transaction
from src.repositories.transaction_repository import TransactionRepository


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
            transaction_type=TransactionType.debit,
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
        assert created.transaction_type == TransactionType.debit
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
            transaction_type=TransactionType.credit,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created = await repo.create(transaction)

        # Retrieve by ID
        retrieved = await repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.description == "Salary"

    async def test_get_by_account_id(self, db_session, test_user, test_account):
        """Test getting all transactions for an account."""
        repo = TransactionRepository(db_session)

        # Create multiple transactions
        for i in range(5):
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today() - timedelta(days=i),
                amount=Decimal(f"-{10 + i}.00"),
                currency="USD",
                description=f"Transaction {i}",
                transaction_type=TransactionType.debit,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Retrieve transactions
        transactions = await repo.get_by_account_id(test_account.id, skip=0, limit=10)

        assert len(transactions) == 5
        # Should be ordered by date descending
        assert transactions[0].description == "Transaction 0"

    async def test_count_by_account_id(self, db_session, test_user, test_account):
        """Test counting transactions for an account."""
        repo = TransactionRepository(db_session)

        # Create 3 transactions
        for i in range(3):
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal(f"-{10 + i}.00"),
                currency="USD",
                description=f"Transaction {i}",
                transaction_type=TransactionType.debit,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        count = await repo.count_by_account_id(test_account.id)
        assert count == 3

    async def test_search_by_date_range(self, db_session, test_user, test_account):
        """Test searching transactions by date range."""
        repo = TransactionRepository(db_session)

        # Create transactions on different dates
        today = date.today()
        for i in range(5):
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=today - timedelta(days=i),
                amount=Decimal("-10.00"),
                currency="USD",
                description=f"Transaction {i}",
                transaction_type=TransactionType.debit,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Search for transactions in last 3 days
        date_from = today - timedelta(days=2)
        transactions, total = await repo.search_transactions(
            account_id=test_account.id,
            date_from=date_from,
            date_to=today,
        )

        assert total == 3

    async def test_search_by_amount_range(self, db_session, test_user, test_account):
        """Test searching transactions by amount range."""
        repo = TransactionRepository(db_session)

        # Create transactions with different amounts
        amounts = [
            Decimal("-10.00"),
            Decimal("-25.00"),
            Decimal("-50.00"),
            Decimal("-100.00"),
        ]
        for amount in amounts:
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=amount,
                currency="USD",
                description="Transaction",
                transaction_type=TransactionType.debit,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Search for amounts between -60 and -20
        transactions, total = await repo.search_transactions(
            account_id=test_account.id,
            amount_min=Decimal("-60.00"),
            amount_max=Decimal("-20.00"),
        )

        assert total == 2  # -25.00 and -50.00

    async def test_search_by_type(self, db_session, test_user, test_account):
        """Test searching transactions by type."""
        repo = TransactionRepository(db_session)

        # Create transactions of different types
        types = [TransactionType.debit, TransactionType.credit, TransactionType.debit]
        for txn_type in types:
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("-10.00")
                if txn_type == TransactionType.debit
                else Decimal("10.00"),
                currency="USD",
                description="Transaction",
                transaction_type=txn_type,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Search for debit transactions
        transactions, total = await repo.search_transactions(
            account_id=test_account.id,
            transaction_type=TransactionType.debit,
        )

        assert total == 2

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
            transaction_type=TransactionType.debit,
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
                transaction_type=TransactionType.debit,
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
            transaction_type=TransactionType.debit,
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
            transaction_type=TransactionType.debit,
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
                transaction_type=TransactionType.debit
                if amount < 0
                else TransactionType.credit,
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
                transaction_type=TransactionType.credit
                if amount > 0
                else TransactionType.debit,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Get balance as of 2 days ago
        balance = await repo.get_balance_at_date(
            test_account.id, today - timedelta(days=2)
        )

        assert balance == Decimal("80.00")  # 100 - 20

    async def test_soft_delete_filtering(self, db_session, test_user, test_account):
        """Test that soft-deleted transactions are filtered out."""
        repo = TransactionRepository(db_session)

        # Create transaction
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-10.00"),
            currency="USD",
            description="To be deleted",
            transaction_type=TransactionType.debit,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created = await repo.create(transaction)

        # Soft delete
        await repo.soft_delete(created.id)

        # Should not be found
        retrieved = await repo.get_by_id(created.id)
        assert retrieved is None

        # Should not be counted
        count = await repo.count_by_account_id(test_account.id)
        assert count == 0

    async def test_pagination(self, db_session, test_user, test_account):
        """Test pagination of transaction list."""
        repo = TransactionRepository(db_session)

        # Create 10 transactions
        for i in range(10):
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal(f"-{i + 1}.00"),
                currency="USD",
                description=f"Transaction {i}",
                transaction_type=TransactionType.debit,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            await repo.create(transaction)

        # Get first page (5 items)
        page1 = await repo.get_by_account_id(test_account.id, skip=0, limit=5)
        assert len(page1) == 5

        # Get second page (5 items)
        page2 = await repo.get_by_account_id(test_account.id, skip=5, limit=5)
        assert len(page2) == 5

        # Pages should not overlap
        page1_ids = {t.id for t in page1}
        page2_ids = {t.id for t in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
