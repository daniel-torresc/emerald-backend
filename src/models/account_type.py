"""
AccountType model.

This module defines:
- AccountType: Account types master data (checking, savings, investment, HSA, 401k, etc.)

Architecture:
- Centralized repository of account types
- Used by accounts to categorize financial accounts
- Administrator-managed, globally available to all users
- Uses is_active flag instead of soft delete (types can be deactivated)
"""

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.mixins import TimestampMixin


class AccountType(Base, TimestampMixin):
    """
    Account type model for master data management.

    Represents different types of financial accounts (checking, savings,
    investment, HSA, 401k, crypto, etc.). This is master data used to
    standardize account categorization across all users.

    Attributes:
        id: UUID primary key
        key: Unique identifier for programmatic use (lowercase, alphanumeric, underscore)
        name: Display name shown to users (max 100 chars)
        description: Detailed description of the account type (max 500 chars, optional)
        icon_url: URL to icon image for UI display (max 500 chars, optional)
        sort_order: Integer for controlling display order (lower = first, default: 0)
        created_at: When the account type was created (auto-set)
        updated_at: When the account type was last updated (auto-updated)

    Unique Constraints:
        - key must be unique globally - enforced via unique constraint

    Check Constraints:
        - key must match pattern ^[a-z0-9_]+$ (lowercase, alphanumeric, underscore only)

    Indexes:
        - key (unique index from constraint)
        - sort_order (for ordering)

    Business Rules:
        - Only administrators can create, update, or delete account types
        - All users can view and select from available account types
        - Keys are immutable once created
        - Account types can be hard-deleted if no accounts reference them

    Note:
        This model does NOT use SoftDeleteMixin. Account types use hard delete
        (permanent removal from database). This is because:
        - Account type data is master data, not transactional data
        - Hard delete is appropriate for cleanup of unused types
        - Foreign key constraints prevent deletion of types in use
    """

    __tablename__ = "account_types"

    # Identification fields
    key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Unique identifier for programmatic use (lowercase, alphanumeric, underscore)",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name shown to users",
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Detailed description of the account type",
    )

    # Visual identity
    icon_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to icon image for UI display",
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,  # Index for ordering
        comment="Integer for controlling display order (lower numbers appear first)",
    )

    # Unique constraint on key (created in migration)
    # Check constraint for key format (created in migration):
    # - CHECK (key ~ '^[a-z0-9_]+$')

    def __repr__(self) -> str:
        """String representation of AccountType."""
        return f"AccountType(id={self.id}, key={self.key}, name={self.name})"
