"""Refresh token domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class RefreshToken:
    """Domain entity representing a refresh token for authentication."""

    id: UUID
    user_id: UUID
    token: str
    expires_at: datetime
    created_at: datetime
    revoked_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """
        Check if the refresh token is valid.

        Returns:
            True if token is not expired and not revoked, False otherwise
        """
        now = datetime.utcnow()
        return now < self.expires_at and self.revoked_at is None

    def is_expired(self) -> bool:
        """
        Check if the refresh token has expired.

        Returns:
            True if token has expired, False otherwise
        """
        return datetime.utcnow() >= self.expires_at

    def is_revoked(self) -> bool:
        """
        Check if the refresh token has been revoked.

        Returns:
            True if token has been revoked, False otherwise
        """
        return self.revoked_at is not None

    def revoke(self) -> None:
        """Revoke this refresh token."""
        if self.revoked_at is None:
            self.revoked_at = datetime.utcnow()

    def __eq__(self, other: object) -> bool:
        """Entity equality based on identity (id), not value."""
        if not isinstance(other, RefreshToken):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity."""
        return hash(self.id)
