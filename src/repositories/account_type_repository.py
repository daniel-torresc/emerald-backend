"""
Account type repository for database operations.

This module provides database operations for the AccountType model,
including lookups by key and ordered retrieval.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.account_type import AccountType
from repositories.base import BaseRepository


class AccountTypeRepository(BaseRepository[AccountType]):
    """
    Repository for AccountType model operations.

    Extends BaseRepository with account-type-specific queries:
    - Key lookups (for uniqueness validation)
    - Ordered retrieval by sort_order (for UI display)

    Note:
        AccountType uses hard delete (permanent removal from database).
        No soft delete filtering is applied.
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

    async def get_all_ordered(self) -> list[AccountType]:
        """
        Get all account types ordered by sort_order, then by name.

        Ordered by sort_order (ascending), then by name (alphabetically).
        Useful for dropdown menus and selection lists in UI.

        Returns:
            List of all AccountType instances

        Example:
            types = await repo.get_all_ordered()
            # Returns: [Checking, Savings, Investment, ...]
        """
        query = select(AccountType).order_by(AccountType.sort_order, AccountType.name)

        result = await self.session.execute(query)
        return list(result.scalars().all())
