"""
User Pydantic schemas for API request/response handling.

This module provides:
- User creation and update schemas
- User response schemas
- Password change schemas
- User filtering and listing schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.core.security import validate_password_strength


class UserBase(BaseModel):
    """
    Base user schema with common fields.

    Attributes:
        email: User's email address (unique)
        username: User's username (unique)
    """

    email: EmailStr = Field(description="User's email address")
    username: str = Field(
        min_length=3,
        max_length=50,
        description="User's username (3-50 characters)",
    )


class UserCreate(UserBase):
    """
    Schema for user registration/creation.

    Attributes:
        email: User's email address
        username: User's username
        password: User's password (validated for strength)
    """

    password: str = Field(
        min_length=8,
        description="User's password (min 8 characters, must meet strength requirements)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Validate password strength requirements."""
        is_valid, error_message = validate_password_strength(value)
        if not is_valid:
            raise ValueError(error_message)
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """Validate username format."""
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return value


class UserUpdate(BaseModel):
    """
    Schema for updating user information.

    All fields are optional to support partial updates (PATCH).

    Attributes:
        email: New email address
        username: New username
        full_name: New full name
    """

    email: EmailStr | None = Field(default=None, description="New email address")
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="New username",
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New full name",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        """Validate username format if provided."""
        if value is not None:
            if not value.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        """Validate and trim full name if provided."""
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value


class UserPasswordChange(BaseModel):
    """
    Schema for changing user password.

    Attributes:
        current_password: User's current password (for verification)
        new_password: New password (validated for strength)
    """

    current_password: str = Field(description="Current password for verification")
    new_password: str = Field(
        min_length=8,
        description="New password (min 8 characters, must meet strength requirements)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """Validate new password strength requirements."""
        is_valid, error_message = validate_password_strength(value)
        if not is_valid:
            raise ValueError(error_message)
        return value


class UserResponse(BaseModel):
    """
    Schema for user response (detailed user information).

    Used for single user endpoints (GET /users/{id}, POST /users).

    Attributes:
        id: User's unique identifier
        email: User's email address
        username: User's username
        full_name: User's full name
        is_admin: Whether user has admin privileges
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login_at: Last login timestamp
    """

    id: uuid.UUID = Field(description="User's unique identifier (UUID)")
    email: str = Field(description="User's email address")
    username: str = Field(description="User's username")
    full_name: str | None = Field(default=None, description="User's full name")
    is_admin: bool = Field(description="Whether user has admin privileges")
    created_at: datetime = Field(description="Account creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    last_login_at: datetime | None = Field(
        default=None,
        description="Last login timestamp",
    )

    model_config = {"from_attributes": True}


class UserListItem(BaseModel):
    """
    Schema for user list items (summary information).

    Used for list endpoints (GET /users) to reduce response size.

    Attributes:
        id: User's unique identifier
        email: User's email address
        username: User's username
        created_at: Account creation timestamp
    """

    id: uuid.UUID = Field(description="User's unique identifier (UUID)")
    email: str = Field(description="User's email address")
    username: str = Field(description="User's username")
    created_at: datetime = Field(description="Account creation timestamp")

    model_config = {"from_attributes": True}


class UserFilterParams(BaseModel):
    """
    Query parameters for filtering user lists.

    Attributes:
        is_superuser: Filter by superuser status
        search: Search in email or username
    """

    is_superuser: bool | None = Field(
        default=None,
        description="Filter by superuser status",
    )
    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Search in email or username",
    )
