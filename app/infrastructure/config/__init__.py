"""
Infrastructure layer configuration.

This package contains configuration for infrastructure components:
- Database connection and session management
- Dependency injection helpers
- External service integrations
- Configuration settings
"""

from app.infrastructure.config.database import DatabaseConfig
from app.infrastructure.config.dependencies import (
    create_session_dependency,
    create_uow_dependency,
)

__all__ = [
    "DatabaseConfig",
    "create_session_dependency",
    "create_uow_dependency",
]
