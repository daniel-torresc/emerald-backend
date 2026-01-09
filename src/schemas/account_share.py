"""
AccountShare Pydantic schemas for API request/response handling.

This module provides:
- Share creation and update schemas
- Share response schemas with user details
- Share filtering schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models import PermissionLevel
from .user import UserEmbeddedResponse


class AccountShareCreate(BaseModel):
    """
    Schema for creating an account share.

    Attributes:
        user_id: ID of the user to share with
        permission_level: Level of access to grant (owner, editor, viewer)
    """

    user_id: uuid.UUID = Field(
        description="ID of the user to share the account with",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    permission_level: PermissionLevel = Field(
        description="Permission level to grant (owner, editor, viewer)",
        examples=[PermissionLevel.viewer, PermissionLevel.editor],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "permission_level": "viewer",
            }
        }
    )


class AccountShareUpdate(BaseModel):
    """
    Schema for updating an account share.

    Only permission_level can be updated.

    Attributes:
        permission_level: New permission level
    """

    permission_level: PermissionLevel = Field(
        description="New permission level (owner, editor, viewer)",
        examples=[PermissionLevel.editor, PermissionLevel.viewer],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "permission_level": "editor",
            }
        }
    )


class AccountShareResponse(BaseModel):
    """
    Schema for account share response.

    Returns share details including user information.

    Attributes:
        id: Share UUID
        account_id: Account being shared
        user_id: User who has access
        permission_level: Permission level granted
        created_at: When share was created
        updated_at: When share was last updated
        user: User details (username, email, full_name)
    """

    id: uuid.UUID = Field(description="Share unique identifier")
    account_id: uuid.UUID = Field(description="Account being shared")
    user_id: uuid.UUID = Field(description="User who has access")
    permission_level: PermissionLevel = Field(description="Permission level granted")
    created_at: datetime = Field(description="When share was created")
    updated_at: datetime = Field(description="When share was last updated")
    user: UserEmbeddedResponse = Field(description="User details")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "123e4567-e89b-12d3-a456-426614174001",
                "user_id": "123e4567-e89b-12d3-a456-426614174002",
                "permission_level": "viewer",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "username": "johndoe",
                    "email": "john@example.com",
                    "full_name": "John Doe",
                },
            }
        },
    )


class AccountShareListResponse(BaseModel):
    """
    Schema for account share list item (optimized response).

    Lighter version of AccountShareResponse for list endpoints.

    Attributes:
        id: Share UUID
        user_id: User who has access
        permission_level: Permission level granted
        created_at: When share was created
        user: User summary (username, email, full_name)
    """

    id: uuid.UUID
    permission_level: PermissionLevel
    created_at: datetime
    user: UserEmbeddedResponse

    model_config = ConfigDict(from_attributes=True)
