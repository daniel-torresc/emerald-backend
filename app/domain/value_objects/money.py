"""Money value object."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.domain.exceptions import CurrencyMismatchError, InvalidMoneyError
from app.domain.value_objects.currency import Currency


@dataclass(frozen=True)
class Money:
    """
    Money value object with currency.

    Immutable value object representing a monetary amount with currency.
    Uses Decimal for precise arithmetic.
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        """Validate money amount."""
        # Convert amount to Decimal if it's not already
        if not isinstance(self.amount, Decimal):
            try:
                object.__setattr__(self, "amount", Decimal(str(self.amount)))
            except (ValueError, TypeError, Exception) as e:
                raise InvalidMoneyError(f"Invalid amount value: {e}")

        # Round to 2 decimal places (standard for most currencies)
        rounded_amount = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", rounded_amount)

    def __str__(self) -> str:
        return f"{self.currency.value} {self.amount}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency={self.currency})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def __lt__(self, other: "Money") -> bool:
        """Less than comparison (requires same currency)."""
        self._validate_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        """Less than or equal comparison (requires same currency)."""
        self._validate_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        """Greater than comparison (requires same currency)."""
        self._validate_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        """Greater than or equal comparison (requires same currency)."""
        self._validate_same_currency(other)
        return self.amount >= other.amount

    def add(self, other: "Money") -> "Money":
        """
        Add two money amounts (must have same currency).

        Args:
            other: Money to add

        Returns:
            New Money instance with sum

        Raises:
            CurrencyMismatchError: If currencies don't match
        """
        self._validate_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: "Money") -> "Money":
        """
        Subtract other money amount from this one (must have same currency).

        Args:
            other: Money to subtract

        Returns:
            New Money instance with difference

        Raises:
            CurrencyMismatchError: If currencies don't match
        """
        self._validate_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def multiply(self, multiplier: int | float | Decimal) -> "Money":
        """
        Multiply money by a scalar value.

        Args:
            multiplier: Scalar value to multiply by

        Returns:
            New Money instance with product
        """
        if not isinstance(multiplier, Decimal):
            multiplier = Decimal(str(multiplier))
        return Money(amount=self.amount * multiplier, currency=self.currency)

    def divide(self, divisor: int | float | Decimal) -> "Money":
        """
        Divide money by a scalar value.

        Args:
            divisor: Scalar value to divide by

        Returns:
            New Money instance with quotient

        Raises:
            InvalidMoneyError: If divisor is zero
        """
        if not isinstance(divisor, Decimal):
            divisor = Decimal(str(divisor))

        if divisor == 0:
            raise InvalidMoneyError("Cannot divide money by zero")

        return Money(amount=self.amount / divisor, currency=self.currency)

    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == 0

    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > 0

    def is_negative(self) -> bool:
        """Check if amount is negative."""
        return self.amount < 0

    def abs(self) -> "Money":
        """Get absolute value of money."""
        return Money(amount=abs(self.amount), currency=self.currency)

    def negate(self) -> "Money":
        """Get negated value of money."""
        return Money(amount=-self.amount, currency=self.currency)

    def _validate_same_currency(self, other: "Money") -> None:
        """Validate that two Money instances have the same currency."""
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency.value, other.currency.value)
