"""
Account repository for database operations.

This module provides database operations for Account model, including:
- Standard CRUD operations (inherited from BaseRepository)
- Custom queries: get by user, get by name, check name existence
- Pagination and filtering support
"""

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account
from src.models.enums import AccountType
from src.repositories.base import BaseRepository


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

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        account_type: AccountType | None = None,
    ) -> list[Account]:
        """
        Get all accounts for a specific user.

        Args:
            user_id: ID of the user who owns the accounts
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (max 100)
            is_active: Filter by active status (None = all)
            account_type: Filter by account type (None = all types)

        Returns:
            List of Account instances

        Example:
            # Get all active savings accounts for user
            accounts = await account_repo.get_by_user(
                user_id=user.id,
                is_active=True,
                account_type=AccountType.SAVINGS
            )
        """
        query = select(Account).where(Account.user_id == user_id)
        query = self._apply_soft_delete_filter(query)

        # Apply filters
        if is_active is not None:
            query = query.where(Account.is_active == is_active)

        if account_type is not None:
            query = query.where(Account.account_type == account_type)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Order by created_at descending (newest first)
        query = query.order_by(Account.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(
        self,
        user_id: uuid.UUID,
        account_name: str,
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
        query = select(Account).where(
            Account.user_id == user_id,
            func.lower(Account.account_name) == account_name.lower(),
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def exists_by_name(
        self,
        user_id: uuid.UUID,
        account_name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """
        Check if an account with the given name exists for a user.

        Useful for validating uniqueness before creating/updating accounts.
        Case-insensitive comparison.

        Args:
            user_id: ID of the user
            account_name: Name to check
            exclude_id: Optional account ID to exclude (for updates)

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
        query = select(Account).where(
            Account.user_id == user_id,
            func.lower(Account.account_name) == account_name.lower(),
        )
        query = self._apply_soft_delete_filter(query)

        # Exclude the account being updated
        if exclude_id is not None:
            query = query.where(Account.id != exclude_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def count_user_accounts(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> int:
        """
        Count total accounts for a user.

        Args:
            user_id: ID of the user
            is_active: Filter by active status (None = all)

        Returns:
            Total count of accounts

        Example:
            total = await account_repo.count_user_accounts(user.id)
            active_count = await account_repo.count_user_accounts(
                user.id, is_active=True
            )
        """
        query = select(func.count()).select_from(Account).where(
            Account.user_id == user_id
        )
        query = self._apply_soft_delete_filter(query)

        if is_active is not None:
            query = query.where(Account.is_active == is_active)

        result = await self.session.execute(query)
        return result.scalar_one()
