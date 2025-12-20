"""
Core module for Emerald Finance Platform.

Exports the main configuration, database, security, and logging components.
"""

from core.config import settings
from core.database import (
    close_database_connection,
    create_database_engine,
)
from core.encryption import EncryptionService
from core.handlers import (
    app_exception_handler,
    general_exception_handler,
    rate_limit_handler,
    validation_exception_handler,
)
from core.logging import get_logger, setup_logging
from core.security import (
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
    "create_database_engine",
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
    # Security - Encryption
    "EncryptionService",
    # Exception Handlers
    "app_exception_handler",
    "validation_exception_handler",
    "general_exception_handler",
    "rate_limit_handler",
]
