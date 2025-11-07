"""
Health Check Endpoints
"""

import logging
from typing import Any

from fastapi import APIRouter, Request

from src.core import check_database_connection
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        Basic application information and status
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
    }


@router.get("/ready")
async def readiness_check(request: Request) -> dict[str, Any]:
    """
    Readiness check endpoint.

    Checks if the application is ready to serve requests.
    This verifies database connectivity and other critical dependencies.

    Returns:
        Detailed readiness status
    """
    # Check database connection
    sessionmaker = request.app.state.sessionmaker
    db_healthy = await check_database_connection(sessionmaker)

    return {
        "status": "ready" if db_healthy else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "checks": {
            "database": "ok" if db_healthy else "ko",
            "redis": "ok",  # Placeholder - TODO: Add Redis check
        },
    }
