"""
Reusable mixins for database models.

This module provides mixins for common model patterns:
- TimestampMixin: created_at and updated_at timestamps
- SoftDeleteMixin: soft delete with deleted_at timestamp
- AuditFieldsMixin: created_by and updated_by tracking
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """
    Mixin to add timestamp columns to models.

    Adds:
    - created_at: Timestamp when record was created (auto-set)
    - updated_at: Timestamp when record was last updated (auto-updated)

    Both timestamps use UTC timezone.

    Usage:
        class User(Base, TimestampMixin):
            __tablename__ = "users"
            username: Mapped[str]
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality to models.

    Adds:
    - deleted_at: Timestamp when record was soft-deleted (NULL if not deleted)

    Soft deleted records remain in the database but are filtered out from
    queries by default. This is required for:
    - Regulatory compliance (7+ year retention for financial data)
    - Accidental deletion recovery
    - Audit trail preservation

    Usage:
        class User(Base, SoftDeleteMixin):
            __tablename__ = "users"
            username: Mapped[str]

    Querying with soft deletes:
        # Get only active records (deleted_at IS NULL)
        active_users = select(User).where(User.deleted_at.is_(None))

        # Get all records including deleted
        all_users = select(User)

    Important: When implementing unique constraints on models with soft delete,
    use partial unique indexes in migrations:
        CREATE UNIQUE INDEX users_email_unique
        ON users(email)
        WHERE deleted_at IS NULL
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,  # Index for efficient filtering
    )

    @property
    def is_deleted(self) -> bool:
        """
        Check if this record has been soft deleted.

        Returns:
            True if deleted (deleted_at is set), False otherwise
        """
        return self.deleted_at is not None


class AuditFieldsMixin:
    """
    Mixin to track who created and updated records.

    Adds:
    - created_by: UUID of user who created the record
    - updated_by: UUID of user who last updated the record

    Both fields are nullable to support:
    - System-generated records (created_by = None)
    - Initial data migrations
    - Anonymous actions

    Usage:
        class Transaction(Base, AuditFieldsMixin):
            __tablename__ = "transactions"
            amount: Mapped[Decimal]

    Setting audit fields:
        # In service layer, pass current user
        transaction = Transaction(
            amount=100.00,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    """

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
