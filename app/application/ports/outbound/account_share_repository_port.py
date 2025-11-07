"""Account share repository port interface."""

from typing import Optional, Protocol
from uuid import UUID

from app.domain.entities.account_share import AccountShare


class AccountShareRepositoryPort(Protocol):
    """Repository interface for AccountShare entity."""

    async def add(self, account_share: AccountShare) -> AccountShare:
        """
        Add a new account share to the repository.

        Args:
            account_share: AccountShare entity to add

        Returns:
            Created account share entity with updated metadata

        Raises:
            AlreadyExistsError: If share already exists for account and user
        """
        ...

    async def get_by_id(self, share_id: UUID) -> Optional[AccountShare]:
        """
        Retrieve account share by ID.

        Args:
            share_id: AccountShare's unique identifier

        Returns:
            AccountShare entity if found, None otherwise
        """
        ...

    async def find_by_account_and_user(
        self, account_id: UUID, shared_with_user_id: UUID
    ) -> Optional[AccountShare]:
        """
        Find account share by account and shared user.

        Args:
            account_id: Account's unique identifier
            shared_with_user_id: User ID the account is shared with

        Returns:
            AccountShare entity if found, None otherwise
        """
        ...

    async def list_by_account(
        self, account_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AccountShare]:
        """
        List all shares for a specific account.

        Args:
            account_id: Account's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of account share entities
        """
        ...

    async def list_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AccountShare]:
        """
        List all shares for a specific user (accounts shared with them).

        Args:
            user_id: User's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of account share entities
        """
        ...

    async def update(self, account_share: AccountShare) -> AccountShare:
        """
        Update existing account share.

        Args:
            account_share: AccountShare entity with updated data

        Returns:
            Updated account share entity

        Raises:
            NotFoundError: If account share doesn't exist
        """
        ...

    async def delete(self, share_id: UUID) -> None:
        """
        Delete account share.

        Args:
            share_id: AccountShare's unique identifier

        Raises:
            NotFoundError: If account share doesn't exist
        """
        ...

    async def delete_by_account_and_user(
        self, account_id: UUID, shared_with_user_id: UUID
    ) -> None:
        """
        Delete account share by account and user.

        Args:
            account_id: Account's unique identifier
            shared_with_user_id: User ID the account is shared with

        Raises:
            NotFoundError: If account share doesn't exist
        """
        ...
