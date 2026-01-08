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

from sqlalchemy import ColumnElement, UnaryExpression, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from models import Account, Card, Transaction
from schemas import (
    PaginationParams,
    SortOrder,
    TransactionFilterParams,
    TransactionSortParams,
)
from .base import BaseRepository


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

    @staticmethod
    def _build_filters(
        user_id: uuid.UUID,
        params: TransactionFilterParams,
    ) -> list[ColumnElement[bool]]:
        """
        Convert TransactionFilterParams to SQLAlchemy filter expressions.

        Args:
            params: Filter parameters from request

        Returns:
            List of SQLAlchemy filter expressions
        """
        filters: list[ColumnElement[bool]] = [
            Transaction.account.has(Account.user_id == user_id),
        ]

        # Account ownership filter
        if params.account_id is not None:
            filters.append(Transaction.account_id == params.account_id)

        # Date range filters
        if params.date_from is not None:
            filters.append(Transaction.transaction_date >= params.date_from)

        if params.date_to is not None:
            filters.append(Transaction.transaction_date <= params.date_to)

        # Amount range filters
        if params.amount_min is not None:
            filters.append(Transaction.amount >= params.amount_min)

        if params.amount_max is not None:
            filters.append(Transaction.amount <= params.amount_max)

        # Fuzzy text search on description (pg_trgm similarity)
        if params.description:
            filters.append(
                func.similarity(Transaction.description, params.description) > 0.3
            )

        # Fuzzy text search on merchant (pg_trgm similarity)
        if params.merchant:
            filters.append(func.similarity(Transaction.merchant, params.merchant) > 0.3)

        # Transaction type filter
        if params.transaction_type is not None:
            filters.append(Transaction.transaction_type == params.transaction_type)

        # Card ID filter
        if params.card_id is not None:
            filters.append(Transaction.card_id == params.card_id)

        # Card type filter (uses relationship)
        if params.card_type is not None:
            filters.append(Transaction.card.has(Card.card_type == params.card_type))

        return filters

    @staticmethod
    def _build_order_by(
        params: TransactionSortParams,
    ) -> list[UnaryExpression]:
        """
        Convert TransactionSortParams to SQLAlchemy order_by expressions.

        Args:
            params: Sort parameters with sort_by and sort_order

        Returns:
            List of SQLAlchemy order_by expressions
        """
        order_by: list[UnaryExpression] = []

        # Get the model column from enum value
        sort_column = getattr(Transaction, params.sort_by.value)

        # Apply sort direction
        if params.sort_order == SortOrder.ASC:
            order_by.append(asc(sort_column))
        else:
            order_by.append(desc(sort_column))

        # Add secondary sort by id for deterministic pagination
        order_by.append(desc(Transaction.id))

        return order_by

    @staticmethod
    def _build_load_relationships() -> list[_AbstractLoad]:
        """
        Build eager loading options for transaction queries.

        Returns:
            List of SQLAlchemy load options
        """
        return [
            selectinload(Transaction.child_transactions),
            selectinload(Transaction.card),
        ]

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        filter_params: TransactionFilterParams,
        sort_params: TransactionSortParams,
        pagination_params: PaginationParams,
    ) -> tuple[list[Transaction], int]:
        filters = self._build_filters(user_id=user_id, params=filter_params)
        order_by = self._build_order_by(params=sort_params)
        load_relationships = self._build_load_relationships()

        return await self._list_and_count(
            filters=filters,
            order_by=order_by,
            load_relationships=load_relationships,
            offset=pagination_params.offset,
            limit=pagination_params.page_size,
        )

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
