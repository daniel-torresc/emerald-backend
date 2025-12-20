"""
Security utilities for authentication and authorization.

This module provides:
- Password hashing with Argon2id (NIST-recommended, OWASP 2025 standard)
- JWT token generation and validation (access and refresh tokens)
- Refresh token hashing with SHA-256
- Password strength validation
"""

import hashlib
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from jose import JWTError, jwt

from core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Password Hashing with Argon2id
# =============================================================================
# Argon2id is the NIST-recommended algorithm (2025) for password hashing.
# It's memory-hard (64MB vs bcrypt's 4KB), resistant to GPU/ASIC attacks,
# and recommended by OWASP for all new implementations.
# =============================================================================

pwd_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,  # 2 iterations
    memory_cost=settings.argon2_memory_cost,  # 64 MB memory
    parallelism=settings.argon2_parallelism,  # 4 parallel threads
    hash_len=32,  # 32-byte output
    salt_len=16,  # 16-byte salt
)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.

    Argon2id configuration:
    - time_cost=2: 2 iterations
    - memory_cost=65536: 64 MB memory usage
    - parallelism=4: 4 parallel threads
    - hash_len=32: 32-byte output hash
    - salt_len=16: 16-byte random salt

    Args:
        password: Plain text password to hash

    Returns:
        Argon2id hash string (includes algorithm, parameters, salt, and hash)

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> # Returns: $argon2id$v=19$m=65536,t=2,p=4$...
    """
    return pwd_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against an Argon2id hash.

    Args:
        password: Plain text password to verify
        hashed_password: Argon2id hash to verify against

    Returns:
        True if password matches hash, False otherwise

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    try:
        pwd_hasher.verify(hashed_password, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """
    Validate password strength against security requirements.

    Requirements (per research - financial app standards):
    - Minimum 8 characters (configurable, 12+ recommended for production)
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Example:
        >>> validate_password_strength("weak")
        (False, "Password must be at least 8 characters long")
        >>> validate_password_strength("StrongP@ss123")
        (True, None)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        return False, "Password must contain at least one special character"

    return True, None


# =============================================================================
# JWT Token Management
# =============================================================================
# Access tokens: Short-lived (15 min), used for API authentication
# Refresh tokens: Long-lived (7 days), used to issue new access tokens
# Token rotation: Refresh tokens are rotated on use for security
# =============================================================================

# JWT algorithm
ALGORITHM = "HS256"

# Token types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Access tokens are short-lived (default: 15 minutes) and used for
    API authentication. They contain user_id and permissions.

    Args:
        data: Dictionary of claims to encode in the token
              Must contain 'sub' (subject, typically user_id)
        expires_delta: Optional custom expiration time. If None,
                      uses settings.access_token_expire_minutes

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": "user_123", "role": "admin"})
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": TOKEN_TYPE_ACCESS,
            "jti": str(uuid.uuid4()),  # Unique JWT ID to ensure token uniqueness
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens are long-lived (default: 7 days) and used to issue
    new access tokens. They are rotated on every use for security.

    Args:
        data: Dictionary of claims to encode in the token
              Must contain 'sub' (subject, typically user_id)
        expires_delta: Optional custom expiration time. If None,
                      uses settings.refresh_token_expire_days

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_refresh_token(
        ...     {"sub": "user_123", "token_family_id": "family_abc"}
        ... )
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": TOKEN_TYPE_REFRESH,
            "jti": str(uuid.uuid4()),  # Unique JWT ID to prevent hash collisions
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Verifies:
    - Token signature
    - Token expiration
    - Token format

    Args:
        token: JWT token string to decode

    Returns:
        Dictionary of token claims

    Raises:
        JWTError: If token is invalid, expired, or malformed

    Example:
        >>> token = create_access_token({"sub": "user_123"})
        >>> claims = decode_token(token)
        >>> print(claims["sub"])
        user_123
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise


def verify_token_type(token_data: dict[str, Any], expected_type: str) -> bool:
    """
    Verify that a token is of the expected type.

    Args:
        token_data: Decoded token claims
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        True if token type matches, False otherwise

    Example:
        >>> token_data = decode_token(token)
        >>> is_access = verify_token_type(token_data, TOKEN_TYPE_ACCESS)
    """
    return token_data.get("type") == expected_type


# =============================================================================
# Refresh Token Hashing
# =============================================================================
# Refresh tokens are stored in the database as SHA-256 hashes for security.
# This prevents token theft if the database is compromised.
# =============================================================================


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token using SHA-256.

    Refresh tokens are stored in the database as hashes to prevent
    token theft if the database is compromised. SHA-256 is sufficient
    for this purpose (tokens are already cryptographically random).

    Args:
        token: JWT refresh token string

    Returns:
        SHA-256 hash of the token (hex string)

    Example:
        >>> token = create_refresh_token({"sub": "user_123"})
        >>> token_hash = hash_refresh_token(token)
        >>> # Store token_hash in database, not the token itself
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_refresh_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a refresh token against its stored hash.

    Args:
        token: JWT refresh token string
        token_hash: Stored SHA-256 hash

    Returns:
        True if token matches hash, False otherwise

    Example:
        >>> token = create_refresh_token({"sub": "user_123"})
        >>> token_hash = hash_refresh_token(token)
        >>> verify_refresh_token_hash(token, token_hash)
        True
    """
    return hash_refresh_token(token) == token_hash
