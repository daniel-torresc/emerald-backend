"""
Audit log Pydantic schemas for API request/response handling.

This module provides:
- Audit log response schemas
- Audit log filtering parameters
- Event type definitions
"""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """
    Schema for audit log response.

    Attributes:
        id: Audit log entry ID
        user_id: ID of user who performed the action
        action: Action performed (e.g., "login", "logout", "user.create")
        resource_type: Type of resource affected (e.g., "user", "account")
        resource_id: ID of the affected resource
        ip_address: IP address of the client
        user_agent: User agent string of the client
        status: Action status ("success" or "failure")
        before_value: Resource state before action (JSON)
        after_value: Resource state after action (JSON)
        created_at: Timestamp of the action
    """

    id: int = Field(description="Audit log entry ID")
    user_id: int | None = Field(
        default=None,
        description="ID of user who performed the action",
    )
    action: str = Field(description="Action performed")
    resource_type: str | None = Field(
        default=None,
        description="Type of resource affected",
    )
    resource_id: str | None = Field(
        default=None,
        description="ID of the affected resource",
    )
    ip_address: str | None = Field(default=None, description="Client IP address")
    user_agent: str | None = Field(default=None, description="Client user agent")
    status: str = Field(description="Action status (success/failure)")
    before_value: dict | None = Field(
        default=None,
        description="Resource state before action",
    )
    after_value: dict | None = Field(
        default=None,
        description="Resource state after action",
    )
    created_at: datetime = Field(description="Timestamp of the action")

    model_config = {"from_attributes": True}


class AuditLogFilterParams(BaseModel):
    """
    Query parameters for filtering audit logs.

    Attributes:
        user_id: Filter by user ID
        action: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        status: Filter by status (success/failure)
        start_date: Filter logs after this date
        end_date: Filter logs before this date
    """

    user_id: int | None = Field(default=None, description="Filter by user ID")
    action: str | None = Field(default=None, description="Filter by action type")
    resource_type: str | None = Field(
        default=None,
        description="Filter by resource type",
    )
    resource_id: str | None = Field(
        default=None,
        description="Filter by resource ID",
    )
    status: str | None = Field(
        default=None,
        description="Filter by status (success/failure)",
    )
    start_date: datetime | None = Field(
        default=None,
        description="Filter logs after this date",
    )
    end_date: datetime | None = Field(
        default=None,
        description="Filter logs before this date",
    )