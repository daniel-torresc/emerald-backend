"""
Currency service for ISO 4217 currency data.

This module provides:
- Currency Pydantic model for type-safe currency representation
- CurrencyService singleton for managing currency list
- Helper function for easy service access
"""

from typing import ClassVar

from pydantic import BaseModel, Field


class Currency(BaseModel):
    """
    ISO 4217 currency representation.

    Immutable Pydantic model for currency data with validation.
    """

    code: str = Field(min_length=3, max_length=3, description="ISO 4217 currency code")
    symbol: str = Field(min_length=1, description="Currency symbol")
    name: str = Field(min_length=1, description="Full currency name")

    model_config = {"frozen": True}  # Immutable for thread safety

    @classmethod
    def create(cls, code: str, symbol: str, name: str) -> "Currency":
        """
        Factory method for creating currency instances.

        Args:
            code: ISO 4217 code (converted to uppercase)
            symbol: Currency symbol
            name: Full currency name

        Returns:
            Currency instance
        """
        return cls(code=code.upper(), symbol=symbol, name=name)


class CurrencyService:
    """
    Currency service providing ISO 4217 currency data.

    Singleton pattern ensures single instance of currency list in memory.
    Thread-safe due to Python's __new__ implementation and immutable currencies.
    """

    _instance: ClassVar["CurrencyService | None"] = None
    _currencies: list[Currency]

    def __new__(cls) -> "CurrencyService":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_currencies()
        return cls._instance

    def _initialize_currencies(self) -> None:
        """Initialize currency list. Called once on first instantiation."""
        self._currencies = [
            # North America
            Currency.create("USD", "$", "US Dollar"),
            # Europe
            Currency.create("EUR", "€", "Euro"),
            Currency.create("GBP", "£", "Pound Sterling"),
            Currency.create("CHF", "CHF", "Swiss Franc"),
            # Asia-Pacific
            Currency.create("JPY", "¥", "Japanese Yen"),
            Currency.create("CNY", "¥", "Chinese Yuan"),
        ]

    def get_all(self) -> list[Currency]:
        """
        Get all supported currencies.

        Returns:
            Copy of currency list to prevent external modification
        """
        return self._currencies.copy()

    def get_by_code(self, code: str) -> Currency | None:
        """
        Get currency by ISO 4217 code (case-insensitive).

        Args:
            code: ISO 4217 currency code

        Returns:
            Currency if found, None otherwise
        """
        code_upper = code.upper()
        return next((c for c in self._currencies if c.code == code_upper), None)

    def is_supported(self, code: str) -> bool:
        """
        Check if currency code is supported.

        Args:
            code: ISO 4217 currency code

        Returns:
            True if currency is supported, False otherwise
        """
        return self.get_by_code(code) is not None


def get_currency_service() -> CurrencyService:
    """
    Get singleton instance of CurrencyService.

    Convenience function for easy access to currency service.

    Returns:
        CurrencyService singleton instance
    """
    return CurrencyService()
