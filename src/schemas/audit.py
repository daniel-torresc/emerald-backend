"""
Audit log Pydantic schemas for API request/response handling.

This module provides:
- Audit log response schemas
- Audit log filtering parameters
- Audit log sort field enum
- Event type definitions
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models import AuditAction, AuditStatus


class AuditLogSortField(str, Enum):
    """
    Allowed sort fields for audit log list queries.

    Whitelists fields that can be used for sorting to prevent SQL injection.
    Values must match SQLAlchemy model attribute names exactly.
    """

    CREATED_AT = "created_at"
    ACTION = "action"
    ENTITY_TYPE = "entity_type"


class AuditLogResponse(BaseModel):
    """
    Schema for audit log response.

    Attributes:
        id: Audit log entry ID
        user_id: ID of user who performed the action
        action: Action performed (e.g., "LOGIN", "LOGOUT", "CREATE")
        entity_type: Type of entity affected (e.g., "user", "transaction")
        entity_id: ID of the affected entity
        ip_address: IP address of the client
        user_agent: User agent string of the client
        status: Action status ("SUCCESS", "FAILURE", "PARTIAL")
        old_values: Entity state before action (JSON)
        new_values: Entity state after action (JSON)
        description: Human-readable description of the action
        request_id: Correlation ID for tracing requests
        error_message: Error message if status is FAILURE
        extra_metadata: Additional context as JSON
        created_at: Timestamp of the action
    """

    id: UUID = Field(description="Audit log entry ID")
    user_id: UUID | None = Field(
        default=None,
        description="ID of user who performed the action",
    )
    action: str = Field(description="Action performed")
    entity_type: str = Field(description="Type of entity affected")
    entity_id: UUID | None = Field(
        default=None,
        description="ID of the affected entity",
    )
    old_values: dict | None = Field(
        default=None,
        description="Entity state before action",
    )
    new_values: dict | None = Field(
        default=None,
        description="Entity state after action",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the action",
    )
    ip_address: str | None = Field(default=None, description="Client IP address")
    user_agent: str | None = Field(default=None, description="Client user agent")
    request_id: str | None = Field(
        default=None,
        description="Correlation ID for tracing requests",
    )
    status: str = Field(description="Action status (SUCCESS/FAILURE/PARTIAL)")
    error_message: str | None = Field(
        default=None,
        description="Error message if status is FAILURE",
    )
    extra_metadata: dict | None = Field(
        default=None,
        description="Additional context as JSON",
    )
    created_at: datetime = Field(description="Timestamp of the action")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "action": "USER_UPDATE",
                "entity_type": "user",
                "entity_id": "123e4567-e89b-12d3-a456-426614174001",
                "old_values": {"email": "old@example.com"},
                "new_values": {"email": "new@example.com"},
                "description": "User updated their email address",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "request_id": "req-abc123",
                "status": "SUCCESS",
                "error_message": None,
                "extra_metadata": None,
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )


class AuditLogFilterParams(BaseModel):
    """
    Query parameters for filtering audit logs.

    Attributes:
        user_id: Filter by user ID
        action: Filter by action type
        entity_type: Filter by entity type
        entity_id: Filter by entity ID
        status: Filter by status (SUCCESS/FAILURE/PARTIAL)
        start_date: Filter logs after this date
        end_date: Filter logs before this date
    """

    user_id: UUID | None = Field(default=None, description="Filter by user ID")
    action: AuditAction | None = Field(
        default=None, description="Filter by action type"
    )
    entity_type: str | None = Field(
        default=None,
        description="Filter by entity type",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Filter by entity ID",
    )
    status: AuditStatus | None = Field(
        default=None,
        description="Filter by status (SUCCESS/FAILURE/PARTIAL)",
    )
    start_date: datetime | None = Field(
        default=None,
        description="Filter logs after this date",
    )
    end_date: datetime | None = Field(
        default=None,
        description="Filter logs before this date",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "action": "USER_UPDATE",
                "entity_type": "user",
                "status": "SUCCESS",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
            }
        }
    )
