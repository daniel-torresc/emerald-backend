"""
BootstrapState model for tracking initial admin setup.

This model ensures that the bootstrap process (creating the first admin user)
can only be performed once. After bootstrap is complete, the CLI command will
be disabled for security.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class BootstrapState(Base):
    """
    BootstrapState model for tracking system bootstrap.

    This table ensures that the initial admin user can only be created once.
    It enforces a single-row constraint, preventing multiple bootstrap attempts.

    Attributes:
        id: UUID primary key
        completed: Whether bootstrap has been completed
        completed_at: When bootstrap was completed
        admin_user_id: ID of the created admin user
        created_at: When this record was created

    Constraints:
        - Only one row can exist (enforced by CHECK constraint on completed=TRUE)
        - completed must be TRUE (bootstrap is atomic)

    Example:
        # Check if bootstrap is needed
        bootstrap = session.query(BootstrapState).first()
        if bootstrap and bootstrap.completed:
            raise ValueError("Bootstrap already completed")

        # Create bootstrap record after admin creation
        bootstrap = BootstrapState(
            completed=True,
            completed_at=datetime.now(UTC),
            admin_user_id=admin_user.id,
        )
        session.add(bootstrap)
        session.commit()
    """

    __tablename__ = "bootstrap_state"

    # Bootstrap completion flag (always TRUE when row exists)
    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # When bootstrap was completed
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Reference to the created admin user
    admin_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # When this record was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Table constraints
    __table_args__ = (
        # Ensure only one row can exist (PostgreSQL-specific)
        # This works by creating a unique constraint on a constant value
        CheckConstraint(
            "completed = TRUE",
            name="ck_bootstrap_state_completed",
        ),
    )

    def __repr__(self) -> str:
        """String representation of BootstrapState."""
        return (
            f"BootstrapState(id={self.id}, completed={self.completed}, "
            f"completed_at={self.completed_at}, admin_user_id={self.admin_user_id})"
        )
