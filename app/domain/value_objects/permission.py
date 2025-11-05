"""Permission value object."""

from enum import Enum


class Permission(str, Enum):
    """
    System permissions.

    Defines all permissions that can be granted through roles.
    """

    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"

    # Account permissions
    ACCOUNT_READ = "account:read"
    ACCOUNT_WRITE = "account:write"
    ACCOUNT_DELETE = "account:delete"
    ACCOUNT_LIST = "account:list"
    ACCOUNT_SHARE = "account:share"

    # Transaction permissions
    TRANSACTION_READ = "transaction:read"
    TRANSACTION_WRITE = "transaction:write"
    TRANSACTION_DELETE = "transaction:delete"
    TRANSACTION_LIST = "transaction:list"

    # Category permissions
    CATEGORY_READ = "category:read"
    CATEGORY_WRITE = "category:write"
    CATEGORY_DELETE = "category:delete"
    CATEGORY_LIST = "category:list"

    # Budget permissions
    BUDGET_READ = "budget:read"
    BUDGET_WRITE = "budget:write"
    BUDGET_DELETE = "budget:delete"
    BUDGET_LIST = "budget:list"

    # Report permissions
    REPORT_READ = "report:read"
    REPORT_GENERATE = "report:generate"

    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_LIST = "audit:list"

    # Admin permissions
    ADMIN_FULL_ACCESS = "admin:full_access"
    ROLE_MANAGE = "role:manage"
    SYSTEM_CONFIG = "system:config"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Permission.{self.name}"

    @property
    def resource(self) -> str:
        """Extract resource name from permission (e.g., 'user' from 'user:read')."""
        return self.value.split(":")[0]

    @property
    def action(self) -> str:
        """Extract action from permission (e.g., 'read' from 'user:read')."""
        return self.value.split(":")[1]

    def is_admin_permission(self) -> bool:
        """Check if this is an admin-level permission."""
        return self.resource in ("admin", "role", "system")

    @classmethod
    def from_string(cls, value: str) -> "Permission":
        """
        Create Permission from string value.

        Args:
            value: Permission string (e.g., "user:read")

        Returns:
            Permission enum value

        Raises:
            ValueError: If permission is not valid
        """
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid permission: {value}")

    @classmethod
    def all_permissions(cls) -> list["Permission"]:
        """Get list of all permissions."""
        return list(cls)

    @classmethod
    def user_permissions(cls) -> list["Permission"]:
        """Get list of user-related permissions."""
        return [p for p in cls if p.resource == "user"]

    @classmethod
    def account_permissions(cls) -> list["Permission"]:
        """Get list of account-related permissions."""
        return [p for p in cls if p.resource == "account"]

    @classmethod
    def admin_permissions(cls) -> list["Permission"]:
        """Get list of admin permissions."""
        return [p for p in cls if p.is_admin_permission()]
