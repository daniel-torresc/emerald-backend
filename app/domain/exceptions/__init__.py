"""Domain exceptions package."""

from app.domain.exceptions.base import DomainException
from app.domain.exceptions.user_exceptions import (
    InvalidEmailError,
    InvalidPasswordError,
    InvalidUserStateTransitionError,
    InvalidUsernameError,
    UserAlreadyExistsError,
    UserDomainException,
    UserInactiveError,
    UserNotFoundError,
)
from app.domain.exceptions.account_exceptions import (
    AccountAlreadyExistsError,
    AccountDomainException,
    AccountNotFoundError,
    AccountShareError,
    AccountShareExpiredError,
    CurrencyMismatchError,
    InsufficientBalanceError,
    InvalidAccountStateError,
    InvalidMoneyError,
)
from app.domain.exceptions.permission_exceptions import (
    InsufficientPermissionsError,
    InvalidPermissionError,
    InvalidRoleError,
    PermissionDomainException,
    RoleNotFoundError,
    UnauthorizedAccessError,
)

__all__ = [
    # Base
    "DomainException",
    # User exceptions
    "UserDomainException",
    "InvalidEmailError",
    "InvalidUsernameError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "UserInactiveError",
    "InvalidPasswordError",
    "InvalidUserStateTransitionError",
    # Account exceptions
    "AccountDomainException",
    "AccountNotFoundError",
    "AccountAlreadyExistsError",
    "InvalidMoneyError",
    "InsufficientBalanceError",
    "InvalidAccountStateError",
    "CurrencyMismatchError",
    "AccountShareError",
    "AccountShareExpiredError",
    # Permission exceptions
    "PermissionDomainException",
    "InsufficientPermissionsError",
    "UnauthorizedAccessError",
    "InvalidPermissionError",
    "RoleNotFoundError",
    "InvalidRoleError",
]
