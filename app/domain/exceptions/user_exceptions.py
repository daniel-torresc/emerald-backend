"""User domain exceptions."""

from app.domain.exceptions.base import DomainException


class UserDomainException(DomainException):
    """Base exception for user-related domain errors."""


class InvalidEmailError(UserDomainException):
    """Raised when an email address is invalid."""

    def __init__(self, email: str):
        super().__init__(
            message=f"Invalid email format: {email}",
            code="INVALID_EMAIL"
        )


class InvalidUsernameError(UserDomainException):
    """Raised when a username is invalid."""

    def __init__(self, username: str, reason: str):
        super().__init__(
            message=f"Invalid username '{username}': {reason}",
            code="INVALID_USERNAME"
        )


class UserAlreadyExistsError(UserDomainException):
    """Raised when attempting to create a user that already exists."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"User already exists: {identifier}",
            code="USER_ALREADY_EXISTS"
        )


class UserNotFoundError(UserDomainException):
    """Raised when a user cannot be found."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"User not found: {identifier}",
            code="USER_NOT_FOUND"
        )


class UserInactiveError(UserDomainException):
    """Raised when attempting to perform an operation on an inactive user."""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"User is inactive: {user_id}",
            code="USER_INACTIVE"
        )


class InvalidPasswordError(UserDomainException):
    """Raised when a password does not meet requirements."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid password: {reason}",
            code="INVALID_PASSWORD"
        )


class InvalidUserStateTransitionError(UserDomainException):
    """Raised when attempting an invalid state transition."""

    def __init__(self, current_state: str, attempted_transition: str):
        super().__init__(
            message=f"Cannot {attempted_transition} user in state: {current_state}",
            code="INVALID_USER_STATE_TRANSITION"
        )
