"""Role domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.value_objects.permission import Permission


@dataclass
class Role:
    """
    Role entity representing a collection of permissions.

    A role is a named set of permissions that can be assigned to users.
    Roles enable role-based access control (RBAC).
    """

    id: UUID
    name: str
    description: str
    permissions: list[Permission] = field(default_factory=list)
    is_system_role: bool = False  # System roles cannot be deleted
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate role after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Role name cannot be empty")

        if len(self.name) > 100:
            raise ValueError("Role name cannot exceed 100 characters")

        # Ensure permissions list contains only Permission enum values
        if not all(isinstance(p, Permission) for p in self.permissions):
            raise ValueError("All permissions must be Permission enum values")

    def has_permission(self, permission: Permission) -> bool:
        """
        Check if this role has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if role has the permission
        """
        return permission in self.permissions

    def add_permission(self, permission: Permission) -> None:
        """
        Add a permission to this role.

        Args:
            permission: Permission to add
        """
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: Permission) -> None:
        """
        Remove a permission from this role.

        Args:
            permission: Permission to remove
        """
        if permission in self.permissions:
            self.permissions.remove(permission)

    def grant_permissions(self, permissions: list[Permission]) -> None:
        """
        Grant multiple permissions to this role.

        Args:
            permissions: List of permissions to grant
        """
        for permission in permissions:
            self.add_permission(permission)

    def revoke_permissions(self, permissions: list[Permission]) -> None:
        """
        Revoke multiple permissions from this role.

        Args:
            permissions: List of permissions to revoke
        """
        for permission in permissions:
            self.remove_permission(permission)

    def has_any_permission(self, permissions: list[Permission]) -> bool:
        """
        Check if role has any of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if role has at least one of the permissions
        """
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: list[Permission]) -> bool:
        """
        Check if role has all of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if role has all the permissions
        """
        return all(p in self.permissions for p in permissions)

    def is_admin_role(self) -> bool:
        """
        Check if this is an admin role.

        An admin role has the ADMIN_FULL_ACCESS permission.

        Returns:
            True if this is an admin role
        """
        return Permission.ADMIN_FULL_ACCESS in self.permissions

    def __eq__(self, other: object) -> bool:
        """Entity equality based on identity (id), not value."""
        if not isinstance(other, Role):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity."""
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Role(id={self.id}, name={self.name!r}, permissions={len(self.permissions)})"
