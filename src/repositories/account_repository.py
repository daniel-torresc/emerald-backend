"""
Account repository for database operations.

This module provides database operations for Account model, including:
- Standard CRUD operations (inherited from BaseRepository)
- Custom queries: get by user, get by name, check name existence
- Pagination and filtering support
"""

import uuid

from sqlalchemy import UnaryExpression, and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Account, AccountShare
from schemas import AccountFilterParams, AccountSortParams, PaginationParams, SortOrder
from .base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """
    Repository for Account model database operations.

    Provides account-specific queries in addition to base CRUD operations.
    Automatically filters soft-deleted accounts in all queries.

    Usage:
        account_repo = AccountRepository(session)
        accounts = await account_repo.get_by_user(user_id)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Account repository.

        Args:
            session: Async database session
        """
        super().__init__(Account, session)

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    async def get_by_user(self, user_id: uuid.UUID) -> list[Account]:
        """
        Get all accounts for a specific user.

        Includes eager loading of financial_institution and account_type relationships
        to prevent N+1 queries. Automatically excludes soft-deleted accounts via BaseRepository.

        Args:
            user_id: ID of the user who owns the accounts

        Returns:
            List of Account instances with eager-loaded institution and account type

        Example:
            # Get all checking accounts for user at specific institution
            accounts = await account_repo.get_by_user(user_id=user.id)
        """
        filters = [
            Account.user_id == user_id,
        ]

        load_relationships = [
            selectinload(Account.financial_institution),
            selectinload(Account.account_type),
        ]

        order_by = [
            desc(Account.created_at),
            desc(Account.id),
        ]

        return await self._list(
            filters=filters,
            load_relationships=load_relationships,
            order_by=order_by,
        )

    async def get_shared_with_user(self, user_id: uuid.UUID) -> list[Account]:
        """
        Get all accounts shared with a specific user.

        Returns accounts where the user has been granted access via AccountShare.
        Includes eager loading of financial_institution and account_type relationships.
        Automatically excludes soft-deleted accounts via BaseRepository.

        Args:
            user_id: ID of the user who has been granted access

        Returns:
            List of Account instances shared with the user

        Example:
            # Get all checking accounts shared with user at specific institution
            shared_accounts = await account_repo.get_shared_with_user(
                user_id=user.id,
                account_type_id=checking_type_id,
                financial_institution_id=chase_id
            )
        """
        filters = [
            AccountShare.user_id == user_id,
        ]

        load_relationships = [
            selectinload(Account.financial_institution),
            selectinload(Account.account_type),
        ]

        order_by = [
            desc(Account.created_at),
            desc(Account.id),
        ]

        # Join Account with AccountShare to find accounts shared with this user
        query = select(Account).join(
            AccountShare, Account.id == AccountShare.account_id
        )
        query = self._apply_soft_delete_filter(query)

        query = query.options(*load_relationships)
        query = query.where(and_(*filters))
        query = query.order_by(*order_by)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(
        self, user_id: uuid.UUID, account_name: str
    ) -> Account | None:
        """
        Get account by name for a specific user.

        Account names are unique per user (case-insensitive).

        Args:
            user_id: ID of the user who owns the account
            account_name: Name of the account

        Returns:
            Account instance or None if not found

        Example:
            account = await account_repo.get_by_name(
                user_id=user.id,
                account_name="Chase Savings"
            )
        """
        filters = [
            AccountShare.user_id == user_id,
            func.lower(Account.account_name) == account_name.lower(),
        ]

        results = await self._list(
            filters=filters,
        )

        return results[0] if results else None

    async def exists_by_name(self, user_id: uuid.UUID, account_name: str) -> bool:
        """
        Check if an account with the given name exists for a user.

        Useful for validating uniqueness before creating/updating accounts.
        Case-insensitive comparison.

        Args:
            user_id: ID of the user
            account_name: Name to check

        Returns:
            True if account name exists, False otherwise

        Example:
            # Before creating account
            if await account_repo.exists_by_name(user.id, "Savings"):
                raise AlreadyExistsError("Account name already exists")

            # Before updating account
            if await account_repo.exists_by_name(
                user.id, "New Name", exclude_id=account.id
            ):
                raise AlreadyExistsError("Account name already exists")
        """
        record = await self.get_by_name(user_id=user_id, account_name=account_name)
        return record is not None

    async def get_for_update(self, account_id: uuid.UUID) -> Account | None:
        """
        Get account with row-level lock (SELECT ... FOR UPDATE).

        Used for atomic balance updates to prevent race conditions.
        The row lock is held until the transaction commits or rolls back.

        IMPORTANT: This should only be called within an explicit database transaction:
            async with session.begin():
                account = await account_repo.get_for_update(account_id)
                account.current_balance += amount
                await session.commit()

        Args:
            account_id: ID of the account

        Returns:
            Account instance with row lock or None if not found

        Raises:
            DatabaseError: If called outside a transaction

        Example:
            # Correct usage - within explicit transaction
            async with session.begin():
                account = await account_repo.get_for_update(account_id)
                if account is None:
                    raise NotFoundError("Account not found")

                # Update balance (row is locked, no race conditions)
                account.current_balance += transaction_amount
                await session.commit()

            # WRONG - will cause issues
            account = await account_repo.get_for_update(account_id)
            account.current_balance += amount  # Lock released, race condition possible!
        """
        query = select(Account).where(Account.id == account_id).with_for_update()
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # ========================================================================
    # USER PARAMS METHODS
    # ========================================================================

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        filter_params: AccountFilterParams,
        sort_params: AccountSortParams,
        pagination_params: PaginationParams,
    ) -> tuple[list[Account], int]:
        filters = [
            Account.user_id == user_id,
        ]

        # Account type filter
        if filter_params.account_type_id is not None:
            filters.append(Account.account_type_id == filter_params.account_type_id)

        # Financial institution filter
        if filter_params.financial_institution_id is not None:
            filters.append(
                Account.financial_institution_id
                == filter_params.financial_institution_id
            )

        order_by: list[UnaryExpression] = []

        # Get the model column from enum value
        sort_column = getattr(Account, sort_params.sort_by.value)

        # Apply sort direction
        if sort_params.sort_order == SortOrder.ASC:
            order_by.append(asc(sort_column))
        else:
            order_by.append(desc(sort_column))

        # Add secondary sort by id for deterministic pagination
        order_by.append(desc(Account.id))

        load_relationships = [
            selectinload(Account.financial_institution),
            selectinload(Account.account_type),
        ]

        return await self._list_and_count(
            filters=filters,
            order_by=order_by,
            load_relationships=load_relationships,
            offset=pagination_params.offset,
            limit=pagination_params.page_size,
        )
