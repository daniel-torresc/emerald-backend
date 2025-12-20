"""
Unit tests for exception handlers.

Tests cover:
- AppException handler response format
- Validation error handler formatting
- General exception handler (debug vs production)
- Rate limit handler response format
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from core.exceptions import AppException, NotFoundError
from core.handlers import (
    app_exception_handler,
    general_exception_handler,
    rate_limit_handler,
    validation_exception_handler,
)


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock request with request_id in state."""
    request = MagicMock(spec=Request)
    request.state.request_id = "test-request-123"
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_request_no_id() -> MagicMock:
    """Create a mock request without request_id."""
    request = MagicMock(spec=Request)
    request.state = MagicMock(spec=[])  # No request_id attribute
    request.client.host = "127.0.0.1"
    return request


class TestAppExceptionHandler:
    """Tests for app_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_correct_status_code(self, mock_request: MagicMock) -> None:
        """Handler returns the exception's status code."""
        exc = NotFoundError(resource="User")
        response = await app_exception_handler(mock_request, exc)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_correct_json_structure(
        self, mock_request: MagicMock
    ) -> None:
        """Handler returns properly structured JSON response."""
        exc = AppException(
            message="Test error",
            status_code=400,
            error_code="TEST_ERROR",
            details={"field": "value"},
        )
        response = await app_exception_handler(mock_request, exc)

        body = json.loads(response.body)

        assert body["error"]["code"] == "TEST_ERROR"
        assert body["error"]["message"] == "Test error"
        assert body["error"]["details"] == {"field": "value"}
        assert body["meta"]["request_id"] == "test-request-123"

    @pytest.mark.asyncio
    async def test_handles_missing_request_id(
        self, mock_request_no_id: MagicMock
    ) -> None:
        """Handler works when request_id is not set."""
        exc = NotFoundError(resource="User")
        response = await app_exception_handler(mock_request_no_id, exc)

        body = json.loads(response.body)

        assert body["meta"]["request_id"] is None


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_422_status(self, mock_request: MagicMock) -> None:
        """Handler returns 422 Unprocessable Entity."""
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = []

        response = await validation_exception_handler(mock_request, exc)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_formats_validation_errors(self, mock_request: MagicMock) -> None:
        """Handler formats validation errors correctly."""
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {"loc": ("body", "email"), "msg": "Invalid email", "type": "value_error"},
            {"loc": ("body", "password"), "msg": "Too short", "type": "value_error"},
        ]

        response = await validation_exception_handler(mock_request, exc)

        body = json.loads(response.body)

        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert len(body["error"]["details"]) == 2
        assert body["error"]["details"][0]["field"] == "body.email"
        assert body["error"]["details"][0]["message"] == "Invalid email"


class TestGeneralExceptionHandler:
    """Tests for general_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status(self, mock_request: MagicMock) -> None:
        """Handler returns 500 Internal Server Error."""
        exc = RuntimeError("Something went wrong")

        with patch("core.handlers.settings") as mock_settings:
            mock_settings.debug = False
            response = await general_exception_handler(mock_request, exc)

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_hides_details_in_production(self, mock_request: MagicMock) -> None:
        """Handler hides exception details when debug is False."""
        exc = RuntimeError("Sensitive database error")

        with patch("core.handlers.settings") as mock_settings:
            mock_settings.debug = False
            response = await general_exception_handler(mock_request, exc)

        body = json.loads(response.body)

        assert "Sensitive database error" not in body["error"]["message"]
        assert "contact support" in body["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_shows_details_in_debug(self, mock_request: MagicMock) -> None:
        """Handler shows exception details when debug is True."""
        exc = RuntimeError("Debug error message")

        with patch("core.handlers.settings") as mock_settings:
            mock_settings.debug = True
            response = await general_exception_handler(mock_request, exc)

        body = json.loads(response.body)

        assert body["error"]["message"] == "Debug error message"


class TestRateLimitHandler:
    """Tests for rate_limit_handler."""

    @pytest.mark.asyncio
    async def test_returns_429_status(self, mock_request: MagicMock) -> None:
        """Handler returns 429 Too Many Requests."""
        exc = MagicMock(spec=RateLimitExceeded)
        response = await rate_limit_handler(mock_request, exc)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_returns_correct_error_code(self, mock_request: MagicMock) -> None:
        """Handler returns RATE_LIMIT_EXCEEDED error code."""
        exc = MagicMock(spec=RateLimitExceeded)
        response = await rate_limit_handler(mock_request, exc)

        body = json.loads(response.body)

        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_handles_missing_client(self) -> None:
        """Handler works when request.client is None."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-123"
        request.client = None

        exc = MagicMock(spec=RateLimitExceeded)
        response = await rate_limit_handler(request, exc)

        assert response.status_code == 429
