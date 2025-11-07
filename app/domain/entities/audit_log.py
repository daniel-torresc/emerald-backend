"""Audit log domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuditLog:
    """
    Audit log entity for tracking system events.

    Immutable entity that records who did what, when, and where.
    Used for security auditing, compliance, and debugging.
    """

    id: UUID
    user_id: UUID | None  # None for system-generated events
    action: str
    resource_type: str
    resource_id: UUID | None
    details: dict[str, str | int | float | bool | None]
    ip_address: str | None
    user_agent: str | None
    timestamp: datetime

    def __post_init__(self) -> None:
        """Validate audit log after initialization."""
        if not self.action or not self.action.strip():
            raise ValueError("Audit log action cannot be empty")

        if not self.resource_type or not self.resource_type.strip():
            raise ValueError("Audit log resource_type cannot be empty")

        if len(self.action) > 100:
            raise ValueError("Audit log action cannot exceed 100 characters")

        if len(self.resource_type) > 100:
            raise ValueError("Audit log resource_type cannot exceed 100 characters")

    def is_user_action(self) -> bool:
        """
        Check if this is a user-initiated action.

        Returns:
            True if action was initiated by a user
        """
        return self.user_id is not None

    def is_system_action(self) -> bool:
        """
        Check if this is a system-initiated action.

        Returns:
            True if action was initiated by the system
        """
        return self.user_id is None

    def get_detail(self, key: str) -> str | int | float | bool | None:
        """
        Get a specific detail value.

        Args:
            key: Detail key

        Returns:
            Detail value or None if not found
        """
        return self.details.get(key)

    def has_detail(self, key: str) -> bool:
        """
        Check if a specific detail exists.

        Args:
            key: Detail key

        Returns:
            True if detail exists
        """
        return key in self.details

    def __eq__(self, other: object) -> bool:
        """Entity equality based on identity (id), not value."""
        if not isinstance(other, AuditLog):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity."""
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"AuditLog(id={self.id}, action={self.action!r}, "
            f"resource_type={self.resource_type!r}, timestamp={self.timestamp})"
        )
