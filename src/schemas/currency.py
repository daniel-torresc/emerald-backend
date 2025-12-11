"""
Currency schemas for ISO 4217 currency data.

This module provides Pydantic schemas for:
- Currency model (code, symbol, name)
- Response schemas for currency endpoints
"""

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


class CurrencyResponse(BaseModel):
    """Response schema for single currency."""

    currency: Currency = Field(description="Currency data")


class CurrenciesResponse(BaseModel):
    """Response schema for currency list."""

    currencies: list[Currency] = Field(description="List of supported currencies")
