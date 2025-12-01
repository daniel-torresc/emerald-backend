"""
Account repository for database operations.

This module provides database operations for Account model, including:
- Standard CRUD operations (inherited from BaseRepository)
- Custom queries: get by user, get by name, check name existence
- Pagination and filtering support
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        financial_institution_id: uuid.UUID | None = None,
    ) -> list[Account]:
        """
        Get all accounts for a specific user.

        Includes eager loading of financial_institution relationship to prevent N+1 queries.

        Args:
            user_id: ID of the user who owns the accounts
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (max 100)
            is_active: Filter by active status (None = all)
            account_type: Filter by account type (None = all types)
            financial_institution_id: Filter by financial institution (None = all)

        Returns:
            List of Account instances with eager-loaded institution

        Example:
            # Get all active savings accounts for user at specific institution
            accounts = await account_repo.get_by_user(
                user_id=user.id,
                is_active=True,
                account_type=AccountType.SAVINGS,
                financial_institution_id=chase_id
            )
        """
        query = (
            select(Account)
            .where(Account.user_id == user_id)
            .options(
                selectinload(Account.financial_institution)
            )  # Eager load institution
        )
        query = self._apply_soft_delete_filter(query)

        # Apply filters
        if is_active is not None:
            query = query.where(Account.is_active == is_active)

        if account_type is not None:
            query = query.where(Account.account_type == account_type)

        if financial_institution_id is not None:
            query = query.where(
                Account.financial_institution_id == financial_institution_id
            )

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Order by created_at descending (newest first)
        query = query.order_by(Account.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_shared_with_user(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
        account_type: AccountType | None = None,
        financial_institution_id: uuid.UUID | None = None,
    ) -> list[Account]:
        """
        Get all accounts shared with a specific user.

        Returns accounts where the user has been granted access via AccountShare.
        Includes eager loading of financial_institution relationship.

        Args:
            user_id: ID of the user who has been granted access
            is_active: Filter by active status (None = all)
            account_type: Filter by account type (None = all types)
            financial_institution_id: Filter by institution (None = all)

        Returns:
            List of Account instances shared with the user

        Example:
            # Get all active accounts shared with user at specific institution
            shared_accounts = await account_repo.get_shared_with_user(
                user_id=user.id,
                is_active=True,
                financial_institution_id=chase_id
            )
        """
        from src.models.account import AccountShare

        # Join Account with AccountShare to find accounts shared with this user
        query = (
            select(Account)
            .join(AccountShare, Account.id == AccountShare.account_id)
            .where(AccountShare.user_id == user_id)
            .options(
                selectinload(Account.financial_institution)
            )  # Eager load institution
        )
        query = self._apply_soft_delete_filter(query)

        # Apply filters
        if is_active is not None:
            query = query.where(Account.is_active == is_active)

        if account_type is not None:
            query = query.where(Account.account_type == account_type)

        if financial_institution_id is not None:
            query = query.where(
                Account.financial_institution_id == financial_institution_id
            )

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
        query = (
            select(func.count()).select_from(Account).where(Account.user_id == user_id)
        )
        query = self._apply_soft_delete_filter(query)

        if is_active is not None:
            query = query.where(Account.is_active == is_active)

        result = await self.session.execute(query)
        return result.scalar_one()

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

    async def validate_institution_active(
        self,
        institution_id: uuid.UUID,
    ) -> bool:
        """
        Check if financial institution exists and is active.

        Used for validating institution before creating/updating accounts.
        This is a business validation query - called by service layer.

        Args:
            institution_id: Institution ID to validate

        Returns:
            True if institution exists and is_active=True, False otherwise

        Example:
            # Before creating account
            is_valid = await account_repo.validate_institution_active(institution_id)
            if not is_valid:
                raise ValidationError("Institution not found or is not active")
        """
        from src.models.financial_institution import FinancialInstitution

        query = select(FinancialInstitution.is_active).where(
            FinancialInstitution.id == institution_id
        )

        result = await self.session.execute(query)
        is_active = result.scalar_one_or_none()

        # Returns None if not found, False if found but inactive, True if active
        return is_active is True
