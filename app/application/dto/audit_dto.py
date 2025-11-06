"""Audit DTOs (Data Transfer Objects)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateAuditLogInput(BaseModel):
    """Input DTO for creating an audit log entry."""

    user_id: UUID = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed (e.g., 'create', 'update')")
    entity_type: str = Field(..., description="Type of entity (e.g., 'user', 'account')")
    entity_id: UUID = Field(..., description="Entity's unique identifier")
    changes: Optional[dict[str, Any]] = Field(
        None, description="Changes made (before/after values)"
    )
    ip_address: Optional[str] = Field(None, description="IP address of the request")
    user_agent: Optional[str] = Field(None, description="User agent string")

    model_config = {"frozen": True}


class AuditLogOutput(BaseModel):
    """Output DTO for audit log information."""

    id: UUID = Field(..., description="Audit log's unique identifier")
    user_id: UUID = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    entity_type: str = Field(..., description="Type of entity")
    entity_id: UUID = Field(..., description="Entity's unique identifier")
    changes: Optional[dict[str, Any]] = Field(None, description="Changes made")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="When the action occurred")

    model_config = {"frozen": True, "from_attributes": True}

    @classmethod
    def from_entity(cls, audit_log: "AuditLog") -> "AuditLogOutput":
        """
        Create DTO from AuditLog entity.

        Args:
            audit_log: AuditLog domain entity

        Returns:
            AuditLogOutput DTO
        """
        return cls(
            id=audit_log.id,
            user_id=audit_log.user_id,
            action=audit_log.action,
            entity_type=audit_log.entity_type,
            entity_id=audit_log.entity_id,
            changes=audit_log.changes,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            timestamp=audit_log.timestamp,
        )


class QueryAuditLogsInput(BaseModel):
    """Input DTO for querying audit logs."""

    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    entity_id: Optional[UUID] = Field(None, description="Filter by entity ID")
    action: Optional[str] = Field(None, description="Filter by action")
    start_date: Optional[datetime] = Field(
        None, description="Filter logs after this date"
    )
    end_date: Optional[datetime] = Field(
        None, description="Filter logs before this date"
    )
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(
        default=100, ge=1, le=1000, description="Maximum number of records to return"
    )

    model_config = {"frozen": True}


class AuditLogListOutput(BaseModel):
    """Output DTO for paginated audit log list."""

    logs: list[AuditLogOutput] = Field(..., description="List of audit logs")
    total: int = Field(..., description="Total number of logs")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of logs per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = {"frozen": True}


# Import for type hints
from app.domain.entities.audit_log import AuditLog  # noqa: E402

AuditLogOutput.model_rebuild()
