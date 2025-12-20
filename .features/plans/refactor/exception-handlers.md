# Implementation Plan: Refactor Exception Handlers to Separate Module

## Executive Summary

This refactoring task extracts all exception handler functions from `src/main.py` into a dedicated `src/core/handlers.py` module. The goal is to improve code organization and maintainability by following the same pattern already established for middleware—where handler/middleware logic lives in dedicated modules under `src/core/`, and `main.py` contains only registration calls.

After this refactor, `main.py` will import handler functions from `src/core/handlers.py` and register them with `app.add_exception_handler(ExceptionType, handler_func)` calls, mirroring how middleware is currently organized with `app.add_middleware(MiddlewareClass)`. This is a pure refactoring task with no behavioral changes—all existing exception handling must remain identical.

**Expected outcomes:**
- Cleaner, more focused `main.py` file (~120 lines of handler logic removed)
- All exception handling logic centralized in `src/core/handlers.py`
- Consistent architectural pattern with existing middleware organization
- Zero functional changes to exception handling behavior

## Technical Architecture

### 2.1 System Design Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        src/main.py                              │
│  - FastAPI app setup                                            │
│  - Lifespan context manager                                     │
│  - Exception handler REGISTRATION (not implementation)          │
│      app.add_exception_handler(AppException, app_exception_handler)
│      app.add_exception_handler(RequestValidationError, validation_exception_handler)
│      app.add_exception_handler(Exception, general_exception_handler)
│      app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
│  - Middleware registration                                      │
│  - Route registration                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ imports handler functions
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    src/core/handlers.py (NEW)                   │
│  - app_exception_handler()                                      │
│  - validation_exception_handler()                               │
│  - general_exception_handler()                                  │
│  - rate_limit_handler()                                         │
└─────────────────────────────────────────────────────────────────┘
```

This mirrors the middleware pattern:
```python
# Middleware pattern (current):
from core.middleware import RequestIDMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
...

# Exception handler pattern (after refactor):
from core.handlers import app_exception_handler, validation_exception_handler, ...
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
...
```

### 2.2 Technology Decisions

No new technologies are introduced. This refactoring uses existing FastAPI exception handling patterns.

### 2.3 File Structure

```
src/core/
├── __init__.py          # Update exports to include handlers
├── handlers.py          # NEW: Exception handler functions
├── exceptions.py        # Existing: Custom exception classes
├── middleware.py        # Existing: Middleware classes (pattern reference)
└── ...
```

## Implementation Specification

### 3.1 Component Breakdown

#### Component: Exception Handlers Module

**Files Involved:**
- `src/core/handlers.py` (NEW)
- `src/core/__init__.py` (UPDATE)
- `src/main.py` (UPDATE)

**Purpose:** Centralize all exception handler functions in a dedicated module, keeping `main.py` focused on application wiring and configuration.

**Implementation Requirements:**

1. **Core Logic:**
   - Create `src/core/handlers.py` with all four exception handlers moved verbatim from `main.py`
   - Preserve exact function signatures and implementations
   - Maintain all logging behavior (logger instance, log levels, message formats)
   - Preserve JSON response structure exactly (error code, message, details, meta/request_id)

2. **Handler Functions to Extract:**
   - `app_exception_handler(request: Request, exc: AppException) -> JSONResponse`
   - `validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse`
   - `general_exception_handler(request: Request, exc: Exception) -> JSONResponse`
   - `rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse`

3. **Dependencies:**
   - Internal: `src/core/exceptions.py` (AppException class)
   - Internal: `src/core/config.py` (settings for debug flag)
   - External: `fastapi`, `starlette`, `slowapi.errors`

4. **Testing Requirements:**
   - [ ] Unit test: `app_exception_handler` returns correct status code and JSON structure for AppException
   - [ ] Unit test: `validation_exception_handler` formats Pydantic errors correctly
   - [ ] Unit test: `general_exception_handler` hides details in production (debug=False)
   - [ ] Unit test: `general_exception_handler` shows details in development (debug=True)
   - [ ] Unit test: `rate_limit_handler` returns 429 with correct error structure
   - [ ] Integration test: Existing auth/account tests still pass (indirect handler validation)

**Acceptance Criteria:**
- [ ] All four exception handlers moved to `src/core/handlers.py`
- [ ] `main.py` contains only registration calls (no handler logic)
- [ ] All existing tests pass without modification
- [ ] Response format for all exception types remains unchanged
- [ ] Logging behavior remains unchanged

---

### 3.2 Detailed File Specifications

#### `src/core/handlers.py` (NEW)

**Purpose:** Centralized exception handler functions for the FastAPI application.

**Implementation:**

```python
"""
Exception handlers for FastAPI application.

This module provides:
- Custom application exception handler (AppException)
- Pydantic validation error handler (RequestValidationError)
- General unhandled exception handler (Exception)
- Rate limit exceeded handler (RateLimitExceeded)
"""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from core.config import settings
from core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.

    Converts AppException to proper HTTP responses with consistent format.
    """
    logger.warning(
        f"Application exception: {exc.error_code} - {exc.message} "
        f"(request_id={getattr(request.state, 'request_id', 'unknown')})"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts validation errors to consistent error response format.
    """
    logger.warning(
        f"Validation error: {exc.errors()} "
        f"(request_id={getattr(request.state, 'request_id', 'unknown')})"
    )

    # Format validation errors
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            },
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Logs the full error and returns a generic error response to the client
    (don't expose internal error details in production).
    """
    logger.error(
        f"Unexpected error: {str(exc)} "
        f"(request_id={getattr(request.state, 'request_id', 'unknown')})",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": (
                    "An unexpected error occurred. Please contact support."
                    if not settings.debug
                    else str(exc)
                ),
                "details": {},
            },
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Handle rate limit exceeded errors.

    Returns 429 status with retry information.
    """
    logger.warning(
        f"Rate limit exceeded: {request.client.host if request.client else 'unknown'} "
        f"(request_id={getattr(request.state, 'request_id', 'unknown')})"
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please try again later.",
            },
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )
```

**Edge Cases:**
- When `request.state` has no `request_id`: Returns `'unknown'` for logging, `None` for response
- When `request.client` is None (e.g., test clients): Returns `'unknown'` in rate limit log
- When `settings.debug` is True: Exposes exception details in 500 errors

**Tests:**
- [ ] Test: AppException with all fields produces correct JSON
- [ ] Test: AppException with empty details produces empty dict in response
- [ ] Test: Validation error with multiple fields formats all correctly
- [ ] Test: General exception hides message when debug=False
- [ ] Test: General exception shows message when debug=True
- [ ] Test: Rate limit handler returns 429 status

---

#### `src/core/__init__.py` (UPDATE)

**Purpose:** Export the new handler functions.

**Implementation:** Add to existing exports:

```python
from core.handlers import (
    app_exception_handler,
    general_exception_handler,
    rate_limit_handler,
    validation_exception_handler,
)

__all__ = [
    # ... existing exports ...
    # Handlers
    "app_exception_handler",
    "validation_exception_handler",
    "general_exception_handler",
    "rate_limit_handler",
]
```

---

#### `src/main.py` (UPDATE)

**Purpose:** Replace inline exception handlers with imports and registration calls.

**Changes:**

1. **Remove:** Lines 111-234 (entire Exception Handlers section with all four handler function implementations)

2. **Add imports:**
```python
from core.handlers import (
    app_exception_handler,
    general_exception_handler,
    rate_limit_handler,
    validation_exception_handler,
)
```

3. **Update Exception Handlers section** to contain only registration calls:
```python
# ============================================================================
# Exception Handlers
# ============================================================================
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
```

4. **Keep these imports** (still needed for registration):
   - `from fastapi.exceptions import RequestValidationError`
   - `from slowapi.errors import RateLimitExceeded`
   - `from core.exceptions import AppException`

5. **Remove unused imports:**
   - `from fastapi import status` (only used in handler implementations, not registration)

**After refactoring, the Exception Handlers section in main.py becomes:**
```python
# ============================================================================
# Exception Handlers
# ============================================================================
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
```

This mirrors the Middleware Setup section pattern:
```python
# ============================================================================
# Middleware Setup (Order matters!)
# ============================================================================
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)
app.add_middleware(CORSMiddleware, ...)
```

---

#### `tests/unit/core/test_handlers.py` (NEW)

**Purpose:** Unit tests for exception handler functions.

**Implementation:**

```python
"""
Unit tests for exception handlers.

Tests cover:
- AppException handler response format
- Validation error handler formatting
- General exception handler (debug vs production)
- Rate limit handler response format
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from core.exceptions import AppException, NotFoundError
from core.handlers import (
    app_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    rate_limit_handler,
)


@pytest.fixture
def mock_request():
    """Create a mock request with request_id in state."""
    request = MagicMock(spec=Request)
    request.state.request_id = "test-request-123"
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_request_no_id():
    """Create a mock request without request_id."""
    request = MagicMock(spec=Request)
    request.state = MagicMock(spec=[])  # No request_id attribute
    request.client.host = "127.0.0.1"
    return request


class TestAppExceptionHandler:
    """Tests for app_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_correct_status_code(self, mock_request):
        """Handler returns the exception's status code."""
        exc = NotFoundError(resource="User")
        response = await app_exception_handler(mock_request, exc)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_correct_json_structure(self, mock_request):
        """Handler returns properly structured JSON response."""
        exc = AppException(
            message="Test error",
            status_code=400,
            error_code="TEST_ERROR",
            details={"field": "value"},
        )
        response = await app_exception_handler(mock_request, exc)

        import json
        body = json.loads(response.body)

        assert body["error"]["code"] == "TEST_ERROR"
        assert body["error"]["message"] == "Test error"
        assert body["error"]["details"] == {"field": "value"}
        assert body["meta"]["request_id"] == "test-request-123"

    @pytest.mark.asyncio
    async def test_handles_missing_request_id(self, mock_request_no_id):
        """Handler works when request_id is not set."""
        exc = NotFoundError(resource="User")
        response = await app_exception_handler(mock_request_no_id, exc)

        import json
        body = json.loads(response.body)

        assert body["meta"]["request_id"] is None


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_422_status(self, mock_request):
        """Handler returns 422 Unprocessable Entity."""
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = []

        response = await validation_exception_handler(mock_request, exc)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_formats_validation_errors(self, mock_request):
        """Handler formats validation errors correctly."""
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {"loc": ("body", "email"), "msg": "Invalid email", "type": "value_error"},
            {"loc": ("body", "password"), "msg": "Too short", "type": "value_error"},
        ]

        response = await validation_exception_handler(mock_request, exc)

        import json
        body = json.loads(response.body)

        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert len(body["error"]["details"]) == 2
        assert body["error"]["details"][0]["field"] == "body.email"
        assert body["error"]["details"][0]["message"] == "Invalid email"


class TestGeneralExceptionHandler:
    """Tests for general_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status(self, mock_request):
        """Handler returns 500 Internal Server Error."""
        exc = RuntimeError("Something went wrong")

        with patch("core.handlers.settings") as mock_settings:
            mock_settings.debug = False
            response = await general_exception_handler(mock_request, exc)

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_hides_details_in_production(self, mock_request):
        """Handler hides exception details when debug is False."""
        exc = RuntimeError("Sensitive database error")

        with patch("core.handlers.settings") as mock_settings:
            mock_settings.debug = False
            response = await general_exception_handler(mock_request, exc)

        import json
        body = json.loads(response.body)

        assert "Sensitive database error" not in body["error"]["message"]
        assert "contact support" in body["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_shows_details_in_debug(self, mock_request):
        """Handler shows exception details when debug is True."""
        exc = RuntimeError("Debug error message")

        with patch("core.handlers.settings") as mock_settings:
            mock_settings.debug = True
            response = await general_exception_handler(mock_request, exc)

        import json
        body = json.loads(response.body)

        assert body["error"]["message"] == "Debug error message"


class TestRateLimitHandler:
    """Tests for rate_limit_handler."""

    @pytest.mark.asyncio
    async def test_returns_429_status(self, mock_request):
        """Handler returns 429 Too Many Requests."""
        exc = RateLimitExceeded(detail="Rate limit exceeded")
        response = await rate_limit_handler(mock_request, exc)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_returns_correct_error_code(self, mock_request):
        """Handler returns RATE_LIMIT_EXCEEDED error code."""
        exc = RateLimitExceeded(detail="Rate limit exceeded")
        response = await rate_limit_handler(mock_request, exc)

        import json
        body = json.loads(response.body)

        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_handles_missing_client(self):
        """Handler works when request.client is None."""
        request = MagicMock(spec=Request)
        request.state.request_id = "test-123"
        request.client = None

        exc = RateLimitExceeded(detail="Rate limit exceeded")
        response = await rate_limit_handler(request, exc)

        assert response.status_code == 429
```

---

## Implementation Roadmap

### Phase 1: Extract Exception Handlers (Size: S, Priority: P0)

**Goal:** Move all exception handler logic from `main.py` to new `handlers.py` module with zero functional changes.

**Scope:**
- ✅ Include: All four exception handlers, exports, unit tests
- ❌ Exclude: Any behavioral changes, new exception types, enhanced error responses, helper registration functions

**Detailed Tasks:**

1. [ ] Create `src/core/handlers.py`
   - Copy all four handler functions from `main.py` (lines 111-234)
   - Add module docstring and imports
   - Ensure logger is module-level: `logger = logging.getLogger(__name__)`

2. [ ] Update `src/core/__init__.py`
   - Add imports for handler functions
   - Add to `__all__` list

3. [ ] Update `src/main.py`
   - Add import for handler functions from `core.handlers`
   - Replace Exception Handlers section (lines 108-234) with four `app.add_exception_handler()` calls
   - Keep imports for exception types needed for registration (RequestValidationError, RateLimitExceeded, AppException)
   - Remove `from fastapi import status` if no longer used

4. [ ] Create `tests/unit/core/test_handlers.py`
   - Unit tests for all four handlers
   - Mock request objects with/without request_id
   - Test debug vs production behavior for general handler

5. [ ] Run full test suite
   - All existing integration tests must pass unchanged
   - New unit tests must pass
   - Coverage should not decrease

**Validation Criteria:**
- [ ] All existing tests pass (`uv run pytest tests/`)
- [ ] New handler unit tests pass
- [ ] `main.py` contains only registration calls (no handler logic)
- [ ] Code quality checks pass (`uv run ruff format . && uv run ruff check --fix . && uv run mypy src/`)
- [ ] Manual verification: API error responses unchanged (test a 404, 422, 500)

**Risk Factors:**
- Import path issues after move → Mitigation: Verify imports resolve correctly before removing from main.py
- Logger name changes affecting log parsing → Mitigation: Logger uses `__name__` which is acceptable

---

## Simplicity & Design Validation

**Simplicity Checklist:**
- [x] Is this the SIMPLEST solution that solves the problem? Yes, direct extraction with no abstraction changes
- [x] Have we avoided premature optimization? Yes, no new patterns introduced
- [x] Does this align with existing patterns in the codebase? Yes, mirrors middleware organization exactly
- [x] Can we deliver value in smaller increments? No, this is already minimal scope
- [x] Are we solving the actual problem vs. a perceived problem? Yes, the description explicitly requests this organization

**Alternatives Considered:**
- **Alternative 1: Keep handlers in main.py** - Rejected because the feature description explicitly requests extraction
- **Alternative 2: Create a register_exception_handlers() helper function** - Rejected to maintain consistency with middleware pattern where registration happens directly in main.py
- **Alternative 3: Put handlers in exceptions.py** - Rejected because handlers depend on Request/Response which are FastAPI concepts, not exception concepts

**Rationale:** Direct extraction maintains consistency with FastAPI patterns and mirrors the existing middleware organization exactly. Registration calls remain in `main.py` just like `app.add_middleware()` calls, while handler logic lives in the dedicated module. No behavioral changes means zero risk of breaking existing functionality.

---

## References & Related Documents

- FastAPI Exception Handling: https://fastapi.tiangolo.com/tutorial/handling-errors/
- Existing pattern reference: `src/core/middleware.py` (middleware organization)
- Custom exceptions: `src/core/exceptions.py`
- Current implementation: `src/main.py` lines 108-234
