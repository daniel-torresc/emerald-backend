"""Account domain exceptions."""

from app.domain.exceptions.base import DomainException


class AccountDomainException(DomainException):
    """Base exception for account-related domain errors."""


class AccountNotFoundError(AccountDomainException):
    """Raised when an account cannot be found."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"Account not found: {identifier}",
            code="ACCOUNT_NOT_FOUND"
        )


class AccountAlreadyExistsError(AccountDomainException):
    """Raised when attempting to create an account that already exists."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"Account already exists: {identifier}",
            code="ACCOUNT_ALREADY_EXISTS"
        )


class InvalidMoneyError(AccountDomainException):
    """Raised when money amount or currency is invalid."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid money value: {reason}",
            code="INVALID_MONEY"
        )


class InsufficientBalanceError(AccountDomainException):
    """Raised when account has insufficient balance for an operation."""

    def __init__(self, account_id: str, required: str, available: str):
        super().__init__(
            message=f"Insufficient balance in account {account_id}: required {required}, available {available}",
            code="INSUFFICIENT_BALANCE"
        )


class InvalidAccountStateError(AccountDomainException):
    """Raised when attempting an operation on an account in invalid state."""

    def __init__(self, account_id: str, reason: str):
        super().__init__(
            message=f"Invalid account state for account {account_id}: {reason}",
            code="INVALID_ACCOUNT_STATE"
        )


class CurrencyMismatchError(AccountDomainException):
    """Raised when attempting operations with mismatched currencies."""

    def __init__(self, currency1: str, currency2: str):
        super().__init__(
            message=f"Currency mismatch: {currency1} != {currency2}",
            code="CURRENCY_MISMATCH"
        )


class AccountShareError(AccountDomainException):
    """Raised when account sharing operation fails."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Account sharing error: {reason}",
            code="ACCOUNT_SHARE_ERROR"
        )


class AccountShareExpiredError(AccountDomainException):
    """Raised when attempting to use an expired account share."""

    def __init__(self, share_id: str):
        super().__init__(
            message=f"Account share has expired: {share_id}",
            code="ACCOUNT_SHARE_EXPIRED"
        )
