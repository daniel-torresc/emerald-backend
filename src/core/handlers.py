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
