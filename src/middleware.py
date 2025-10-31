"""
Custom middleware for FastAPI application.

This module provides:
- Request ID generation and tracking
- Security headers middleware
- Request/response logging
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and track request IDs.

    This middleware:
    - Generates a unique UUID for each request
    - Stores it in request.state.request_id
    - Adds X-Request-ID header to responses
    - Enables request tracing across services

    The request ID can be used in:
    - Log messages (for correlation)
    - Audit logs (for tracking)
    - Error responses (for debugging)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add request ID.

        Args:
            request: FastAPI Request object
            call_next: Next middleware or endpoint handler

        Returns:
            Response with X-Request-ID header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Store in request state for use in endpoints and logging
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Security headers added:
    - X-Content-Type-Options: nosniff (prevent MIME type sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 1; mode=block (enable XSS filter)
    - Content-Security-Policy: Strict CSP policy
    - Strict-Transport-Security: Force HTTPS (production only)
    - Referrer-Policy: strict-origin-when-cross-origin

    These headers protect against common web vulnerabilities.
    """

    def __init__(self, app: ASGIApp, enable_hsts: bool = False):
        """
        Initialize SecurityHeadersMiddleware.

        Args:
            app: ASGI application
            enable_hsts: Enable Strict-Transport-Security header (production only)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers.

        Args:
            request: FastAPI Request object
            call_next: Next middleware or endpoint handler

        Returns:
            Response with security headers
        """
        # Process request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        # This is a strict policy - adjust based on your needs
        # Note: We allow cdn.jsdelivr.net and fastapi.tiangolo.com for Swagger UI
        # 'unsafe-inline' is needed for Swagger UI's inline scripts
        # blob: is needed for Swagger UI's worker scripts
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net blob:",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "img-src 'self' data: https: https://fastapi.tiangolo.com",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "worker-src 'self' blob:",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # HSTS (only in production with HTTPS)
        if self.enable_hsts:
            # max-age=31536000 = 1 year
            # includeSubDomains = apply to all subdomains
            # preload = submit to HSTS preload list
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and outgoing responses.

    This middleware logs:
    - Request method and path
    - Request ID
    - Client IP address
    - Response status code
    - Response time
    - User agent

    Log format:
    - INFO: Successful requests (2xx, 3xx)
    - WARNING: Client errors (4xx)
    - ERROR: Server errors (5xx)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: FastAPI Request object
            call_next: Next middleware or endpoint handler

        Returns:
            Response object
        """
        # Record start time
        start_time = time.time()

        # Get request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        request_id = getattr(request.state, "request_id", "unknown")

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {method} {path} - "
                f"request_id={request_id} client={client_host} "
                f"duration={duration:.3f}s error={str(e)}",
                exc_info=True,
            )
            raise

        # Calculate response time
        duration = time.time() - start_time

        # Log based on status code
        status_code = response.status_code
        log_message = (
            f"{method} {path} {status_code} - "
            f"request_id={request_id} client={client_host} "
            f"duration={duration:.3f}s user_agent={user_agent}"
        )

        if 200 <= status_code < 400:
            logger.info(log_message)
        elif 400 <= status_code < 500:
            logger.warning(log_message)
        else:
            logger.error(log_message)

        # Add response time header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response