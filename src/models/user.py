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

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin


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
        is_admin: Admin flag for administrative privileges
        last_login_at: Timestamp of last successful login
        created_at: When the account was created
        updated_at: When the account was last updated
        deleted_at: When the account was soft-deleted (NULL if active)
        created_by: Who created the account (system = NULL)
        updated_by: Who last updated the account

    Soft Delete:
        Deleted users have deleted_at set. They cannot login and are
        excluded from normal queries. Email and username remain reserved
        even after deletion (cannot be reused).

    Security:
        - password_hash stores Argon2id hash (never store plain passwords)
        - deleted_at controls login access (deleted users cannot login)
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

    # Indexes for common queries will be created in migration
    # __table_args__ will be used in migration for partial unique indexes

    def __repr__(self) -> str:
        """String representation of User."""
        return f"User(id={self.id}, username={self.username}, email={self.email})"
