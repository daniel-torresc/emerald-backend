"""
Admin Pydantic schemas for API request/response handling.

This module provides:
- Admin user creation and update schemas
- Admin user response schemas
- Admin permission management schemas
- Admin filtering and listing schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.core.security import validate_password_strength


class CreateAdminUserRequest(BaseModel):
    """
    Schema for creating a new admin user.

    Attributes:
        username: Admin username (3-50 characters, alphanumeric + underscore)
        email: Admin email address
        password: Admin password (optional, generated if not provided)
        full_name: Admin full name (optional)
        permissions: Custom permissions (optional, defaults to full admin)
    """

    username: str = Field(
        min_length=3,
        max_length=50,
        description="Admin username (3-50 characters)",
    )
    email: EmailStr = Field(description="Admin email address")
    password: str | None = Field(
        default=None,
        min_length=8,
        description="Admin password (min 8 chars, leave empty to generate)",
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Admin full name",
    )
    permissions: list[str] | None = Field(
        default=None,
        description="Custom permissions (defaults to full admin access)",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """Validate username format."""
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        """Validate password strength requirements if provided."""
        if value is not None:
            is_valid, error_message = validate_password_strength(value)
            if not is_valid:
                raise ValueError(error_message)
        return value


class UpdateAdminUserRequest(BaseModel):
    """
    Schema for updating admin user information.

    Only allows updating full_name and is_active status.
    Username and email cannot be changed via this endpoint.

    Attributes:
        full_name: New full name (optional)
        is_active: Active status (optional)
    """

    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Admin full name",
    )
    is_active: bool | None = Field(
        default=None,
        description="Active status",
    )


class ResetPasswordRequest(BaseModel):
    """
    Schema for resetting admin user password.

    Attributes:
        new_password: New password (optional, generated if not provided)
    """

    new_password: str | None = Field(
        default=None,
        min_length=8,
        description="New password (min 8 chars, leave empty to generate)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        """Validate password strength requirements if provided."""
        if value is not None:
            is_valid, error_message = validate_password_strength(value)
            if not is_valid:
                raise ValueError(error_message)
        return value


class UpdatePermissionsRequest(BaseModel):
    """
    Schema for updating admin user permissions.

    Attributes:
        permissions: List of permission strings
    """

    permissions: list[str] = Field(
        description="List of permission strings",
        min_length=1,
    )


class AdminUserResponse(BaseModel):
    """
    Schema for admin user response (detailed admin information).

    Used for single admin endpoints (GET /admin/users/{id}, POST /admin/users).

    Attributes:
        id: Admin user's unique identifier
        username: Admin username
        email: Admin email address
        full_name: Admin full name
        is_active: Whether admin account is active
        is_admin: Always true for admin users
        permissions: List of permission strings
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login_at: Last login timestamp
        temporary_password: Temporary password (only on creation/reset)
    """

    id: uuid.UUID = Field(description="Admin user's unique identifier (UUID)")
    username: str = Field(description="Admin username")
    email: str = Field(description="Admin email address")
    full_name: str | None = Field(default=None, description="Admin full name")
    is_active: bool = Field(description="Whether admin account is active")
    is_admin: bool = Field(
        description="Whether user has admin privileges (always true)"
    )
    permissions: list[str] = Field(description="List of permission strings")
    created_at: datetime = Field(description="Account creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    last_login_at: datetime | None = Field(
        default=None,
        description="Last login timestamp",
    )
    temporary_password: str | None = Field(
        default=None,
        description="Temporary password (only on creation/reset if generated)",
    )

    model_config = {"from_attributes": True}


class AdminUserListItem(BaseModel):
    """
    Schema for admin user list items (summary information).

    Used for list endpoints (GET /admin/users) to reduce response size.

    Attributes:
        id: Admin user's unique identifier
        username: Admin username
        email: Admin email address
        full_name: Admin full name
        is_active: Whether admin account is active
        created_at: Account creation timestamp
        last_login_at: Last login timestamp
    """

    id: uuid.UUID = Field(description="Admin user's unique identifier (UUID)")
    username: str = Field(description="Admin username")
    email: str = Field(description="Admin email address")
    full_name: str | None = Field(default=None, description="Admin full name")
    is_active: bool = Field(description="Whether admin account is active")
    created_at: datetime = Field(description="Account creation timestamp")
    last_login_at: datetime | None = Field(
        default=None,
        description="Last login timestamp",
    )

    model_config = {"from_attributes": True}


class AdminUserFilterParams(BaseModel):
    """
    Query parameters for filtering admin user lists.

    Attributes:
        search: Search in username, email, or full_name
        is_active: Filter by active status
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (max 100)
        sort_by: Field to sort by (username or created_at)
    """

    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Search in username, email, or full_name",
    )
    is_active: bool | None = Field(
        default=None,
        description="Filter by active status",
    )
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip (pagination)",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of records to return (max 100)",
    )
    sort_by: str | None = Field(
        default="created_at",
        description="Field to sort by (username or created_at)",
    )

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, value: str | None) -> str | None:
        """Validate sort_by field."""
        if value is not None and value not in ["username", "created_at"]:
            raise ValueError("sort_by must be 'username' or 'created_at'")
        return value

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        """Ensure limit doesn't exceed maximum."""
        if value > 100:
            return 100
        return value
