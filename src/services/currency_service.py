"""
Currency service for ISO 4217 currency data.

This module provides:
- CurrencyService for managing currency list
- Injectable service that follows FastAPI dependency patterns
"""

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.currency import Currency


class CurrencyService:
    """
    Currency service providing ISO 4217 currency data.

    Injectable service that provides currency lookup and validation.
    Thread-safe due to immutable Currency models.
    """

    def __init__(self, session: AsyncSession | None = None):
        """
        Initialize CurrencyService.

        Args:
            session: Optional database session (for future use or
                     pattern consistency when used inside other services)
        """
        self.session = session
        self._currencies = self._initialize_currencies()

    def _initialize_currencies(self) -> list[Currency]:
        """
        Initialize currency list.

        Returns:
            List of supported currencies
        """
        return [
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

    def get_supported_codes(self) -> list[str]:
        """
        Get list of supported currency codes.

        Returns:
            List of ISO 4217 currency codes
        """
        return [c.code for c in self._currencies]
