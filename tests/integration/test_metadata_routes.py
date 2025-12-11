"""
Integration tests for metadata API endpoints.

Tests the metadata routes to ensure:
- All endpoints return correct status codes
- Response format matches schemas
- Data is accurate and complete
"""

import pytest
from httpx import AsyncClient


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


class TestMetadataEndpointsNoAuth:
    """Test that metadata endpoints don't require authentication."""

    @pytest.mark.asyncio
    async def test_currencies_no_auth_required(self, async_client: AsyncClient):
        """Test that currencies endpoint works without authentication."""
        response = await async_client.get("/api/metadata/currencies")
        assert response.status_code == 200
