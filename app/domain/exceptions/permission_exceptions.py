"""Permission and authorization domain exceptions."""

from app.domain.exceptions.base import DomainException


class PermissionDomainException(DomainException):
    """Base exception for permission-related domain errors."""


class InsufficientPermissionsError(PermissionDomainException):
    """Raised when a user lacks required permissions."""

    def __init__(self, user_id: str, required_permission: str):
        super().__init__(
            message=f"User {user_id} lacks required permission: {required_permission}",
            code="INSUFFICIENT_PERMISSIONS"
        )


class UnauthorizedAccessError(PermissionDomainException):
    """Raised when a user attempts unauthorized access to a resource."""

    def __init__(self, user_id: str, resource: str):
        super().__init__(
            message=f"User {user_id} is not authorized to access resource: {resource}",
            code="UNAUTHORIZED_ACCESS"
        )


class InvalidPermissionError(PermissionDomainException):
    """Raised when a permission identifier is invalid."""

    def __init__(self, permission: str):
        super().__init__(
            message=f"Invalid permission: {permission}",
            code="INVALID_PERMISSION"
        )


class RoleNotFoundError(PermissionDomainException):
    """Raised when a role cannot be found."""

    def __init__(self, role_identifier: str):
        super().__init__(
            message=f"Role not found: {role_identifier}",
            code="ROLE_NOT_FOUND"
        )


class InvalidRoleError(PermissionDomainException):
    """Raised when a role is invalid or cannot be assigned."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid role: {reason}",
            code="INVALID_ROLE"
        )
