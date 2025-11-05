"""User domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.exceptions import InvalidUserStateTransitionError
from app.domain.value_objects.email import Email
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.value_objects.permission import Permission
from app.domain.value_objects.username import Username


@dataclass
class User:
    """
    User entity representing a system user.

    A user can authenticate, own accounts, have roles,
    and perform actions based on their permissions.
    """

    id: UUID
    email: Email
    username: Username
    password_hash: PasswordHash
    full_name: str
    is_active: bool = True
    is_admin: bool = False
    roles: list["Role"] = field(default_factory=list)  # Forward reference
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    last_login_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate user after initialization."""
        if not self.full_name or not self.full_name.strip():
            raise ValueError("Full name cannot be empty")

        if len(self.full_name) > 200:
            raise ValueError("Full name cannot exceed 200 characters")

    def activate(self) -> None:
        """
        Activate this user account.

        Raises:
            InvalidUserStateTransitionError: If user is already active
        """
        if self.is_active:
            raise InvalidUserStateTransitionError("active", "activate")
        self.is_active = True

    def deactivate(self) -> None:
        """
        Deactivate this user account.

        Raises:
            InvalidUserStateTransitionError: If user is already inactive
        """
        if not self.is_active:
            raise InvalidUserStateTransitionError("inactive", "deactivate")
        self.is_active = False

    def make_admin(self) -> None:
        """
        Grant admin privileges to this user.

        Raises:
            InvalidUserStateTransitionError: If user is already admin
        """
        if self.is_admin:
            raise InvalidUserStateTransitionError("admin", "make_admin")
        self.is_admin = True

    def revoke_admin(self) -> None:
        """
        Revoke admin privileges from this user.

        Raises:
            InvalidUserStateTransitionError: If user is not admin
        """
        if not self.is_admin:
            raise InvalidUserStateTransitionError("non-admin", "revoke_admin")
        self.is_admin = False

    def change_password(self, new_password_hash: PasswordHash) -> None:
        """
        Change user password.

        Args:
            new_password_hash: New password hash
        """
        self.password_hash = new_password_hash

    def update_full_name(self, new_full_name: str) -> None:
        """
        Update user's full name.

        Args:
            new_full_name: New full name

        Raises:
            ValueError: If name is invalid
        """
        if not new_full_name or not new_full_name.strip():
            raise ValueError("Full name cannot be empty")

        if len(new_full_name) > 200:
            raise ValueError("Full name cannot exceed 200 characters")

        self.full_name = new_full_name.strip()

    def update_email(self, new_email: Email) -> None:
        """
        Update user's email address.

        Args:
            new_email: New email address
        """
        self.email = new_email

    def update_username(self, new_username: Username) -> None:
        """
        Update user's username.

        Args:
            new_username: New username
        """
        self.username = new_username

    def record_login(self) -> None:
        """Record that user logged in."""
        self.last_login_at = datetime.utcnow()

    def has_permission(self, permission: Permission) -> bool:
        """
        Check if user has a specific permission.

        Admin users have all permissions.
        Otherwise, check through assigned roles.

        Args:
            permission: Permission to check

        Returns:
            True if user has the permission
        """
        if self.is_admin:
            return True

        return any(role.has_permission(permission) for role in self.roles)

    def has_any_permission(self, permissions: list[Permission]) -> bool:
        """
        Check if user has any of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has at least one permission
        """
        if self.is_admin:
            return True

        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, permissions: list[Permission]) -> bool:
        """
        Check if user has all of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has all permissions
        """
        if self.is_admin:
            return True

        return all(self.has_permission(p) for p in permissions)

    def add_role(self, role: "Role") -> None:
        """
        Assign a role to this user.

        Args:
            role: Role to assign

        Raises:
            ValueError: If role is already assigned
        """
        if role in self.roles:
            raise ValueError(f"User already has role: {role.name}")

        self.roles.append(role)

    def remove_role(self, role: "Role") -> None:
        """
        Remove a role from this user.

        Args:
            role: Role to remove

        Raises:
            ValueError: If role is not assigned
        """
        if role not in self.roles:
            raise ValueError(f"User does not have role: {role.name}")

        self.roles.remove(role)

    def has_role(self, role_name: str) -> bool:
        """
        Check if user has a specific role by name.

        Args:
            role_name: Name of role to check

        Returns:
            True if user has the role
        """
        return any(role.name == role_name for role in self.roles)

    def get_all_permissions(self) -> set[Permission]:
        """
        Get all permissions this user has (from all roles).

        Returns:
            Set of all permissions
        """
        if self.is_admin:
            return set(Permission.all_permissions())

        permissions: set[Permission] = set()
        for role in self.roles:
            permissions.update(role.permissions)

        return permissions

    def can_access_account(self, account: "Account") -> bool:
        """
        Check if user can access a specific account.

        A user can access an account if they own it or it's shared with them.

        Args:
            account: Account to check access for

        Returns:
            True if user can access the account
        """
        return account.can_be_accessed_by(self.id)

    def is_deleted(self) -> bool:
        """
        Check if user is soft-deleted.

        Returns:
            True if user is deleted
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """
        Soft delete this user.

        Raises:
            InvalidUserStateTransitionError: If user is already deleted
        """
        if self.is_deleted():
            raise InvalidUserStateTransitionError("deleted", "soft_delete")

        self.deleted_at = datetime.utcnow()
        self.is_active = False

    def __eq__(self, other: object) -> bool:
        """Entity equality based on identity (id), not value."""
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity."""
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"User(id={self.id}, username={self.username}, "
            f"email={self.email}, is_active={self.is_active})"
        )


# Import here to avoid circular import
from app.domain.entities.role import Role  # noqa: E402
from app.domain.entities.account import Account  # noqa: E402
