"""
Authentication Pydantic schemas for API request/response handling.

This module provides:
- Login request and response schemas
- Token refresh schemas
- JWT token response models
"""

from datetime import UTC, datetime

from pydantic import BaseModel, EmailStr, Field, computed_field


class LoginRequest(BaseModel):
    """
    Schema for user login request.

    Attributes:
        email: User's email address
        password: User's password
    """

    email: EmailStr = Field(description="User's email address")
    password: str = Field(description="User's password")


class RefreshTokenRequest(BaseModel):
    """
    Schema for token refresh request.

    Attributes:
        refresh_token: JWT refresh token to use for obtaining new tokens
    """

    refresh_token: str = Field(description="JWT refresh token")


class AccessTokenResponse(BaseModel):
    """
    Schema for access token refresh response.

    Returned after successful token refresh.

    Attributes:
        access_token: New JWT access token
        refresh_token: New JWT refresh token (rotated)
        token_type: Type of token (always "bearer")
        expires_at: Access token expiration datetime
    """

    access_token: str = Field(description="New JWT access token")
    refresh_token: str = Field(description="New JWT refresh token (rotated)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: datetime = Field(
        description="Access token expiration datetime", exclude=True
    )

    @computed_field
    @property
    def expires_in(self) -> int:
        """Calculate seconds until expiration from expires_at."""
        now = datetime.now(UTC)
        delta = self.expires_at - now
        return int(delta.total_seconds())


class LogoutRequest(BaseModel):
    """
    Schema for logout request.

    Attributes:
        refresh_token: JWT refresh token to revoke
    """

    refresh_token: str = Field(description="JWT refresh token to revoke")
