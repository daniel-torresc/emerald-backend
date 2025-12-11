"""
Transaction repository for database operations.

This module provides database operations for Transaction model, including:
- Standard CRUD operations (inherited from BaseRepository)
- Advanced search with fuzzy matching (pg_trgm)
- Transaction splitting operations
- Balance calculation queries
- Pagination and filtering support
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.card import Card
from src.models.enums import CardType, TransactionType
from src.models.transaction import Transaction
from src.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """
    Repository for Transaction model database operations.

    Provides transaction-specific queries in addition to base CRUD operations.
    Automatically filters soft-deleted transactions in all queries.

    Features:
    - CRUD operations (create, read, update, soft delete)
    - Advanced search with multiple filters
    - Fuzzy text search on merchant and description (pg_trgm)
    - Transaction splitting queries (parent-child relationships)
    - Balance calculation queries

    Usage:
        transaction_repo = TransactionRepository(session)
        transactions = await transaction_repo.get_by_account_id(account_id)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Transaction repository.

        Args:
            session: Async database session
        """
        super().__init__(Transaction, session)

    async def create(self, transaction: Transaction) -> Transaction:
        """
        Create a new transaction.

        Args:
            transaction: Transaction instance to create

        Returns:
            Created transaction with all relationships loaded

        Example:
            transaction = Transaction(
                account_id=account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.25"),
                currency="USD",
                description="Grocery Shopping",
                transaction_type=TransactionType.DEBIT,
                created_by=user.id,
                updated_by=user.id,
            )
            created = await repo.create(transaction)
        """
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(
            transaction,
            ["account", "parent_transaction", "child_transactions", "card"],
        )
        return transaction

    async def get_by_id(self, transaction_id: uuid.UUID) -> Transaction | None:
        """
        Get transaction by ID with all relationships loaded.

        Automatically filters out soft-deleted transactions.

        Args:
            transaction_id: UUID of the transaction

        Returns:
            Transaction instance or None if not found/deleted

        Example:
            transaction = await repo.get_by_id(transaction_id)
            if transaction is None:
                raise NotFoundError("Transaction not found")
        """
        query = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(
                selectinload(Transaction.account),
                selectinload(Transaction.parent_transaction),
                selectinload(Transaction.child_transactions),
                selectinload(Transaction.card),
            )
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(self, transaction: Transaction) -> Transaction:
        """
        Update an existing transaction.

        Args:
            transaction: Transaction instance with updated fields

        Returns:
            Updated transaction instance

        Example:
            transaction.amount = Decimal("-60.00")
            transaction.description = "Updated description"
            updated = await repo.update(transaction)
        """
        await self.session.flush()
        await self.session.refresh(
            transaction,
            ["account", "parent_transaction", "child_transactions", "card"],
        )
        return transaction

    async def soft_delete(self, transaction_id: uuid.UUID) -> bool:
        """
        Soft delete a transaction (set deleted_at timestamp).

        Args:
            transaction_id: UUID of the transaction to delete

        Returns:
            True if deleted, False if not found

        Example:
            deleted = await repo.soft_delete(transaction_id)
            if not deleted:
                raise NotFoundError("Transaction not found")
        """
        transaction = await self.get_by_id(transaction_id)
        if transaction is None:
            return False

        from datetime import UTC, datetime

        transaction.deleted_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def get_by_account_id(
        self,
        account_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Transaction]:
        """
        Get all transactions for an account with pagination.

        Args:
            account_id: UUID of the account
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of Transaction instances ordered by date descending

        Example:
            transactions = await repo.get_by_account_id(
                account_id=account.id,
                skip=0,
                limit=20,
            )
        """
        query = (
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .options(
                selectinload(Transaction.child_transactions),
                selectinload(Transaction.card),
            )
            .order_by(
                Transaction.transaction_date.desc(), Transaction.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_account_id(self, account_id: uuid.UUID) -> int:
        """
        Count total transactions for an account.

        Args:
            account_id: UUID of the account

        Returns:
            Total count of non-deleted transactions

        Example:
            total = await repo.count_by_account_id(account.id)
        """
        query = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.account_id == account_id)
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def search_transactions(
        self,
        account_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        description: str | None = None,
        merchant: str | None = None,
        transaction_type: TransactionType | None = None,
        card_id: uuid.UUID | None = None,
        card_type: CardType | None = None,
        sort_by: str = "transaction_date",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Transaction], int]:
        """
        Advanced search with multiple filters and fuzzy text matching.

        Uses PostgreSQL pg_trgm extension for fuzzy matching on merchant and description.
        Similarity threshold: 0.3 (finds matches with ~70% similarity).

        Args:
            account_id: Account to search in
            date_from: Filter transactions from this date (inclusive)
            date_to: Filter transactions to this date (inclusive)
            amount_min: Minimum transaction amount (inclusive)
            amount_max: Maximum transaction amount (inclusive)
            description: Fuzzy search on description (handles typos)
            merchant: Fuzzy search on merchant (handles typos)
            transaction_type: Filter by transaction type
            card_id: Filter by specific card UUID
            card_type: Filter by card type (credit_card or debit_card)
            sort_by: Field to sort by (transaction_date, amount, description, created_at)
            sort_order: Sort order (asc or desc)
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (max 100)

        Returns:
            Tuple of (transactions, total_count)

        Example:
            # Search for groceries with fuzzy matching
            transactions, total = await repo.search_transactions(
                account_id=account.id,
                description="groceris",  # Typo will still match "groceries"
                amount_min=Decimal("10.00"),
                amount_max=Decimal("100.00"),
                sort_by="transaction_date",
                sort_order="desc",
                skip=0,
                limit=20,
            )
        """
        # Build base query
        query = (
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .options(
                selectinload(Transaction.child_transactions),
                selectinload(Transaction.card),
            )
        )
        query = self._apply_soft_delete_filter(query)

        # Build filters
        filters = []

        # Date range filter
        if date_from:
            filters.append(Transaction.transaction_date >= date_from)
        if date_to:
            filters.append(Transaction.transaction_date <= date_to)

        # Amount range filter
        if amount_min is not None:
            filters.append(Transaction.amount >= amount_min)
        if amount_max is not None:
            filters.append(Transaction.amount <= amount_max)

        # Transaction type filter
        if transaction_type:
            filters.append(Transaction.transaction_type == transaction_type)

        # Card ID filter
        if card_id is not None:
            filters.append(Transaction.card_id == card_id)

        # Card type filter (requires join with Card table)
        if card_type is not None:
            query = query.join(Card, Transaction.card_id == Card.id).where(
                Card.card_type == card_type
            )

        # Fuzzy text search on description (pg_trgm similarity)
        if description:
            # Use trigram similarity with threshold 0.3 (~70% match)
            filters.append(func.similarity(Transaction.description, description) > 0.3)

        # Fuzzy text search on merchant (pg_trgm similarity)
        if merchant:
            filters.append(func.similarity(Transaction.merchant, merchant) > 0.3)

        # Apply all filters
        if filters:
            query = query.where(and_(*filters))

        # Count total results (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar_one()

        # Apply sorting
        if sort_by == "transaction_date":
            order_col = Transaction.transaction_date
        elif sort_by == "amount":
            order_col = Transaction.amount
        elif sort_by == "description":
            order_col = Transaction.description
        elif sort_by == "created_at":
            order_col = Transaction.created_at
        else:
            # Default to transaction_date
            order_col = Transaction.transaction_date

        if sort_order == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        # Add secondary sort by created_at for consistent ordering
        query = query.order_by(Transaction.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(min(limit, 100))  # Cap at 100

        # Execute query
        result = await self.session.execute(query)
        transactions = list(result.scalars().all())

        return transactions, total_count

    async def get_children(self, parent_id: uuid.UUID) -> list[Transaction]:
        """
        Get all child transactions for a parent transaction.

        Args:
            parent_id: UUID of the parent transaction

        Returns:
            List of child Transaction instances

        Example:
            children = await repo.get_children(parent_transaction.id)
            for child in children:
                print(f"Child: {child.amount} - {child.description}")
        """
        query = (
            select(Transaction)
            .where(Transaction.parent_transaction_id == parent_id)
            .order_by(Transaction.amount.desc())
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_parent(self, transaction_id: uuid.UUID) -> Transaction | None:
        """
        Get the parent transaction for a child transaction.

        Args:
            transaction_id: UUID of the child transaction

        Returns:
            Parent Transaction instance or None if not a child

        Example:
            parent = await repo.get_parent(child_transaction.id)
            if parent:
                print(f"Parent: {parent.amount} - {parent.description}")
        """
        # First get the child to find parent_transaction_id
        child = await self.get_by_id(transaction_id)
        if child is None or child.parent_transaction_id is None:
            return None

        return await self.get_by_id(child.parent_transaction_id)

    async def has_children(self, transaction_id: uuid.UUID) -> bool:
        """
        Check if a transaction has child splits.

        Args:
            transaction_id: UUID of the transaction

        Returns:
            True if transaction has children, False otherwise

        Example:
            if await repo.has_children(transaction.id):
                print("This is a split parent transaction")
        """
        query = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.parent_transaction_id == transaction_id)
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        count = result.scalar_one()
        return count > 0

    async def calculate_account_balance(self, account_id: uuid.UUID) -> Decimal:
        """
        Calculate account balance from all non-deleted transactions.

        Formula: SUM(amount) WHERE account_id = ? AND deleted_at IS NULL

        This is used to verify cached balance in accounts.current_balance.

        Args:
            account_id: UUID of the account

        Returns:
            Sum of all transaction amounts (Decimal)

        Example:
            calculated_balance = await repo.calculate_account_balance(account.id)
            cached_balance = account.current_balance
            if calculated_balance != cached_balance:
                # Balance mismatch - repair needed
                print("Balance mismatch detected!")
        """
        query = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .select_from(Transaction)
            .where(Transaction.account_id == account_id)
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        balance_sum = result.scalar_one()
        return Decimal(str(balance_sum))

    async def get_balance_at_date(
        self, account_id: uuid.UUID, as_of_date: date
    ) -> Decimal:
        """
        Calculate historical balance at a specific date.

        Formula: SUM(amount) WHERE account_id = ? AND date <= ? AND deleted_at IS NULL

        Useful for historical reports and balance verification.

        Args:
            account_id: UUID of the account
            as_of_date: Date to calculate balance as of

        Returns:
            Sum of transaction amounts up to date (Decimal)

        Example:
            # Get balance as of end of last month
            from datetime import date
            last_month_end = date(2025, 10, 31)
            balance = await repo.get_balance_at_date(account.id, last_month_end)
            print(f"Balance on {last_month_end}: {balance}")
        """
        query = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .select_from(Transaction)
            .where(
                Transaction.account_id == account_id,
                Transaction.transaction_date <= as_of_date,
            )
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        balance_sum = result.scalar_one()
        return Decimal(str(balance_sum))
