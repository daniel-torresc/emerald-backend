"""Authentication DTOs (Data Transfer Objects)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterUserInput(BaseModel):
    """Input DTO for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="User's password")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name")

    model_config = {"frozen": True}


class LoginInput(BaseModel):
    """Input DTO for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    model_config = {"frozen": True}


class LoginOutput(BaseModel):
    """Output DTO for successful login."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")
    user: "UserProfileOutput" = Field(..., description="User profile information")

    model_config = {"frozen": True}


class RefreshTokenInput(BaseModel):
    """Input DTO for token refresh."""

    refresh_token: str = Field(..., description="Refresh token")

    model_config = {"frozen": True}


class RefreshTokenOutput(BaseModel):
    """Output DTO for token refresh."""

    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")

    model_config = {"frozen": True}


class ChangePasswordInput(BaseModel):
    """Input DTO for changing password."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    model_config = {"frozen": True}


class UserProfileOutput(BaseModel):
    """Output DTO for user profile information."""

    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    username: str = Field(..., description="Username")
    full_name: str = Field(..., description="Full name")
    is_active: bool = Field(..., description="Whether user account is active")
    is_admin: bool = Field(..., description="Whether user has admin privileges")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = {"frozen": True, "from_attributes": True}

    @classmethod
    def from_entity(cls, user: "User") -> "UserProfileOutput":
        """
        Create DTO from User entity.

        Args:
            user: User domain entity

        Returns:
            UserProfileOutput DTO
        """
        return cls(
            id=user.id,
            email=user.email.value,
            username=user.username.value,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


# Import for type hints
from app.domain.entities.user import User  # noqa: E402

UserProfileOutput.model_rebuild()
