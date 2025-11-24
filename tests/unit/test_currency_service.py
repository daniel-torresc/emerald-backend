"""
Unit tests for currency service.

Tests the CurrencyService singleton and Currency model to ensure:
- Singleton pattern works correctly
- Currency data is valid
- Service methods work as expected
"""

import pytest

from src.services.currency_service import (
    Currency,
    CurrencyService,
    get_currency_service,
)


class TestCurrency:
    """Test cases for Currency Pydantic model."""

    def test_currency_creation(self):
        """Test creating a Currency instance."""
        currency = Currency(code="USD", symbol="$", name="US Dollar")
        assert currency.code == "USD"
        assert currency.symbol == "$"
        assert currency.name == "US Dollar"

    def test_currency_create_factory(self):
        """Test Currency.create() factory method converts code to uppercase."""
        currency = Currency.create("usd", "$", "US Dollar")
        assert currency.code == "USD"
        assert currency.symbol == "$"
        assert currency.name == "US Dollar"

    def test_currency_is_frozen(self):
        """Test that Currency model is immutable (frozen)."""
        currency = Currency(code="USD", symbol="$", name="US Dollar")

        with pytest.raises(
            Exception
        ):  # Pydantic raises ValidationError for frozen models
            currency.code = "EUR"

    def test_currency_validation(self):
        """Test Currency model validation."""
        # Valid currency
        currency = Currency(code="USD", symbol="$", name="US Dollar")
        assert currency.code == "USD"

        # Invalid: code too short
        with pytest.raises(Exception):
            Currency(code="US", symbol="$", name="US Dollar")

        # Invalid: code too long
        with pytest.raises(Exception):
            Currency(code="USDD", symbol="$", name="US Dollar")

        # Invalid: empty symbol
        with pytest.raises(Exception):
            Currency(code="USD", symbol="", name="US Dollar")


class TestCurrencyService:
    """Test cases for CurrencyService singleton."""

    def test_singleton_pattern(self):
        """Test that CurrencyService returns same instance."""
        service1 = CurrencyService()
        service2 = CurrencyService()
        assert service1 is service2

    def test_get_currency_service_returns_singleton(self):
        """Test that get_currency_service() returns singleton instance."""
        service1 = get_currency_service()
        service2 = get_currency_service()
        assert service1 is service2

    def test_get_all_returns_currencies(self):
        """Test that get_all() returns list of currencies."""
        service = get_currency_service()
        currencies = service.get_all()

        assert isinstance(currencies, list)
        assert len(currencies) == 6  # Based on the 6 currencies in the service
        assert all(isinstance(c, Currency) for c in currencies)

    def test_get_all_returns_copy(self):
        """Test that get_all() returns a copy to prevent external modification."""
        service = get_currency_service()
        currencies1 = service.get_all()
        currencies2 = service.get_all()

        # Should be different list objects
        assert currencies1 is not currencies2

        # But should contain same data
        assert len(currencies1) == len(currencies2)

    def test_all_currencies_have_required_fields(self):
        """Test that all currencies have valid code, symbol, and name."""
        service = get_currency_service()
        currencies = service.get_all()

        for currency in currencies:
            assert len(currency.code) == 3
            assert currency.code.isupper()
            assert len(currency.symbol) >= 1
            assert len(currency.name) >= 1

    def test_no_duplicate_currency_codes(self):
        """Test that there are no duplicate currency codes."""
        service = get_currency_service()
        currencies = service.get_all()

        codes = [c.code for c in currencies]
        assert len(codes) == len(set(codes))

    def test_get_by_code_found(self):
        """Test get_by_code() returns currency when found."""
        service = get_currency_service()
        currency = service.get_by_code("USD")

        assert currency is not None
        assert currency.code == "USD"
        assert currency.symbol == "$"
        assert currency.name == "US Dollar"

    def test_get_by_code_case_insensitive(self):
        """Test get_by_code() is case-insensitive."""
        service = get_currency_service()

        usd_upper = service.get_by_code("USD")
        usd_lower = service.get_by_code("usd")
        usd_mixed = service.get_by_code("UsD")

        assert usd_upper is not None
        assert usd_lower is not None
        assert usd_mixed is not None
        assert usd_upper.code == usd_lower.code == usd_mixed.code == "USD"

    def test_get_by_code_not_found(self):
        """Test get_by_code() returns None when not found."""
        service = get_currency_service()
        currency = service.get_by_code("INVALID")

        assert currency is None

    def test_is_supported_true(self):
        """Test is_supported() returns True for valid currency."""
        service = get_currency_service()
        assert service.is_supported("USD") is True
        assert service.is_supported("EUR") is True
        assert service.is_supported("GBP") is True

    def test_is_supported_case_insensitive(self):
        """Test is_supported() is case-insensitive."""
        service = get_currency_service()
        assert service.is_supported("usd") is True
        assert service.is_supported("UsD") is True

    def test_is_supported_false(self):
        """Test is_supported() returns False for invalid currency."""
        service = get_currency_service()
        assert service.is_supported("INVALID") is False
        assert service.is_supported("XXX") is False

    def test_specific_currencies_exist(self):
        """Test that specific expected currencies exist."""
        service = get_currency_service()

        # Test major currencies
        assert service.is_supported("USD")
        assert service.is_supported("EUR")
        assert service.is_supported("GBP")
        assert service.is_supported("JPY")
        assert service.is_supported("CNY")
        assert service.is_supported("CHF")

    def test_currency_symbols_are_valid_utf8(self):
        """Test that all currency symbols are valid UTF-8."""
        service = get_currency_service()
        currencies = service.get_all()

        for currency in currencies:
            # Should not raise exception
            symbol_encoded = currency.symbol.encode("utf-8")
            assert len(symbol_encoded) > 0
