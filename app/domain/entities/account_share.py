"""Account share domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.value_objects.permission import Permission


@dataclass
class AccountShare:
    """
    Account share entity representing shared access to an account.

    Allows one user to share their account with another user
    with specific permissions and optional expiration.
    """

    id: UUID
    account_id: UUID
    shared_by_user_id: UUID  # Owner who shared the account
    shared_with_user_id: UUID  # User who received the share
    permissions: list[Permission]
    can_view: bool = True
    can_edit: bool = False
    can_delete: bool = False
    expires_at: datetime | None = None
    created_at: datetime | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate account share after initialization."""
        if self.shared_by_user_id == self.shared_with_user_id:
            raise ValueError("Cannot share account with yourself")

        # Ensure permissions list contains only Permission enum values
        if not all(isinstance(p, Permission) for p in self.permissions):
            raise ValueError("All permissions must be Permission enum values")

    def is_active(self) -> bool:
        """
        Check if this share is currently active.

        A share is active if it's not revoked and not expired.

        Returns:
            True if share is active
        """
        if self.revoked_at is not None:
            return False

        if self.expires_at is not None and datetime.utcnow() > self.expires_at:
            return False

        return True

    def is_expired(self) -> bool:
        """
        Check if this share has expired.

        Returns:
            True if share has expired
        """
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_revoked(self) -> bool:
        """
        Check if this share has been revoked.

        Returns:
            True if share has been revoked
        """
        return self.revoked_at is not None

    def revoke(self) -> None:
        """
        Revoke this account share.

        Sets revoked_at timestamp to current time.
        """
        if self.revoked_at is not None:
            raise ValueError("Account share is already revoked")
        self.revoked_at = datetime.utcnow()

    def has_permission(self, permission: Permission) -> bool:
        """
        Check if this share includes a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if share includes the permission
        """
        if not self.is_active():
            return False
        return permission in self.permissions

    def grant_permission(self, permission: Permission) -> None:
        """
        Grant a permission to this share.

        Args:
            permission: Permission to grant
        """
        if permission not in self.permissions:
            self.permissions.append(permission)

    def revoke_permission(self, permission: Permission) -> None:
        """
        Revoke a permission from this share.

        Args:
            permission: Permission to revoke
        """
        if permission in self.permissions:
            self.permissions.remove(permission)

    def extend_expiration(self, new_expiration: datetime) -> None:
        """
        Extend the expiration date of this share.

        Args:
            new_expiration: New expiration datetime

        Raises:
            ValueError: If new expiration is in the past or before current expiration
        """
        if new_expiration < datetime.utcnow():
            raise ValueError("Cannot set expiration in the past")

        if self.expires_at is not None and new_expiration < self.expires_at:
            raise ValueError("Cannot reduce expiration time")

        self.expires_at = new_expiration

    def make_permanent(self) -> None:
        """
        Remove expiration from this share, making it permanent.
        """
        self.expires_at = None

    def __eq__(self, other: object) -> bool:
        """Entity equality based on identity (id), not value."""
        if not isinstance(other, AccountShare):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity."""
        return hash(self.id)

    def __repr__(self) -> str:
        status = "active" if self.is_active() else "inactive"
        return (
            f"AccountShare(id={self.id}, account_id={self.account_id}, "
            f"shared_with={self.shared_with_user_id}, status={status})"
        )
