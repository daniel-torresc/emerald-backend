"""Currency value object."""

from enum import Enum


class Currency(str, Enum):
    """ISO 4217 currency codes supported by the system."""

    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    JPY = "JPY"  # Japanese Yen
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    CHF = "CHF"  # Swiss Franc
    CNY = "CNY"  # Chinese Yuan
    MXN = "MXN"  # Mexican Peso
    BRL = "BRL"  # Brazilian Real

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Currency.{self.name}"

    @classmethod
    def from_string(cls, value: str) -> "Currency":
        """
        Create Currency from string value.

        Args:
            value: Currency code string (e.g., "USD")

        Returns:
            Currency enum value

        Raises:
            ValueError: If currency code is not supported
        """
        try:
            return cls(value.upper())
        except ValueError:
            supported = ", ".join([c.value for c in cls])
            raise ValueError(
                f"Unsupported currency code: {value}. Supported currencies: {supported}"
            )
