"""
Authentication Pydantic schemas for API request/response handling.

This module provides:
- Login request and response schemas
- Token refresh schemas
- JWT token response models
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """
    Schema for user login request.

    Attributes:
        email: User's email address
        password: User's password
    """

    email: EmailStr = Field(description="User's email address")
    password: str = Field(description="User's password")


class TokenResponse(BaseModel):
    """
    Schema for authentication token response.

    Returned after successful login or registration.

    Attributes:
        access_token: JWT access token (short-lived, 15 minutes)
        refresh_token: JWT refresh token (long-lived, 7 days)
        token_type: Type of token (always "bearer")
        expires_in: Access token expiration time in seconds
    """

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(
        description="Access token expiration time in seconds (900 = 15 minutes)"
    )


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
        expires_in: Access token expiration time in seconds
    """

    access_token: str = Field(description="New JWT access token")
    refresh_token: str = Field(description="New JWT refresh token (rotated)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(
        description="Access token expiration time in seconds (900 = 15 minutes)"
    )


class LogoutRequest(BaseModel):
    """
    Schema for logout request.

    Attributes:
        refresh_token: JWT refresh token to revoke
    """

    refresh_token: str = Field(description="JWT refresh token to revoke")