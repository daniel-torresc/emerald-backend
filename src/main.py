"""
FastAPI application entry point for Emerald Finance Platform.

This module sets up:
- FastAPI application with middleware
- Exception handlers
- Rate limiting with Redis
- API routes
- CORS configuration
"""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.routes import (
    account_shares,
    account_types,
    accounts,
    audit_logs,
    auth,
    cards,
    financial_institutions,
    health,
    metadata,
    root,
    transactions,
    users,
)
from src.core import settings, setup_logging
from src.core.database import (
    close_database_connection,
    create_database_engine,
)
from src.exceptions import AppException
from src.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


# ============================================================================
# Rate Limiter Setup
# ============================================================================
# Initialize rate limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=str(settings.redis_url),
    default_limits=[settings.rate_limit_default],  # Global rate limit
)


# ============================================================================
# Lifespan Context Manager
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database engine creation and storage in app.state
    - Session factory creation
    - Resource cleanup on shutdown
    """
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Environment: {settings.environment}")

    # Create database engine and store in app state
    logger.info("Initializing database engine...")
    engine = create_database_engine()

    # Create sessionmaker and store in app state
    app.state.sessionmaker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Database engine initialized successfully")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")
    await close_database_connection(engine)
    app.state.sessionmaker = None


# ============================================================================
# FastAPI Application
# ============================================================================
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Emerald Personal Finance Platform - Backend API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter
# Add SlowAPI exception handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================================
# Exception Handlers
# ============================================================================
@app.exception_handler(AppException)
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


@app.exception_handler(RequestValidationError)
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


@app.exception_handler(Exception)
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


@app.exception_handler(RateLimitExceeded)
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
                "details": {
                    "retry_after": 60,  # seconds
                },
            },
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )


# ============================================================================
# Middleware Setup (Order matters!)
# ============================================================================
# 1. Request ID middleware (must be first to add request_id to state)
app.add_middleware(RequestIDMiddleware)

# 2. Request logging middleware (logs all requests with request_id)
app.add_middleware(RequestLoggingMiddleware)

# 3. Security headers middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=(settings.environment == "production"),
)

# 4. CORS middleware (should be last to ensure headers are added to all responses)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Routes
# ============================================================================
# Create V1 Router
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(audit_logs.router)
v1_router.include_router(users.router)
v1_router.include_router(financial_institutions.router)
v1_router.include_router(account_types.router)
v1_router.include_router(accounts.router)
v1_router.include_router(account_shares.router)
v1_router.include_router(cards.router)
v1_router.include_router(transactions.router)

# Create API Router
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(metadata.router)
api_router.include_router(v1_router)

# Include Application Routers
app.include_router(root.router)
app.include_router(health.router)
app.include_router(api_router)
