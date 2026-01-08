"""
Health Check Endpoints
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text

from core.config import settings
from ..dependencies import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
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
async def readiness_check(
    request: Request,
    db: DbSession,
) -> dict[str, Any]:
    """
    Readiness check endpoint.

    Checks if the application is ready to serve requests.
    This verifies database connectivity and other critical dependencies.

    Returns:
        Detailed readiness status
    """
    try:
        await db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_healthy = False

    return {
        "status": "ready" if db_healthy else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "checks": {
            "database": "ok" if db_healthy else "ko",
            "redis": "-",  # TODO: Add Redis check
        },
    }
