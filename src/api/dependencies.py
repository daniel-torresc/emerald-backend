"""
FastAPI dependencies for authentication and authorization.

This module provides:
- Current user extraction from JWT
- Active user verification
- Admin role checking
- Permission-based access control
- Database session management
"""

import logging
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import TOKEN_TYPE_ACCESS, decode_token, verify_token_type
from src.models.user import User
from src.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI - this adds the padlock icon
security = HTTPBearer(
    scheme_name="Bearer",
    description="Enter your JWT access token",
    auto_error=False,
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to extract and validate current user from JWT access token.

    This dependency:
    1. Extracts Bearer token from Authorization header
    2. Decodes and validates JWT
    3. Verifies token is an access token (not refresh token)
    4. Retrieves user from database
    5. Returns User instance

    Args:
        credentials: HTTP Bearer credentials from security scheme
        db: Database session

    Returns:
        User instance of authenticated user

    Raises:
        HTTPException (401): If token is missing, invalid, or user not found

    Usage:
        @app.get("/api/v1/profile")
        async def get_profile(
            current_user: User = Depends(get_current_user)
        ):
            return {"email": current_user.email}
    """
    # Check if credentials are present
    if not credentials:
        logger.warning("Authentication failed: missing Bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Decode and validate token
    try:
        token_data = decode_token(token)
    except JWTError as e:
        logger.warning(f"Authentication failed: invalid JWT - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type (must be access token)
    if not verify_token_type(token_data, TOKEN_TYPE_ACCESS):
        logger.warning("Authentication failed: wrong token type")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id_str = token_data.get("sub")
    if not user_id_str:
        logger.warning("Authentication failed: missing user ID in token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse user ID
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        logger.warning(f"Authentication failed: invalid user ID format - {user_id_str}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_with_roles(user_id)

    if not user:
        logger.warning(f"Authentication failed: user not found - {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure user is active (not deactivated/banned).

    This dependency extends get_current_user by verifying the user
    account is active.

    Args:
        current_user: Current authenticated user

    Returns:
        User instance (guaranteed to be active)

    Raises:
        HTTPException (403): If user account is inactive

    Usage:
        @app.post("/api/v1/transactions")
        async def create_transaction(
            current_user: User = Depends(require_active_user)
        ):
            # Only active users can create transactions
            pass
    """
    if not current_user.is_active:
        logger.warning(f"Access denied: inactive user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    return current_user


async def require_admin(
    current_user: User = Depends(require_active_user),
) -> User:
    """
    Dependency to ensure user has admin privileges.

    This dependency extends require_active_user by verifying the user
    has superuser/admin status.

    Args:
        current_user: Current authenticated user (must be active)

    Returns:
        User instance (guaranteed to be active admin)

    Raises:
        HTTPException (403): If user is not an admin

    Usage:
        @app.get("/api/v1/admin/users")
        async def list_all_users(
            current_user: User = Depends(require_admin)
        ):
            # Only admins can list all users
            pass
    """
    if not current_user.is_admin:
        logger.warning(
            f"Access denied: user {current_user.id} attempted admin-only action"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )

    return current_user


def require_permission(permission: str):
    """
    Dependency factory to check for specific permissions.

    This creates a dependency that verifies the user has a specific
    permission based on their roles.

    Permission format: resource:action[:scope]
    Examples:
    - "users:read:self" - Read own user data
    - "users:read:all" - Read all users' data
    - "transactions:write:all" - Write any transaction
    - "audit_logs:read:all" - Read all audit logs

    Args:
        permission: Required permission string

    Returns:
        Dependency function that checks for the permission

    Raises:
        HTTPException (403): If user lacks the required permission

    Usage:
        @app.delete("/api/v1/users/{user_id}")
        async def delete_user(
            user_id: int,
            current_user: User = Depends(require_permission("users:delete:all"))
        ):
            # Only users with "users:delete:all" permission can delete users
            pass
    """

    async def _check_permission(
        current_user: User = Depends(require_active_user),
    ) -> User:
        """Check if user has required permission."""
        # Admin users have all permissions
        if current_user.is_admin:
            return current_user

        # Check if user has the permission in any of their roles
        user_permissions = set()
        for role in current_user.roles:
            if role.permissions:
                user_permissions.update(role.permissions)

        if permission not in user_permissions:
            logger.warning(
                f"Access denied: user {current_user.id} lacks permission '{permission}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )

        return current_user

    return _check_permission


# ============================================================================
# Service Dependencies
# ============================================================================


def get_auth_service(db: AsyncSession = Depends(get_db)):
    """
    Dependency to get AuthService instance.

    This dependency provides an AuthService with an active database session.

    Args:
        db: Database session

    Returns:
        AuthService instance

    Usage:
        @app.post("/api/v1/auth/login")
        async def login(
            auth_service: AuthService = Depends(get_auth_service)
        ):
            user, tokens = await auth_service.login(...)
    """
    from src.services.auth_service import AuthService

    return AuthService(db)


def get_user_service(db: AsyncSession = Depends(get_db)):
    """
    Dependency to get UserService instance.

    This dependency provides a UserService with an active database session.

    Args:
        db: Database session

    Returns:
        UserService instance

    Usage:
        @app.get("/api/v1/users/me")
        async def get_profile(
            user_service: UserService = Depends(get_user_service)
        ):
            return await user_service.get_user_profile(...)
    """
    from src.services.user_service import UserService

    return UserService(db)


def get_audit_service(db: AsyncSession = Depends(get_db)):
    """
    Dependency to get AuditService instance.

    This dependency provides an AuditService with an active database session.

    Args:
        db: Database session

    Returns:
        AuditService instance

    Usage:
        @app.post("/api/v1/actions")
        async def perform_action(
            audit_service: AuditService = Depends(get_audit_service)
        ):
            await audit_service.log_event(...)
    """
    from src.services.audit_service import AuditService

    return AuditService(db)


def get_account_service(db: AsyncSession = Depends(get_db)):
    """
    Dependency to get AccountService instance.

    This dependency provides an AccountService with an active database session.

    Args:
        db: Database session

    Returns:
        AccountService instance

    Usage:
        @app.post("/api/v1/accounts")
        async def create_account(
            account_service: AccountService = Depends(get_account_service)
        ):
            return await account_service.create_account(...)
    """
    from src.services.account_service import AccountService

    return AccountService(db)


def get_admin_service(db: AsyncSession = Depends(get_db)):
    """
    Dependency to get AdminService instance.

    This dependency provides an AdminService with an active database session.

    Args:
        db: Database session

    Returns:
        AdminService instance

    Usage:
        @app.post("/api/v1/admin/users")
        async def create_admin_user(
            admin_service: AdminService = Depends(get_admin_service)
        ):
            return await admin_service.create_admin_user(...)
    """
    from src.services.admin_service import AdminService

    return AdminService(db)


def get_transaction_service(db: AsyncSession = Depends(get_db)):
    """
    Dependency to get TransactionService instance.

    This dependency provides a TransactionService with an active database session.

    Args:
        db: Database session

    Returns:
        TransactionService instance

    Usage:
        @app.post("/api/v1/accounts/{account_id}/transactions")
        async def create_transaction(
            transaction_service: TransactionService = Depends(get_transaction_service)
        ):
            return await transaction_service.create_transaction(...)
    """
    from src.services.transaction_service import TransactionService

    return TransactionService(db)


# Convenience type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(require_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]