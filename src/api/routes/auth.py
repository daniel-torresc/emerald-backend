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

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import ActiveUser
from src.core.config import settings
from src.core.database import get_db
from src.models.audit_log import AuditAction, AuditStatus
from src.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from src.schemas.user import UserCreate, UserPasswordChange, UserResponse
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Initialize rate limiter for this router
limiter = Limiter(key_func=get_remote_address)

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
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user.

    Args:
        user_data: User registration data (email, username, password)
        request: FastAPI request object
        db: Database session

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

    # Create services
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    # Register user
    user, tokens = await auth_service.register(
        user_data=user_data,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Log registration
    await audit_service.log_data_change(
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="user",
        entity_id=user.id,
        new_values={
            "email": user.email,
            "username": user.username,
        },
        description="User registered",
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    await db.commit()

    logger.info(f"User registered: {user.id} ({user.email})")

    # Store tokens in response headers (alternative to body)
    # This is optional - tokens are already in the response body
    # response.headers["X-Access-Token"] = tokens.access_token
    # response.headers["X-Refresh-Token"] = tokens.refresh_token

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
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
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Login and receive authentication tokens.

    Args:
        credentials: Login credentials (email, password)
        request: FastAPI request object
        db: Database session

    Returns:
        TokenResponse with access and refresh tokens

    Raises:
        401: Invalid credentials or inactive account
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    # Create services
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    # Attempt login
    try:
        user, tokens = await auth_service.login(
            email=credentials.email,
            password=credentials.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Log successful login
        await audit_service.log_login(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
        )

        await db.commit()

        logger.info(f"User logged in: {user.id} ({user.email})")

        return tokens

    except Exception as e:
        # Log failed login attempt
        # Note: We don't have user_id for failed attempts, so it's None
        await audit_service.log_event(
            user_id=None,
            action=AuditAction.LOGIN_FAILED,
            entity_type="user",
            description=f"Failed login attempt for {credentials.email}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=AuditStatus.FAILURE,
            error_message=str(e),
        )

        await db.commit()

        logger.warning(f"Failed login attempt for {credentials.email}")

        # Re-raise the exception
        raise


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
    db: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        token_request: Refresh token
        request: FastAPI request object
        db: Database session

    Returns:
        AccessTokenResponse with new access and refresh tokens

    Raises:
        401: Invalid, expired, or revoked refresh token
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    # Create services
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    # Attempt token refresh
    try:
        tokens = await auth_service.refresh_access_token(
            refresh_token=token_request.refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Extract user_id from the new access token for logging
        from src.core.security import decode_token
        token_data = decode_token(tokens.access_token)
        user_id_str = token_data.get("sub")

        if user_id_str:
            import uuid
            user_id = uuid.UUID(user_id_str)

            # Log successful token refresh
            await audit_service.log_token_refresh(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                success=True,
            )

        await db.commit()

        logger.info("Token refreshed successfully")

        return tokens

    except Exception as e:
        # Log failed token refresh
        await audit_service.log_event(
            user_id=None,
            action=AuditAction.TOKEN_REFRESH,
            entity_type="token",
            description="Failed token refresh attempt",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=AuditStatus.FAILURE,
            error_message=str(e),
        )

        await db.commit()

        logger.warning("Failed token refresh attempt")

        # Re-raise the exception
        raise


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
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Logout user by revoking refresh token.

    Args:
        logout_request: Refresh token to revoke
        request: FastAPI request object
        db: Database session

    Raises:
        401: Invalid refresh token
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    # Create services
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    # Extract user_id before logout
    from src.core.security import decode_token
    try:
        token_data = decode_token(logout_request.refresh_token)
        user_id_str = token_data.get("sub")
    except Exception:
        user_id_str = None

    # Logout
    await auth_service.logout(refresh_token=logout_request.refresh_token)

    # Log logout
    if user_id_str:
        import uuid
        user_id = uuid.UUID(user_id_str)
        await audit_service.log_logout(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    await db.commit()

    logger.info("User logged out")


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
    current_user: ActiveUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Change user password.

    Args:
        password_data: Current and new password
        request: FastAPI request object
        current_user: Authenticated user (from dependency)
        db: Database session

    Raises:
        401: Invalid current password
        422: New password doesn't meet requirements
    """
    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    request_id = getattr(request.state, "request_id", None)

    # Create services
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    # Attempt password change
    try:
        await auth_service.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )

        # Log successful password change
        await audit_service.log_password_change(
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
        )

        await db.commit()

        logger.info(f"Password changed for user {current_user.id}")

    except Exception as e:
        # Log failed password change
        await audit_service.log_password_change(
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=False,
            error_message=str(e),
        )

        await db.commit()

        logger.warning(f"Failed password change for user {current_user.id}")

        # Re-raise the exception
        raise