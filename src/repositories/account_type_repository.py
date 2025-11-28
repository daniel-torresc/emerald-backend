"""
Account type repository for database operations.

This module provides database operations for the AccountType model,
including lookups by key, filtering by active status, and ordered retrieval.
"""

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account_type import AccountType
from src.repositories.base import BaseRepository


class AccountTypeRepository(BaseRepository[AccountType]):
    """
    Repository for AccountType model operations.

    Extends BaseRepository with account-type-specific queries:
    - Key lookups (for uniqueness validation)
    - Active status filtering (for dropdown menus)
    - Ordered retrieval by sort_order (for UI display)

    Note:
        This repository does NOT use soft delete filtering because
        AccountType uses is_active flag instead (same as FinancialInstitution).
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AccountTypeRepository.

        Args:
            session: Async database session
        """
        super().__init__(AccountType, session)

    async def get_by_key(self, key: str) -> AccountType | None:
        """
        Get account type by its unique key.

        Keys are stored lowercase in the database.
        This method is case-sensitive - keys should be lowercase.

        Args:
            key: Unique key identifier (lowercase, alphanumeric, underscore)

        Returns:
            AccountType instance or None if not found

        Example:
            account_type = await repo.get_by_key("checking")
        """
        query = select(AccountType).where(AccountType.key == key.lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def exists_by_key(self, key: str) -> bool:
        """
        Check if an account type with the given key already exists.

        Used for uniqueness validation before creating new account types.
        Case-insensitive check (converts to lowercase).

        Args:
            key: Unique key to check

        Returns:
            True if exists, False otherwise

        Example:
            exists = await repo.exists_by_key("hsa")
            if exists:
                raise AlreadyExistsError("Account type with key 'hsa' already exists")
        """
        query = select(AccountType.id).where(AccountType.key == key.lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_all_active(self) -> list[AccountType]:
        """
        Get all active account types.

        Ordered by sort_order (ascending), then by name (alphabetically).
        Useful for dropdown menus and selection lists in UI.

        Returns:
            List of all active AccountType instances

        Example:
            active_types = await repo.get_all_active()
            # Returns: [Checking, Savings, Investment, ...]
        """
        query = (
            select(AccountType)
            .where(AccountType.is_active)
            .order_by(AccountType.sort_order, AccountType.name)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_ordered(self, is_active: bool | None = True) -> list[AccountType]:
        """
        Get all account types with optional active status filtering.

        Ordered by sort_order (ascending), then by name (alphabetically).
        Allows retrieving both active and inactive types based on parameter.

        Args:
            is_active: Filter by active status (default: True)
                - True: Only active types
                - False: Only inactive types
                - None: All types (active and inactive)

        Returns:
            List of AccountType instances matching filter

        Example:
            # Get all active types (default)
            active = await repo.get_all_ordered()

            # Get all inactive types
            inactive = await repo.get_all_ordered(is_active=False)

            # Get all types (active and inactive)
            all_types = await repo.get_all_ordered(is_active=None)
        """
        query = select(AccountType)

        # Apply active status filter (if specified)
        if is_active is not None:
            query = query.where(AccountType.is_active == is_active)

        # Order by sort_order, then name
        query = query.order_by(AccountType.sort_order, AccountType.name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    def _apply_soft_delete_filter(self, query: Select) -> Select:
        """
        Override base method - AccountType uses is_active, not soft delete.

        This method is intentionally a no-op because AccountType
        does not use the SoftDeleteMixin pattern. Instead, account types
        are deactivated using the is_active flag.

        Args:
            query: SQLAlchemy select statement

        Returns:
            Original query unchanged
        """
        return query
