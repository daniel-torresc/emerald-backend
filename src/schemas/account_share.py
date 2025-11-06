"""
AccountShare Pydantic schemas for API request/response handling.

This module provides:
- Share creation and update schemas
- Share response schemas with user details
- Share filtering schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.enums import PermissionLevel


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
        examples=[PermissionLevel.VIEWER, PermissionLevel.EDITOR],
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
        examples=[PermissionLevel.EDITOR, PermissionLevel.VIEWER],
    )


class UserSummary(BaseModel):
    """
    Summary of user information for share responses.

    Attributes:
        id: User UUID
        username: Username
        email: Email address
        full_name: Full name
    """

    id: uuid.UUID = Field(description="User unique identifier")
    username: str = Field(description="Username")
    email: str = Field(description="Email address")
    full_name: str | None = Field(description="Full name (optional)")

    model_config = {"from_attributes": True}


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
    user: UserSummary = Field(description="User details")

    model_config = {"from_attributes": True}


class AccountShareListItem(BaseModel):
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
    user_id: uuid.UUID
    permission_level: PermissionLevel
    created_at: datetime
    user: UserSummary

    model_config = {"from_attributes": True}
