"""Unit tests for Currency value object."""

import pytest

from app.domain.value_objects.currency import Currency


class TestCurrency:
    """Test Currency enum."""

    def test_currency_values(self):
        """Test currency enum values."""
        assert Currency.USD.value == "USD"
        assert Currency.EUR.value == "EUR"
        assert Currency.GBP.value == "GBP"

    def test_str_returns_value(self):
        """Test __str__ returns currency code."""
        assert str(Currency.USD) == "USD"

    def test_repr_shows_enum(self):
        """Test __repr__ shows enum name."""
        assert repr(Currency.USD) == "Currency.USD"

    def test_from_string_valid(self):
        """Test from_string with valid code."""
        currency = Currency.from_string("USD")
        assert currency == Currency.USD

    def test_from_string_lowercase(self):
        """Test from_string handles lowercase."""
        currency = Currency.from_string("usd")
        assert currency == Currency.USD

    def test_from_string_invalid_raises_error(self):
        """Test from_string with invalid code raises error."""
        with pytest.raises(ValueError) as exc_info:
            Currency.from_string("INVALID")
        assert "Unsupported currency code" in str(exc_info.value)

    def test_all_currencies_supported(self):
        """Test all supported currencies."""
        currencies = [Currency.USD, Currency.EUR, Currency.GBP, Currency.JPY,
                     Currency.CAD, Currency.AUD, Currency.CHF, Currency.CNY,
                     Currency.MXN, Currency.BRL]
        assert len(currencies) == 10
