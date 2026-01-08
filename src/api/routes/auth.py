"""
Authentication API routes.

This module provides REST endpoints for:
- User registration
- User login
- Token refresh
- User logout
- Password change
"""

import logging

from fastapi import APIRouter
from starlette import status
from starlette.requests import Request

from core import settings
from core.rate_limit import limiter
from schemas import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    UserCreate,
    UserPasswordChange,
    UserResponse,
)
from ..dependencies import AuthServiceDep, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Register a new user account with email and password.

    **Password Requirements:**
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character

    **Rate Limit:** Configurable via RATE_LIMIT_REGISTER (default: 3/hour)

    Returns the created user and authentication tokens.
    """,
)
@limiter.limit(settings.rate_limit_register)
async def register(
    data: UserCreate,
    request: Request,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """
    Register a new user.

    Args:
        data: User registration data (email, username, password)
        request: FastAPI request object
        auth_service: Injected AuthService instance

    Returns:
        UserResponse with created user data

    Raises:
        409: Email or username already exists
        422: Password doesn't meet requirements
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    # Register user
    user = await auth_service.register(
        data=data,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description="""
    Authenticate with email and password to receive JWT tokens.

    **Rate Limit:** Configurable via RATE_LIMIT_LOGIN (default: 5/15minute)

    Returns access token (15 min expiry) and refresh token (7 day expiry).
    """,
)
@limiter.limit(settings.rate_limit_login)
async def login(
    credentials: LoginRequest,
    request: Request,
    auth_service: AuthServiceDep,
) -> AccessTokenResponse:
    """
    Login and receive authentication tokens.

    Args:
        credentials: Login credentials (email, password)
        request: FastAPI request object
        auth_service: Injected AuthService instance

    Returns:
        TokenResponse with access and refresh tokens

    Raises:
        401: Invalid credentials or inactive account
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    access_token, refresh_token, expires_at = await auth_service.login(
        email=credentials.email,
        password=credentials.password,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return AccessTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="""
    Use refresh token to obtain new access and refresh tokens.

    **Token Rotation:** The refresh token is rotated on every use.
    The old refresh token is revoked and a new one is issued.

    **Reuse Detection:** If a revoked token is reused, the entire
    token family is revoked for security.

    **Rate Limit:** Configurable via RATE_LIMIT_TOKEN_REFRESH (default: 10/hour)
    """,
)
@limiter.limit(settings.rate_limit_token_refresh)
async def refresh(
    token_request: RefreshTokenRequest,
    request: Request,
    auth_service: AuthServiceDep,
) -> AccessTokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        token_request: Refresh token
        request: FastAPI request object
        auth_service: Injected AuthService instance

    Returns:
        AccessTokenResponse with new access and refresh tokens

    Raises:
        401: Invalid, expired, or revoked refresh token
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    access_token, refresh_token, expires_at = await auth_service.refresh_access_token(
        refresh_token=token_request.refresh_token,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return AccessTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="""
    Revoke refresh token to logout.

    The access token will continue to work until it expires (15 minutes).
    The refresh token is immediately revoked and cannot be used again.
    """,
)
async def logout(
    logout_request: LogoutRequest,
    request: Request,
    auth_service: AuthServiceDep,
) -> None:
    """
    Logout user by revoking refresh token.

    Args:
        logout_request: Refresh token to revoke
        request: FastAPI request object
        auth_service: Injected AuthService instance

    Raises:
        401: Invalid refresh token
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    await auth_service.logout(
        refresh_token=logout_request.refresh_token,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="""
    Change the current user's password.

    **Security:** All refresh tokens are revoked after password change,
    requiring re-authentication on all devices.

    **Rate Limit:** Configurable via RATE_LIMIT_PASSWORD_CHANGE (default: 3/hour)
    """,
)
@limiter.limit(settings.rate_limit_password_change)
async def change_password(
    password_data: UserPasswordChange,
    request: Request,
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> None:
    """
    Change user password.

    Args:
        password_data: Current and new password
        request: FastAPI request object
        current_user: Authenticated user (from dependency)
        auth_service: Injected AuthService instance

    Raises:
        401: Invalid current password
        422: New password doesn't meet requirements
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    await auth_service.change_password(
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
