"""Account domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.exceptions import (
    CurrencyMismatchError,
    InsufficientBalanceError,
    InvalidAccountStateError,
)
from app.domain.value_objects.money import Money


@dataclass
class Account:
    """
    Account entity representing a financial account.

    An account holds a monetary balance and belongs to a user.
    It can be shared with other users with specific permissions.
    """

    id: UUID
    user_id: UUID  # Owner of the account
    name: str
    description: str | None
    balance: Money
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    shared_with_user_ids: list[UUID] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate account after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Account name cannot be empty")

        if len(self.name) > 100:
            raise ValueError("Account name cannot exceed 100 characters")

        if self.description and len(self.description) > 500:
            raise ValueError("Account description cannot exceed 500 characters")

    def is_owned_by(self, user_id: UUID) -> bool:
        """
        Check if account is owned by the specified user.

        Args:
            user_id: User ID to check

        Returns:
            True if user is the owner
        """
        return self.user_id == user_id

    def is_shared_with(self, user_id: UUID) -> bool:
        """
        Check if account is shared with the specified user.

        Args:
            user_id: User ID to check

        Returns:
            True if account is shared with the user
        """
        return user_id in self.shared_with_user_ids

    def can_be_accessed_by(self, user_id: UUID) -> bool:
        """
        Check if the specified user can access this account.

        A user can access an account if they own it or it's shared with them.

        Args:
            user_id: User ID to check

        Returns:
            True if user can access the account
        """
        return self.is_owned_by(user_id) or self.is_shared_with(user_id)

    def activate(self) -> None:
        """
        Activate this account.

        Raises:
            InvalidAccountStateError: If account is already active
        """
        if self.is_active:
            raise InvalidAccountStateError(
                str(self.id),
                "Account is already active"
            )
        self.is_active = True

    def deactivate(self) -> None:
        """
        Deactivate this account.

        Raises:
            InvalidAccountStateError: If account is already inactive
        """
        if not self.is_active:
            raise InvalidAccountStateError(
                str(self.id),
                "Account is already inactive"
            )
        self.is_active = False

    def update_name(self, new_name: str) -> None:
        """
        Update account name.

        Args:
            new_name: New account name

        Raises:
            ValueError: If name is invalid
        """
        if not new_name or not new_name.strip():
            raise ValueError("Account name cannot be empty")

        if len(new_name) > 100:
            raise ValueError("Account name cannot exceed 100 characters")

        self.name = new_name.strip()

    def update_description(self, new_description: str | None) -> None:
        """
        Update account description.

        Args:
            new_description: New account description or None

        Raises:
            ValueError: If description is too long
        """
        if new_description and len(new_description) > 500:
            raise ValueError("Account description cannot exceed 500 characters")

        self.description = new_description

    def add_funds(self, amount: Money) -> None:
        """
        Add funds to the account balance.

        Args:
            amount: Money to add

        Raises:
            CurrencyMismatchError: If currencies don't match
            ValueError: If amount is negative
        """
        if amount.is_negative():
            raise ValueError("Cannot add negative amount")

        if amount.currency != self.balance.currency:
            raise CurrencyMismatchError(
                self.balance.currency.value,
                amount.currency.value
            )

        self.balance = self.balance.add(amount)

    def subtract_funds(self, amount: Money) -> None:
        """
        Subtract funds from the account balance.

        Args:
            amount: Money to subtract

        Raises:
            CurrencyMismatchError: If currencies don't match
            InsufficientBalanceError: If balance is insufficient
            ValueError: If amount is negative
        """
        if amount.is_negative():
            raise ValueError("Cannot subtract negative amount")

        if amount.currency != self.balance.currency:
            raise CurrencyMismatchError(
                self.balance.currency.value,
                amount.currency.value
            )

        if self.balance < amount:
            raise InsufficientBalanceError(
                str(self.id),
                str(amount),
                str(self.balance)
            )

        self.balance = self.balance.subtract(amount)

    def set_balance(self, new_balance: Money) -> None:
        """
        Set account balance directly.

        This should be used with caution and typically only for
        administrative corrections or initial setup.

        Args:
            new_balance: New balance to set

        Raises:
            CurrencyMismatchError: If currencies don't match
        """
        if new_balance.currency != self.balance.currency:
            raise CurrencyMismatchError(
                self.balance.currency.value,
                new_balance.currency.value
            )

        self.balance = new_balance

    def has_sufficient_balance(self, amount: Money) -> bool:
        """
        Check if account has sufficient balance.

        Args:
            amount: Amount to check

        Returns:
            True if balance is sufficient

        Raises:
            CurrencyMismatchError: If currencies don't match
        """
        if amount.currency != self.balance.currency:
            raise CurrencyMismatchError(
                self.balance.currency.value,
                amount.currency.value
            )

        return self.balance >= amount

    def share_with_user(self, user_id: UUID) -> None:
        """
        Share this account with another user.

        Args:
            user_id: User ID to share with

        Raises:
            ValueError: If trying to share with owner or already shared
        """
        if user_id == self.user_id:
            raise ValueError("Cannot share account with owner")

        if user_id in self.shared_with_user_ids:
            raise ValueError("Account already shared with this user")

        self.shared_with_user_ids.append(user_id)

    def unshare_with_user(self, user_id: UUID) -> None:
        """
        Remove account share with a user.

        Args:
            user_id: User ID to unshare with

        Raises:
            ValueError: If account is not shared with this user
        """
        if user_id not in self.shared_with_user_ids:
            raise ValueError("Account is not shared with this user")

        self.shared_with_user_ids.remove(user_id)

    def is_deleted(self) -> bool:
        """
        Check if account is soft-deleted.

        Returns:
            True if account is deleted
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """
        Soft delete this account.

        Raises:
            InvalidAccountStateError: If account is already deleted
        """
        if self.is_deleted():
            raise InvalidAccountStateError(
                str(self.id),
                "Account is already deleted"
            )
        self.deleted_at = datetime.utcnow()
        self.is_active = False

    def __eq__(self, other: object) -> bool:
        """Entity equality based on identity (id), not value."""
        if not isinstance(other, Account):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity."""
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"Account(id={self.id}, name={self.name!r}, "
            f"balance={self.balance}, owner={self.user_id})"
        )
