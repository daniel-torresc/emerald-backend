"""
AuditLog model for comprehensive audit trail.

This module implements immutable audit logging for:
- GDPR compliance (data access and modification tracking)
- SOX compliance (7-year retention for financial data)
- Security monitoring (authentication events, permission changes)
- Forensic analysis (who did what, when, and why)

Audit logs are WRITE-ONCE - they cannot be modified or deleted after creation.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import AuditAction, AuditStatus
from .user import User


class AuditLog(Base):
    """
    AuditLog model for tracking all system actions.

    This model provides a comprehensive, immutable audit trail of all actions
    in the system. It's designed to meet regulatory requirements (GDPR, SOX)
    and support security monitoring and forensic analysis.

    Immutability:
    - Audit logs CANNOT be modified after creation
    - Audit logs CANNOT be deleted (except by automated retention policy)
    - Database constraints prevent updates/deletes on this table

    Compliance:
    - GDPR: Tracks all data access and modifications
    - SOX: 7-year retention for financial data
    - PCI DSS: Tracks all access to cardholder data

    Attributes:
        id: UUID primary key
        user_id: User who performed the action (NULL for system actions)
        action: Type of action performed (enum)
        entity_type: Type of entity affected (e.g., "user", "transaction")
        entity_id: UUID of the affected entity
        old_values: JSONB snapshot of values before the action
        new_values: JSONB snapshot of values after the action
        description: Human-readable description of the action
        ip_address: IP address of the client
        user_agent: User agent string of the client
        request_id: Correlation ID for tracing requests
        status: Status of the action (SUCCESS, FAILURE, PARTIAL)
        error_message: Error message if status is FAILURE
        extra_metadata: Additional context as JSONB
        created_at: When the action occurred (indexed for queries)
        user: Relationship to User model

    Data Retention:
    - 7 years for financial compliance (configurable via settings)
    - Older logs archived to cold storage (S3 Glacier)
    - Automatic cleanup job runs monthly

    Query Performance:
    - Indexed by user_id, entity_type, entity_id, action, created_at
    - Partitioned by date for large datasets (future enhancement)

    Example:
        # Log user login
        audit_log = AuditLog(
            user_id=user.id,
            action=AuditAction.LOGIN,
            entity_type="user",
            entity_id=user.id,
            description="User logged in successfully",
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            request_id=request.state.request_id,
            status=AuditStatus.SUCCESS,
        )

        # Log data modification with before/after values
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=target_user.id,
            old_values={"email": "old@example.com", "full_name": "Old Name"},
            new_values={"email": "new@example.com", "full_name": "New Name"},
            description="User profile updated",
            status=AuditStatus.SUCCESS,
        )
    """

    __tablename__ = "audit_logs"

    # Who performed the action (NULL for system actions)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What action was performed
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action_enum", create_type=True),
        nullable=False,
        index=True,
    )

    # What entity was affected
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # What changed (for data modifications)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Human-readable description
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        index=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(36),  # UUID length
        nullable=True,
        index=True,
    )

    # Action result
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, name="audit_status_enum", create_type=True),
        nullable=False,
        default=AuditStatus.SUCCESS,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Additional context
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamp (immutable, indexed for queries)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationship to User (who performed the action)
    user: Mapped[User | None] = relationship(
        "User",
        lazy="selectin",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        # Index for user's audit logs
        Index("ix_audit_logs_user_date", "user_id", "created_at"),
        # Index for entity audit logs
        Index("ix_audit_logs_entity", "entity_type", "entity_id", "created_at"),
        # Index for action-based queries
        Index("ix_audit_logs_action_date", "action", "created_at"),
        # Index for request correlation
        Index("ix_audit_logs_request", "request_id", "created_at"),
        # Index for security monitoring (failed actions)
        Index(
            "ix_audit_logs_failures",
            "status",
            "created_at",
            postgresql_where=(status == AuditStatus.FAILURE),
        ),
    )

    def __repr__(self) -> str:
        """String representation of AuditLog."""
        return (
            f"AuditLog(id={self.id}, user_id={self.user_id}, action={self.action}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id})"
        )
