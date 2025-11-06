"""Application layer exceptions."""

from typing import Any, Optional


class ApplicationError(Exception):
    """Base exception for all application layer errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize application error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.details:
            return f"{self.message} (code: {self.error_code}, details: {self.details})"
        return f"{self.message} (code: {self.error_code})"


class NotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        """
        Initialize not found error.

        Args:
            message: Human-readable error message
            resource_type: Type of resource (e.g., 'User', 'Account')
            resource_id: ID of the resource that was not found
        """
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(message, "NOT_FOUND", details)


class AlreadyExistsError(ApplicationError):
    """Raised when attempting to create a resource that already exists."""

    def __init__(
        self,
        message: str = "Resource already exists",
        resource_type: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[str] = None,
    ):
        """
        Initialize already exists error.

        Args:
            message: Human-readable error message
            resource_type: Type of resource (e.g., 'User', 'Account')
            field: Field that has duplicate value
            value: The duplicate value
        """
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if field:
            details["field"] = field
        if value:
            details["value"] = value

        super().__init__(message, "ALREADY_EXISTS", details)


class UnauthorizedError(ApplicationError):
    """Raised when authentication is required but not provided or invalid."""

    def __init__(self, message: str = "Authentication required"):
        """
        Initialize unauthorized error.

        Args:
            message: Human-readable error message
        """
        super().__init__(message, "UNAUTHORIZED")


class ForbiddenError(ApplicationError):
    """Raised when user lacks permission to perform an action."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        """
        Initialize forbidden error.

        Args:
            message: Human-readable error message
            required_permission: Permission that was required
            resource_type: Type of resource being accessed
            resource_id: ID of the resource being accessed
        """
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(message, "FORBIDDEN", details)


class ValidationError(ApplicationError):
    """Raised when application-level validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Human-readable error message
            field: Field that failed validation
            value: Invalid value
            constraint: Constraint that was violated
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if constraint:
            details["constraint"] = constraint

        super().__init__(message, "VALIDATION_ERROR", details)


class ConflictError(ApplicationError):
    """Raised when an operation conflicts with the current state."""

    def __init__(
        self,
        message: str = "Operation conflicts with current state",
        operation: Optional[str] = None,
        current_state: Optional[str] = None,
    ):
        """
        Initialize conflict error.

        Args:
            message: Human-readable error message
            operation: Operation that was attempted
            current_state: Current state that conflicts
        """
        details = {}
        if operation:
            details["operation"] = operation
        if current_state:
            details["current_state"] = current_state

        super().__init__(message, "CONFLICT", details)


class BusinessRuleViolationError(ApplicationError):
    """Raised when a business rule is violated."""

    def __init__(
        self,
        message: str = "Business rule violated",
        rule: Optional[str] = None,
    ):
        """
        Initialize business rule violation error.

        Args:
            message: Human-readable error message
            rule: Name or description of the rule that was violated
        """
        details = {}
        if rule:
            details["rule"] = rule

        super().__init__(message, "BUSINESS_RULE_VIOLATION", details)


class ExternalServiceError(ApplicationError):
    """Raised when an external service call fails."""

    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        """
        Initialize external service error.

        Args:
            message: Human-readable error message
            service: Name of the external service
            status_code: HTTP status code if applicable
        """
        details = {}
        if service:
            details["service"] = service
        if status_code:
            details["status_code"] = status_code

        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)
