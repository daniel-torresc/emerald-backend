"""
FastAPI application entry point for Emerald Finance Platform.

This is a placeholder for Phase 1.1. The full application implementation
will be added in Phase 1.2 (Authentication & Security).
"""

from fastapi import FastAPI

from src.core import settings, setup_logging

# Setup logging
setup_logging()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Emerald Personal Finance Platform - Backend API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns basic application information.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns welcome message.
    """
    return {
        "message": "Welcome to Emerald Finance Platform API",
        "version": settings.version,
        "docs": "/docs" if settings.debug else "disabled in production",
    }
