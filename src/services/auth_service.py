"""
Authentication service for user registration, login, and token management.

This module provides:
- User registration with email/password
- User login with JWT token generation
- Token refresh with rotation and reuse detection
- Logout with token revocation
- Password change with token invalidation
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_token_type,
)
from models import AuditAction, RefreshToken, User
from repositories import RefreshTokenRepository, UserRepository
from schemas import UserCreate
from services import AuditService

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service class for authentication operations.

    This service handles:
    - User registration
    - Login and token generation
    - Token refresh with rotation
    - Logout and token revocation
    - Password changes

    All methods require an active database session.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AuthService.

        Args:
            session: Async database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.audit_service = AuditService(session)

    async def register(
        self,
        data: UserCreate,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """
        Register a new user and generate authentication tokens.

        This method:
        1. Validates email and username uniqueness
        2. Hashes the password with Argon2id
        3. Creates the user in the database
        4. Generates access and refresh tokens
        5. Stores refresh token hash in database

        Args:
            data: User registration data (email, username, password)
            request_id: Optional request ID for correlation
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Returns:
            Tuple of (User, TokenResponse)

        Raises:
            AlreadyExistsError: If email or username already exists

        Example:
            user, tokens = await auth_service.register(
                UserCreate(
                    email="john@example.com",
                    username="johndoe",
                    password="SecureP@ss123"
                ),
                ip_address="192.168.1.1"
            )
        """
        # Check if email already exists
        if await self.user_repo.email_exists(data.email):
            logger.warning(f"Registration attempted with existing email: {data.email}")
            raise AlreadyExistsError("User with this email")

        # Check if username already exists
        if await self.user_repo.username_exists(data.username):
            logger.warning(
                f"Registration attempted with existing username: {data.username}"
            )
            raise AlreadyExistsError("User with this username")

        # Hash the password
        password_hash = hash_password(data.password)

        # Create user in database
        user = User(
            email=str(data.email),
            username=data.username,
            password_hash=password_hash,
            is_admin=False,  # Regular user by default
        )
        user = await self.user_repo.create(user)
        await self.session.commit()

        logger.info(f"User registered successfully: {user.id} ({user.email})")

        # Log registration
        await self.audit_service.log_event(
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

        return user

    async def login(
        self,
        email: EmailStr,
        password: str,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, datetime]:
        """
        Authenticate user and generate authentication tokens.

        This method:
        1. Validates credentials (email + password)
        2. Updates last login timestamp
        3. Generates access and refresh tokens
        4. Stores refresh token hash in database

        Note: Soft-deleted users are automatically filtered by repository layer.

        Args:
            email: User's email address
            password: User's password (plain text)
            request_id: Optional request ID for correlation
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Returns:
            Tuple of (User, TokenResponse)

        Raises:
            InvalidCredentialsError: If email or password is incorrect

        Example:
            tokens = await auth_service.login(
                email="john@example.com",
                password="SecureP@ss123",
                ip_address="192.168.1.1"
            )
        """
        # Get user by email (soft-deleted users are automatically excluded)
        user = await self.user_repo.get_by_email(email)
        if not user:
            logger.warning(f"Login failed: user not found with email {email}")
            raise InvalidCredentialsError()

        # Verify password
        if not verify_password(password, user.password_hash):
            logger.warning(f"Login failed: invalid password for user {user.id}")
            raise InvalidCredentialsError()

        # Update last login timestamp
        await self.user_repo.update_last_login(user.id)

        # Generate tokens
        access_token, refresh_token = await self._generate_tokens(user=user)
        expires_at = datetime.fromtimestamp(decode_token(access_token)["exp"], UTC)

        await self.session.commit()

        logger.info(f"User logged in successfully: {user.id} ({user.email})")

        # Log successful login
        await self.audit_service.log_login(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
        )

        return access_token, refresh_token, expires_at

    async def refresh_access_token(
        self,
        refresh_token: str,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, datetime]:
        """
        Refresh access token using a refresh token.

        This method implements token rotation for security:
        1. Validates the refresh token JWT
        2. Checks if token exists and is not revoked
        3. Checks if token is expired
        4. **Detects token reuse** - if revoked token is reused, revokes entire family
        5. Revokes the old refresh token
        6. Generates new access and refresh tokens
        7. Stores new refresh token hash

        Token Rotation Security:
        - Each refresh token can only be used once
        - When used, a new refresh token is issued (rotation)
        - If a revoked token is reused, it indicates theft
        - On reuse detection, entire token family is revoked

        Args:
            refresh_token: JWT refresh token
            request_id: Optional request ID for correlation
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Returns:
            AccessTokenResponse with new tokens

        Raises:
            InvalidTokenError: If token is invalid, expired, or revoked
            AuthenticationError: If user is inactive

        Example:
            new_tokens = await auth_service.refresh_access_token(
                refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                ip_address="192.168.1.1"
            )
        """
        # Decode and validate JWT
        try:
            token_data = decode_token(refresh_token)
        except JWTError as e:
            logger.warning(f"Token refresh failed: invalid JWT - {e}")
            raise InvalidTokenError("Invalid refresh token")

        # Verify token type
        if not verify_token_type(token_data, TOKEN_TYPE_REFRESH):
            logger.warning("Token refresh failed: wrong token type")
            raise InvalidTokenError("Token is not a refresh token")

        # Get token from database
        token_hash = hash_refresh_token(refresh_token)
        db_token = await self.token_repo.get_by_token_hash(token_hash)

        if not db_token:
            logger.warning("Token refresh failed: token not found in database")
            raise InvalidTokenError("Invalid refresh token")

        # Check if token is revoked (reuse detection)
        if db_token.is_revoked:
            logger.warning(
                f"Token reuse detected! Revoking entire token family: {db_token.token_family_id}"
            )
            # Revoke entire token family
            await self.token_repo.revoke_token_family(db_token.token_family_id)
            await self.session.commit()
            raise InvalidTokenError("Token has been compromised. Please log in again.")

        # Check if token is expired
        if db_token.expires_at < datetime.now(UTC):
            logger.warning(
                f"Token refresh failed: token expired for user {db_token.user_id}"
            )
            raise InvalidTokenError("Refresh token has expired")

        # Get user (soft-deleted users are automatically excluded by repository)
        user = await self.user_repo.get_by_id(db_token.user_id)
        if not user:
            logger.error(
                f"Token refresh failed: user not found or deleted {db_token.user_id}"
            )
            raise InvalidTokenError("User not found")

        # Revoke old refresh token
        await self.token_repo.revoke_token(db_token.id)

        # Generate new tokens (same token family for rotation tracking)
        access_token, refresh_token = await self._generate_tokens(
            user=user,
            token_family_id=db_token.token_family_id,
        )
        expires_at = datetime.fromtimestamp(decode_token(access_token)["exp"], UTC)

        await self.session.commit()

        logger.info(f"Access token refreshed for user {user.id}")

        # Extract user_id from the new access token for logging
        token_data = decode_token(access_token)
        user_id_str = token_data.get("sub")

        if user_id_str:
            # Log successful token refresh
            await self.audit_service.log_token_refresh(
                user_id=uuid.UUID(user_id_str),
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                success=True,
            )

        logger.info("Token refreshed successfully")

        return access_token, refresh_token, expires_at

    async def logout(
        self,
        refresh_token: str,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Logout user by revoking their refresh token.

        This method:
        1. Decodes the refresh token
        2. Finds the token in the database
        3. Revokes the token (sets is_revoked=True)

        After logout, the refresh token cannot be used to obtain new access tokens.
        The access token will continue to work until it expires (15 minutes).

        Args:
            refresh_token: JWT refresh token to revoke
            request_id: Optional request ID for correlation
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Raises:
            InvalidTokenError: If token is invalid or not found

        Example:
            await auth_service.logout(refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        """
        # Decode token
        try:
            token_data = decode_token(refresh_token)
        except JWTError:
            logger.warning("Logout failed: invalid JWT")
            raise InvalidTokenError("Invalid refresh token")

        # Verify token type
        if not verify_token_type(token_data, TOKEN_TYPE_REFRESH):
            logger.warning("Logout failed: wrong token type")
            raise InvalidTokenError("Token is not a refresh token")

        # Get token from database
        token_hash = hash_refresh_token(refresh_token)
        db_token = await self.token_repo.get_by_token_hash(token_hash)

        if not db_token:
            logger.warning("Logout failed: token not found")
            raise InvalidTokenError("Invalid refresh token")

        # Revoke token
        await self.token_repo.revoke_token(db_token.id)
        await self.session.commit()

        logger.info(f"User logged out: {db_token.user_id}")

        user_id_str = token_data.get("sub")

        # Log logout
        if user_id_str:
            await self.audit_service.log_logout(
                user_id=uuid.UUID(user_id_str),
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Change user's password and revoke all refresh tokens.

        This method:
        1. Verifies current password
        2. Hashes new password with Argon2id
        3. Updates password in database
        4. **Revokes all refresh tokens** (forces re-authentication on all devices)

        Security Note:
        All refresh tokens are revoked to prevent unauthorized access
        if the password change was initiated due to a security concern.

        Args:
            user_id: User's UUID
            current_password: Current password (for verification)
            new_password: New password (will be hashed)
            request_id: Optional request ID for correlation
            ip_address: Client IP address (for audit logging)
            user_agent: Client user agent (for audit logging)

        Raises:
            NotFoundError: If user not found
            InvalidCredentialsError: If current password is incorrect

        Example:
            await auth_service.change_password(
                user_id=user.id,
                current_password="OldP@ss123",
                new_password="NewP@ss456"
            )
        """
        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.error(f"Password change failed: user not found {user_id}")
            raise AuthenticationError("User not found")

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            logger.warning(
                f"Password change failed: invalid current password for user {user_id}"
            )
            raise InvalidCredentialsError("Current password is incorrect")

        # Hash new password
        new_password_hash = hash_password(new_password)

        # Update password
        user.password_hash = new_password_hash
        await self.session.flush()

        # Revoke all refresh tokens (force re-authentication on all devices)
        revoked_count = await self.token_repo.revoke_user_tokens(user_id)
        await self.session.commit()

        logger.info(
            f"Password changed for user {user_id}. Revoked {revoked_count} refresh tokens."
        )

        # Log successful password change
        await self.audit_service.log_password_change(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=True,
        )

    async def _generate_tokens(
        self,
        user: User,
        token_family_id: uuid.UUID | None = None,
    ) -> tuple[str, str]:
        """
        Generate access and refresh tokens for a user.

        This is an internal method used by register, login, and refresh_access_token.

        Args:
            user: User instance
            token_family_id: Existing token family ID (for rotation)

        Returns:
            TokenResponse with access and refresh tokens
        """
        # Generate token family ID if not provided
        if token_family_id is None:
            token_family_id = uuid.uuid4()

        # Create access token
        access_token = create_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
            },
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
            token_type=TOKEN_TYPE_ACCESS,
        )
        expires_at = datetime.fromtimestamp(decode_token(access_token)["exp"], UTC)

        # Create refresh token
        refresh_token = create_token(
            data={
                "sub": str(user.id),
                "token_family_id": str(token_family_id),
            },
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
            token_type=TOKEN_TYPE_REFRESH,
        )

        # Store refresh token hash in database
        refresh_token_hash = hash_refresh_token(refresh_token)

        token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            token_family_id=token_family_id,
            expires_at=expires_at,
        )
        await self.token_repo.create(token)

        return (
            access_token,
            refresh_token,
        )
