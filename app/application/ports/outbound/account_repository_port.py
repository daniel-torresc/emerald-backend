"""Account repository port interface."""

from typing import Optional, Protocol
from uuid import UUID

from app.domain.entities.account import Account


class AccountRepositoryPort(Protocol):
    """Repository interface for Account entity."""

    async def add(self, account: Account) -> Account:
        """
        Add a new account to the repository.

        Args:
            account: Account entity to add

        Returns:
            Created account entity with updated metadata

        Raises:
            AlreadyExistsError: If account with same name exists for user
        """
        ...

    async def get_by_id(self, account_id: UUID) -> Optional[Account]:
        """
        Retrieve account by ID.

        Args:
            account_id: Account's unique identifier

        Returns:
            Account entity if found, None otherwise
        """
        ...

    async def find_by_user_and_name(
        self, user_id: UUID, name: str
    ) -> Optional[Account]:
        """
        Find account by user ID and account name.

        Args:
            user_id: Owner's user ID
            name: Account name

        Returns:
            Account entity if found, None otherwise
        """
        ...

    async def list_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[Account]:
        """
        List accounts owned by a specific user.

        Args:
            user_id: Owner's user ID
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive accounts

        Returns:
            List of account entities
        """
        ...

    async def list_shared_with_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Account]:
        """
        List accounts shared with a specific user.

        Args:
            user_id: User ID to check shares for
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of account entities shared with the user
        """
        ...

    async def update(self, account: Account) -> Account:
        """
        Update existing account.

        Args:
            account: Account entity with updated data

        Returns:
            Updated account entity

        Raises:
            NotFoundError: If account doesn't exist
        """
        ...

    async def delete(self, account_id: UUID) -> None:
        """
        Hard delete account.

        Args:
            account_id: Account's unique identifier

        Raises:
            NotFoundError: If account doesn't exist
        """
        ...

    async def soft_delete(self, account_id: UUID) -> None:
        """
        Soft delete account (set deleted_at timestamp).

        Args:
            account_id: Account's unique identifier

        Raises:
            NotFoundError: If account doesn't exist
        """
        ...

    async def exists_by_id(self, account_id: UUID) -> bool:
        """
        Check if account exists by ID.

        Args:
            account_id: Account ID to check

        Returns:
            True if account exists, False otherwise
        """
        ...
