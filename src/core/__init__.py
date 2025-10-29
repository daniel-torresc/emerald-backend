"""
Core module for Emerald Finance Platform.

Exports the main configuration, database, security, and logging components.
"""

from src.core.config import settings
from src.core.database import (
    AsyncSessionLocal,
    check_database_connection,
    close_database_connection,
    engine,
    get_db,
)
from src.core.logging import get_logger, setup_logging
from src.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    validate_password_strength,
    verify_password,
    verify_refresh_token_hash,
    verify_token_type,
)

__all__ = [
    # Config
    "settings",
    # Database
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "check_database_connection",
    "close_database_connection",
    # Logging
    "setup_logging",
    "get_logger",
    # Security - Password
    "hash_password",
    "verify_password",
    "validate_password_strength",
    # Security - JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token_type",
    "TOKEN_TYPE_ACCESS",
    "TOKEN_TYPE_REFRESH",
    # Security - Refresh Token
    "hash_refresh_token",
    "verify_refresh_token_hash",
]
