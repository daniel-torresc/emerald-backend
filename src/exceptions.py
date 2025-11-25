"""
Custom exception classes for the Emerald Finance Platform.

This module defines a hierarchy of custom exceptions that map to HTTP status codes
and provide consistent error responses across the API.

Exception hierarchy:
    AppException (base)
    ├── AuthenticationError (401)
    │   ├── InvalidCredentialsError
    │   ├── InvalidTokenError
    │   ├── TokenExpiredError
    │   └── AccountLockedError
    ├── AuthorizationError (403)
    │   └── InsufficientPermissionsError
    ├── ResourceError
    │   ├── NotFoundError (404)
    │   ├── AlreadyExistsError (409)
    │   └── ConflictError (409)
    ├── ValidationError (422)
    │   ├── WeakPasswordError
    │   └── InvalidInputError
    └── RateLimitExceededError (429)
"""

from typing import Any


class AppException(Exception):
    """
    Base exception class for all application exceptions.

    All custom exceptions should inherit from this class to ensure
    consistent error handling and response formatting.

    Attributes:
        status_code: HTTP status code for the error
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize application exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            error_code: Machine-readable error code
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for JSON response.

        Returns:
            Dictionary with error information
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


# =============================================================================
# Authentication Errors (401 Unauthorized)
# =============================================================================


class AuthenticationError(AppException):
    """Base class for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTHENTICATION_FAILED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid email or password",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="INVALID_CREDENTIALS",
            details=details,
        )


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid or malformed."""

    def __init__(
        self,
        message: str = "Invalid or malformed token",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="INVALID_TOKEN",
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            details=details,
        )


class AccountLockedError(AuthenticationError):
    """Raised when an account is locked due to too many failed login attempts."""

    def __init__(
        self,
        message: str = "Account is locked due to too many failed login attempts",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ACCOUNT_LOCKED",
            details=details,
        )


# =============================================================================
# Authorization Errors (403 Forbidden)
# =============================================================================


class AuthorizationError(AppException):
    """Base class for authorization errors."""

    def __init__(
        self,
        message: str = "Access forbidden",
        error_code: str = "AUTHORIZATION_FAILED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            details=details,
        )


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions for an action."""

    def __init__(
        self,
        message: str = "Insufficient permissions to perform this action",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_PERMISSIONS",
            details=details,
        )


class ForbiddenError(AuthorizationError):
    """Raised when an action is forbidden (e.g., violates business rules)."""

    def __init__(
        self,
        message: str = "This action is forbidden",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            details=details,
        )


# =============================================================================
# Resource Errors
# =============================================================================


class ResourceError(AppException):
    """Base class for resource-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )


class NotFoundError(ResourceError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource: str = "Resource",
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if message is None:
            message = f"{resource} not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class AlreadyExistsError(ResourceError):
    """Raised when attempting to create a resource that already exists."""

    def __init__(
        self,
        resource: str = "Resource",
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if message is None:
            message = f"{resource} already exists"
        super().__init__(
            message=message,
            status_code=409,
            error_code="ALREADY_EXISTS",
            details=details,
        )


class ConflictError(ResourceError):
    """Raised when there's a conflict with the current state of the resource."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


# =============================================================================
# Validation Errors (422 Unprocessable Entity)
# =============================================================================


class ValidationError(AppException):
    """Base class for validation errors."""

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code,
            details=details,
        )


class WeakPasswordError(ValidationError):
    """Raised when a password doesn't meet strength requirements."""

    def __init__(
        self,
        message: str = "Password does not meet security requirements",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="WEAK_PASSWORD",
            details=details,
        )


class InvalidInputError(ValidationError):
    """Raised when input data is invalid."""

    def __init__(
        self,
        field: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if message is None and field:
            message = f"Invalid input for field: {field}"
        elif message is None:
            message = "Invalid input"

        super().__init__(
            message=message,
            error_code="INVALID_INPUT",
            details=details,
        )


# =============================================================================
# Rate Limiting Error (429 Too Many Requests)
# =============================================================================


class RateLimitExceededError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if details is None:
            details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


# =============================================================================
# Encryption Error (500 Internal Server Error)
# =============================================================================


class EncryptionError(AppException):
    """Raised when encryption or decryption operations fail."""

    def __init__(
        self,
        message: str = "Encryption operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="ENCRYPTION_ERROR",
            details=details,
        )
