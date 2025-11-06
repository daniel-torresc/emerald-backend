"""Refresh token repository port interface."""

from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from app.domain.entities.refresh_token import RefreshToken


class RefreshTokenRepositoryPort(Protocol):
    """Repository interface for RefreshToken entity."""

    async def add(self, refresh_token: RefreshToken) -> RefreshToken:
        """
        Add a new refresh token to the repository.

        Args:
            refresh_token: RefreshToken entity to add

        Returns:
            Created refresh token entity with updated metadata
        """
        ...

    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """
        Retrieve refresh token by token string.

        Args:
            token: Token string

        Returns:
            RefreshToken entity if found, None otherwise
        """
        ...

    async def get_by_id(self, token_id: UUID) -> Optional[RefreshToken]:
        """
        Retrieve refresh token by ID.

        Args:
            token_id: Token's unique identifier

        Returns:
            RefreshToken entity if found, None otherwise
        """
        ...

    async def list_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[RefreshToken]:
        """
        List all refresh tokens for a specific user.

        Args:
            user_id: User's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of refresh token entities
        """
        ...

    async def list_active_by_user(self, user_id: UUID) -> list[RefreshToken]:
        """
        List all active (non-revoked, non-expired) refresh tokens for a user.

        Args:
            user_id: User's unique identifier

        Returns:
            List of active refresh token entities
        """
        ...

    async def revoke_token(self, token: str) -> None:
        """
        Revoke a specific refresh token.

        Args:
            token: Token string to revoke

        Raises:
            NotFoundError: If token doesn't exist
        """
        ...

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """
        Revoke all refresh tokens for a specific user.

        Args:
            user_id: User's unique identifier
        """
        ...

    async def delete_expired(self, before_date: datetime) -> int:
        """
        Delete expired refresh tokens.

        Args:
            before_date: Delete tokens that expired before this date

        Returns:
            Number of tokens deleted
        """
        ...

    async def is_token_valid(self, token: str) -> bool:
        """
        Check if a refresh token is valid (exists, not revoked, not expired).

        Args:
            token: Token string to check

        Returns:
            True if token is valid, False otherwise
        """
        ...
