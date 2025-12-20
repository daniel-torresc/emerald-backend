"""
FastAPI application entry point.

This module sets up:
- FastAPI application with middleware
- Exception handlers
- Rate limiting with Redis
- API routes
- CORS configuration
"""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.routes import (
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
from core import settings, setup_logging
from core.database import (
    close_database_connection,
    create_database_engine,
)
from core.exceptions import AppException
from core.handlers import (
    app_exception_handler,
    general_exception_handler,
    rate_limit_handler,
    validation_exception_handler,
)
from core.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from core.rate_limit import limiter

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


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

    # Create database engine
    engine = create_database_engine()

    # Create sessionmaker and store in app state
    app.state.sessionmaker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Sessionmaker created successfully")

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
    description=settings.description,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter


# ============================================================================
# Exception Handlers
# ============================================================================
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


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
    enable_hsts=settings.is_production,
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
