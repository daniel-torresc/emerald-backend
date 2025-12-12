"""
Audit log Pydantic schemas for API request/response handling.

This module provides:
- Audit log response schemas
- Audit log filtering parameters
- Event type definitions
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models import AuditAction, AuditStatus


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

    model_config = {"from_attributes": True}


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
    action: AuditAction | None = Field(default=None, description="Filter by action type")
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
