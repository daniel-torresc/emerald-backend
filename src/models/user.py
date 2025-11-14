"""
User, Role, and UserRole models.

This module defines:
- User: Core user model with authentication and profile information
- Role: Role definition with JSONB permissions
- UserRole: Many-to-many junction table between User and Role

Architecture:
- Users can have multiple roles (many-to-many relationship)
- Roles contain permissions as JSONB array
- Permissions follow format: resource:action[:scope]
  Examples: "users:read:self", "users:write:all", "audit_logs:read:all"
"""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin

# =============================================================================
# UserRole Junction Table (Many-to-Many)
# =============================================================================
# This table links users to their roles. A user can have multiple roles,
# and a role can be assigned to multiple users.

user_roles = Table(
    "user_roles",
    Base.metadata,
    # User foreign key
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Role foreign key
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # When the role was assigned
    Column(
        "assigned_at",
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    ),
    # Who assigned the role (nullable for system assignments)
    Column(
        "assigned_by",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
)


# =============================================================================
# User Model
# =============================================================================

class User(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    User model for authentication and profile management.

    Attributes:
        id: UUID primary key
        username: Unique username (alphanumeric, underscore, hyphen)
        email: Unique email address
        password_hash: Argon2id hashed password
        full_name: User's full name
        is_active: Whether the account is active (can login)
        is_admin: Quick admin flag (use roles for fine-grained permissions)
        last_login_at: Timestamp of last successful login
        created_at: When the account was created
        updated_at: When the account was last updated
        deleted_at: When the account was soft-deleted (NULL if active)
        created_by: Who created the account (system = NULL)
        updated_by: Who last updated the account
        roles: List of Role objects assigned to this user

    Soft Delete:
        Deleted users have deleted_at set. They cannot login and are
        excluded from normal queries. Email and username remain reserved
        even after deletion (cannot be reused).

    Security:
        - password_hash stores Argon2id hash (never store plain passwords)
        - is_active controls login access (can be used for banning)
        - last_login_at tracks user activity
    """

    __tablename__ = "users"

    # Authentication fields
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,  # Fully unique - no two users can have same username (even if deleted)
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,  # Fully unique - no two users can have same email (even if deleted)
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # Activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",  # Load roles automatically
        primaryjoin="User.id == user_roles.c.user_id",
        secondaryjoin="Role.id == user_roles.c.role_id",
    )

    # Indexes for common queries will be created in migration
    # __table_args__ will be used in migration for partial unique indexes

    def __repr__(self) -> str:
        """String representation of User."""
        return f"User(id={self.id}, username={self.username}, email={self.email})"


# =============================================================================
# Role Model
# =============================================================================

class Role(Base, TimestampMixin):
    """
    Role model for role-based access control (RBAC).

    Roles define a set of permissions that can be assigned to users.
    Permissions are stored as a JSONB array for flexibility.

    Attributes:
        id: UUID primary key
        name: Unique role name (e.g., "admin", "user", "readonly")
        description: Human-readable description of the role
        permissions: JSONB array of permission strings
        created_at: When the role was created
        updated_at: When the role was last updated
        users: List of User objects assigned this role

    Permission Format:
        Permissions follow the pattern: resource:action[:scope]

        Examples:
        - "users:read:self" - Read own user profile
        - "users:read:all" - Read all user profiles (admin)
        - "users:write:self" - Update own user profile
        - "users:write:all" - Update any user profile (admin)
        - "users:delete:all" - Delete users (admin)
        - "audit_logs:read:self" - View own audit logs
        - "audit_logs:read:all" - View all audit logs (admin)
        - "transactions:read:self" - View own transactions
        - "transactions:write:self" - Create own transactions

    Built-in Roles (created in migration):
        - "admin": Full access to all resources
        - "user": Standard user permissions (self-access only)
        - "readonly": Read-only access (for support/audit)
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    permissions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        primaryjoin="Role.id == user_roles.c.role_id",
        secondaryjoin="User.id == user_roles.c.user_id",
    )

    def __repr__(self) -> str:
        """String representation of Role."""
        return f"Role(id={self.id}, name={self.name})"

    def has_permission(self, permission: str) -> bool:
        """
        Check if this role has a specific permission.

        Args:
            permission: Permission string to check

        Returns:
            True if role has the permission, False otherwise

        Example:
            >>> admin_role.has_permission("users:write:all")
            True
            >>> user_role.has_permission("users:write:all")
            False
        """
        return permission in self.permissions
