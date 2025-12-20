"""
Root Endpoints
"""

import logging

from fastapi import APIRouter

from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Root"])


@router.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns:
        Welcome message with API information
    """
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.version,
        "docs": "/docs" if settings.debug else "disabled in production",
        "health": "/health",
    }
