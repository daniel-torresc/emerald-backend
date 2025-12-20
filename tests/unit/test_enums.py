"""
Unit tests for enum models.

Tests the TransactionType enum to ensure:
- Correct values are defined
- Helper methods work correctly
- Enum serialization works as expected

Note: AccountType is no longer an enum - it's now a database model (account_types table).
Tests for AccountType functionality should be in test_account_type_model.py or integration tests.
"""

from models.enums import TransactionType


# AccountType enum tests removed - AccountType is now a database model, not an enum
# See Feature 4: Convert account type from enum to foreign key relationship


class TestTransactionType:
    """Test cases for TransactionType enum."""

    def test_transaction_type_values(self):
        """Test that TransactionType has correct values."""
        assert TransactionType.income.value == "income"
        assert TransactionType.expense.value == "expense"
        assert TransactionType.transfer.value == "transfer"

    def test_transaction_type_count(self):
        """Test that TransactionType has exactly 3 values."""
        assert len(list(TransactionType)) == 3

    def test_transaction_type_to_dict_list(self):
        """Test TransactionType.to_dict_list() returns correct format."""
        result = TransactionType.to_dict_list()

        # Check it's a list
        assert isinstance(result, list)
        assert len(result) == 3

        # Check structure of each item
        for item in result:
            assert isinstance(item, dict)
            assert "key" in item
            assert "label" in item
            assert isinstance(item["key"], str)
            assert isinstance(item["label"], str)

        # Check specific values
        keys = [item["key"] for item in result]
        assert "income" in keys
        assert "expense" in keys
        assert "transfer" in keys

        # Check labels are title case
        labels = [item["label"] for item in result]
        assert "Income" in labels
        assert "Expense" in labels
        assert "Transfer" in labels

    def test_transaction_type_string_enum(self):
        """Test that TransactionType is a string enum."""
        assert isinstance(TransactionType.income, str)
        assert TransactionType.income == "income"

    def test_transaction_type_iteration(self):
        """Test that TransactionType can be iterated."""
        transaction_types = list(TransactionType)
        assert len(transaction_types) == 3
        assert TransactionType.income in transaction_types

    def test_transaction_type_dict_list_format(self):
        """Test that to_dict_list returns properly formatted labels."""
        result = TransactionType.to_dict_list()

        # Find the income entry
        income_entry = next(item for item in result if item["key"] == "income")
        assert income_entry["label"] == "Income"

        # Verify all labels are capitalized correctly
        for item in result:
            assert item["label"][0].isupper()
