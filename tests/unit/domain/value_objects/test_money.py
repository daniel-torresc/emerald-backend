"""Unit tests for Money value object."""

from decimal import Decimal

import pytest

from app.domain.exceptions import CurrencyMismatchError, InvalidMoneyError
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.money import Money


class TestMoneyCreation:
    """Test Money value object creation."""

    def test_create_money_with_decimal(self):
        """Test creating money with Decimal amount."""
        money = Money(amount=Decimal("100.50"), currency=Currency.USD)
        assert money.amount == Decimal("100.50")
        assert money.currency == Currency.USD

    def test_create_money_with_int(self):
        """Test creating money with int amount."""
        money = Money(amount=100, currency=Currency.USD)
        assert money.amount == Decimal("100.00")

    def test_create_money_with_float(self):
        """Test creating money with float amount."""
        money = Money(amount=100.50, currency=Currency.USD)
        assert money.amount == Decimal("100.50")

    def test_create_money_with_string(self):
        """Test creating money with string amount."""
        money = Money(amount="100.50", currency=Currency.USD)  # type: ignore
        assert money.amount == Decimal("100.50")

    def test_money_rounded_to_two_decimals(self):
        """Test money is rounded to 2 decimal places."""
        money = Money(amount=Decimal("100.999"), currency=Currency.USD)
        assert money.amount == Decimal("101.00")  # Rounds up with ROUND_HALF_UP

    def test_create_money_with_zero(self):
        """Test creating money with zero amount."""
        money = Money(amount=0, currency=Currency.USD)
        assert money.amount == Decimal("0.00")

    def test_create_money_with_negative(self):
        """Test creating money with negative amount."""
        money = Money(amount=-50, currency=Currency.USD)
        assert money.amount == Decimal("-50.00")


class TestMoneyValidation:
    """Test Money validation."""

    def test_invalid_amount_raises_error(self):
        """Test invalid amount raises error."""
        with pytest.raises(InvalidMoneyError):
            Money(amount="invalid", currency=Currency.USD)  # type: ignore


class TestMoneyArithmetic:
    """Test Money arithmetic operations."""

    def test_add_money(self):
        """Test adding two money amounts."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=50, currency=Currency.USD)
        result = money1.add(money2)
        assert result.amount == Decimal("150.00")
        assert result.currency == Currency.USD

    def test_add_money_different_currency_raises_error(self):
        """Test adding money with different currencies raises error."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=50, currency=Currency.EUR)
        with pytest.raises(CurrencyMismatchError):
            money1.add(money2)

    def test_subtract_money(self):
        """Test subtracting money."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=30, currency=Currency.USD)
        result = money1.subtract(money2)
        assert result.amount == Decimal("70.00")

    def test_subtract_more_than_available_gives_negative(self):
        """Test subtracting more than available gives negative."""
        money1 = Money(amount=50, currency=Currency.USD)
        money2 = Money(amount=100, currency=Currency.USD)
        result = money1.subtract(money2)
        assert result.amount == Decimal("-50.00")

    def test_subtract_money_different_currency_raises_error(self):
        """Test subtracting money with different currencies raises error."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=50, currency=Currency.EUR)
        with pytest.raises(CurrencyMismatchError):
            money1.subtract(money2)

    def test_multiply_money(self):
        """Test multiplying money by scalar."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.multiply(2)
        assert result.amount == Decimal("200.00")

    def test_multiply_money_by_decimal(self):
        """Test multiplying money by Decimal."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.multiply(Decimal("1.5"))
        assert result.amount == Decimal("150.00")

    def test_multiply_money_by_float(self):
        """Test multiplying money by float."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.multiply(0.5)
        assert result.amount == Decimal("50.00")

    def test_divide_money(self):
        """Test dividing money by scalar."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.divide(2)
        assert result.amount == Decimal("50.00")

    def test_divide_money_by_decimal(self):
        """Test dividing money by Decimal."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.divide(Decimal("4"))
        assert result.amount == Decimal("25.00")

    def test_divide_by_zero_raises_error(self):
        """Test dividing by zero raises error."""
        money = Money(amount=100, currency=Currency.USD)
        with pytest.raises(InvalidMoneyError):
            money.divide(0)


class TestMoneyComparison:
    """Test Money comparison operations."""

    def test_equal_money_amounts(self):
        """Test equal money amounts."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=100, currency=Currency.USD)
        assert money1 == money2

    def test_different_amounts_not_equal(self):
        """Test different amounts are not equal."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=50, currency=Currency.USD)
        assert money1 != money2

    def test_different_currencies_not_equal(self):
        """Test same amount different currencies not equal."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=100, currency=Currency.EUR)
        assert money1 != money2

    def test_less_than(self):
        """Test less than comparison."""
        money1 = Money(amount=50, currency=Currency.USD)
        money2 = Money(amount=100, currency=Currency.USD)
        assert money1 < money2

    def test_less_than_or_equal(self):
        """Test less than or equal comparison."""
        money1 = Money(amount=50, currency=Currency.USD)
        money2 = Money(amount=100, currency=Currency.USD)
        money3 = Money(amount=50, currency=Currency.USD)
        assert money1 <= money2
        assert money1 <= money3

    def test_greater_than(self):
        """Test greater than comparison."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=50, currency=Currency.USD)
        assert money1 > money2

    def test_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=50, currency=Currency.USD)
        money3 = Money(amount=100, currency=Currency.USD)
        assert money1 >= money2
        assert money1 >= money3

    def test_comparison_different_currency_raises_error(self):
        """Test comparison with different currencies raises error."""
        money1 = Money(amount=100, currency=Currency.USD)
        money2 = Money(amount=50, currency=Currency.EUR)
        with pytest.raises(CurrencyMismatchError):
            _ = money1 < money2


class TestMoneyPredicates:
    """Test Money predicate methods."""

    def test_is_zero(self):
        """Test is_zero method."""
        money = Money(amount=0, currency=Currency.USD)
        assert money.is_zero() is True

    def test_is_zero_false(self):
        """Test is_zero returns False for non-zero."""
        money = Money(amount=100, currency=Currency.USD)
        assert money.is_zero() is False

    def test_is_positive(self):
        """Test is_positive method."""
        money = Money(amount=100, currency=Currency.USD)
        assert money.is_positive() is True

    def test_is_positive_false_for_negative(self):
        """Test is_positive returns False for negative."""
        money = Money(amount=-100, currency=Currency.USD)
        assert money.is_positive() is False

    def test_is_positive_false_for_zero(self):
        """Test is_positive returns False for zero."""
        money = Money(amount=0, currency=Currency.USD)
        assert money.is_positive() is False

    def test_is_negative(self):
        """Test is_negative method."""
        money = Money(amount=-100, currency=Currency.USD)
        assert money.is_negative() is True

    def test_is_negative_false_for_positive(self):
        """Test is_negative returns False for positive."""
        money = Money(amount=100, currency=Currency.USD)
        assert money.is_negative() is False


class TestMoneyTransformations:
    """Test Money transformation methods."""

    def test_abs_positive(self):
        """Test abs of positive money."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.abs()
        assert result.amount == Decimal("100.00")

    def test_abs_negative(self):
        """Test abs of negative money."""
        money = Money(amount=-100, currency=Currency.USD)
        result = money.abs()
        assert result.amount == Decimal("100.00")

    def test_negate_positive(self):
        """Test negate of positive money."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.negate()
        assert result.amount == Decimal("-100.00")

    def test_negate_negative(self):
        """Test negate of negative money."""
        money = Money(amount=-100, currency=Currency.USD)
        result = money.negate()
        assert result.amount == Decimal("100.00")


class TestMoneyStringRepresentation:
    """Test Money string representation."""

    def test_str_format(self):
        """Test __str__ returns formatted string."""
        money = Money(amount=100, currency=Currency.USD)
        assert str(money) == "USD 100.00"

    def test_repr_format(self):
        """Test __repr__ shows class and values."""
        money = Money(amount=100, currency=Currency.USD)
        assert "Money" in repr(money)
        assert "100" in repr(money)
        assert "USD" in repr(money)


class TestMoneyImmutability:
    """Test Money is immutable."""

    def test_cannot_change_amount(self):
        """Test amount cannot be changed."""
        money = Money(amount=100, currency=Currency.USD)
        with pytest.raises(AttributeError):
            money.amount = Decimal("200")  # type: ignore

    def test_cannot_change_currency(self):
        """Test currency cannot be changed."""
        money = Money(amount=100, currency=Currency.USD)
        with pytest.raises(AttributeError):
            money.currency = Currency.EUR  # type: ignore

    def test_operations_return_new_instance(self):
        """Test operations return new instances."""
        money = Money(amount=100, currency=Currency.USD)
        result = money.add(Money(amount=50, currency=Currency.USD))
        assert money.amount == Decimal("100.00")  # Original unchanged
        assert result.amount == Decimal("150.00")
