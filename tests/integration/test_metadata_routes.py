"""
Integration tests for metadata API endpoints.

Tests the metadata routes to ensure:
- All endpoints return correct status codes
- Response format matches schemas
- Data is accurate and complete
"""

import pytest
from httpx import AsyncClient


class TestAccountTypesEndpoint:
    """Test cases for GET /api/metadata/account-types"""

    @pytest.mark.asyncio
    async def test_get_account_types_success(self, async_client: AsyncClient):
        """Test GET /api/metadata/account-types returns 200."""
        response = await async_client.get("/api/metadata/account-types")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_account_types_response_structure(
        self, async_client: AsyncClient
    ):
        """Test that response matches expected schema."""
        response = await async_client.get("/api/metadata/account-types")
        data = response.json()

        # Check top-level structure
        assert "account_types" in data
        assert isinstance(data["account_types"], list)

    @pytest.mark.asyncio
    async def test_get_account_types_contains_all_types(
        self, async_client: AsyncClient
    ):
        """Test that response contains all expected account types."""
        response = await async_client.get("/api/metadata/account-types")
        data = response.json()

        account_types = data["account_types"]
        assert len(account_types) == 4

        # Extract keys
        keys = [item["key"] for item in account_types]
        assert "checking" in keys
        assert "savings" in keys
        assert "investment" in keys
        assert "other" in keys

    @pytest.mark.asyncio
    async def test_get_account_types_item_structure(self, async_client: AsyncClient):
        """Test that each account type has correct structure."""
        response = await async_client.get("/api/metadata/account-types")
        data = response.json()

        for item in data["account_types"]:
            assert "key" in item
            assert "label" in item
            assert isinstance(item["key"], str)
            assert isinstance(item["label"], str)
            assert len(item["key"]) > 0
            assert len(item["label"]) > 0

    @pytest.mark.asyncio
    async def test_get_account_types_labels_are_capitalized(
        self, async_client: AsyncClient
    ):
        """Test that labels are properly capitalized."""
        response = await async_client.get("/api/metadata/account-types")
        data = response.json()

        labels = [item["label"] for item in data["account_types"]]
        assert "Checking" in labels
        assert "Savings" in labels
        assert "Investment" in labels
        assert "Other" in labels


class TestCurrenciesEndpoint:
    """Test cases for GET /api/metadata/currencies"""

    @pytest.mark.asyncio
    async def test_get_currencies_success(self, async_client: AsyncClient):
        """Test GET /api/metadata/currencies returns 200."""
        response = await async_client.get("/api/metadata/currencies")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_currencies_response_structure(self, async_client: AsyncClient):
        """Test that response matches expected schema."""
        response = await async_client.get("/api/metadata/currencies")
        data = response.json()

        # Check top-level structure
        assert "currencies" in data
        assert isinstance(data["currencies"], list)

    @pytest.mark.asyncio
    async def test_get_currencies_has_minimum_currencies(
        self, async_client: AsyncClient
    ):
        """Test that response contains minimum expected currencies."""
        response = await async_client.get("/api/metadata/currencies")
        data = response.json()

        currencies = data["currencies"]
        assert len(currencies) >= 6  # At least 6 major currencies

    @pytest.mark.asyncio
    async def test_get_currencies_item_structure(self, async_client: AsyncClient):
        """Test that each currency has correct structure."""
        response = await async_client.get("/api/metadata/currencies")
        data = response.json()

        for currency in data["currencies"]:
            assert "code" in currency
            assert "symbol" in currency
            assert "name" in currency
            assert isinstance(currency["code"], str)
            assert isinstance(currency["symbol"], str)
            assert isinstance(currency["name"], str)
            assert len(currency["code"]) == 3
            assert len(currency["symbol"]) > 0
            assert len(currency["name"]) > 0

    @pytest.mark.asyncio
    async def test_get_currencies_codes_are_uppercase(self, async_client: AsyncClient):
        """Test that all currency codes are uppercase."""
        response = await async_client.get("/api/metadata/currencies")
        data = response.json()

        for currency in data["currencies"]:
            assert currency["code"].isupper()

    @pytest.mark.asyncio
    async def test_get_currencies_contains_major_currencies(
        self, async_client: AsyncClient
    ):
        """Test that response contains major world currencies."""
        response = await async_client.get("/api/metadata/currencies")
        data = response.json()

        codes = [currency["code"] for currency in data["currencies"]]
        assert "USD" in codes
        assert "EUR" in codes
        assert "GBP" in codes

    @pytest.mark.asyncio
    async def test_get_currencies_no_duplicates(self, async_client: AsyncClient):
        """Test that there are no duplicate currency codes."""
        response = await async_client.get("/api/metadata/currencies")
        data = response.json()

        codes = [currency["code"] for currency in data["currencies"]]
        assert len(codes) == len(set(codes))

    @pytest.mark.asyncio
    async def test_get_currencies_symbols_valid_json(self, async_client: AsyncClient):
        """Test that currency symbols serialize correctly in JSON."""
        response = await async_client.get("/api/metadata/currencies")
        data = response.json()

        # If we can parse the response, symbols are valid JSON/UTF-8
        assert len(data["currencies"]) > 0

        # Check that symbols exist and are non-empty
        for currency in data["currencies"]:
            assert currency["symbol"]


class TestTransactionTypesEndpoint:
    """Test cases for GET /api/metadata/transaction-types"""

    @pytest.mark.asyncio
    async def test_get_transaction_types_success(self, async_client: AsyncClient):
        """Test GET /api/metadata/transaction-types returns 200."""
        response = await async_client.get("/api/metadata/transaction-types")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_transaction_types_response_structure(
        self, async_client: AsyncClient
    ):
        """Test that response matches expected schema."""
        response = await async_client.get("/api/metadata/transaction-types")
        data = response.json()

        # Check top-level structure
        assert "transaction_types" in data
        assert isinstance(data["transaction_types"], list)

    @pytest.mark.asyncio
    async def test_get_transaction_types_contains_all_types(
        self, async_client: AsyncClient
    ):
        """Test that response contains all expected transaction types."""
        response = await async_client.get("/api/metadata/transaction-types")
        data = response.json()

        transaction_types = data["transaction_types"]
        assert len(transaction_types) == 3

        # Extract keys
        keys = [item["key"] for item in transaction_types]
        assert "income" in keys
        assert "expense" in keys
        assert "transfer" in keys

    @pytest.mark.asyncio
    async def test_get_transaction_types_item_structure(
        self, async_client: AsyncClient
    ):
        """Test that each transaction type has correct structure."""
        response = await async_client.get("/api/metadata/transaction-types")
        data = response.json()

        for item in data["transaction_types"]:
            assert "key" in item
            assert "label" in item
            assert isinstance(item["key"], str)
            assert isinstance(item["label"], str)
            assert len(item["key"]) > 0
            assert len(item["label"]) > 0

    @pytest.mark.asyncio
    async def test_get_transaction_types_labels_are_capitalized(
        self, async_client: AsyncClient
    ):
        """Test that labels are properly capitalized."""
        response = await async_client.get("/api/metadata/transaction-types")
        data = response.json()

        labels = [item["label"] for item in data["transaction_types"]]
        assert "Income" in labels
        assert "Expense" in labels
        assert "Transfer" in labels


class TestMetadataEndpointsNoAuth:
    """Test that metadata endpoints don't require authentication."""

    @pytest.mark.asyncio
    async def test_account_types_no_auth_required(self, async_client: AsyncClient):
        """Test that account-types endpoint works without authentication."""
        # Don't include any auth headers
        response = await async_client.get("/api/metadata/account-types")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_currencies_no_auth_required(self, async_client: AsyncClient):
        """Test that currencies endpoint works without authentication."""
        response = await async_client.get("/api/metadata/currencies")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_transaction_types_no_auth_required(self, async_client: AsyncClient):
        """Test that transaction-types endpoint works without authentication."""
        response = await async_client.get("/api/metadata/transaction-types")
        assert response.status_code == 200
