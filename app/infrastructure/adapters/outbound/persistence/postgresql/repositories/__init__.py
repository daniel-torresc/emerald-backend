"""
PostgreSQL repository implementations.

This package contains concrete implementations of repository ports
using PostgreSQL and SQLAlchemy.

All repositories inherit from BaseRepository for common CRUD operations
and implement their specific port interfaces.
"""

from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.account_repository import (
    PostgresAccountRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.account_share_repository import (
    PostgresAccountShareRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.audit_log_repository import (
    PostgresAuditLogRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.base_repository import (
    BaseRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.role_repository import (
    PostgresRoleRepository,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.user_repository import (
    PostgresUserRepository,
)

__all__ = [
    "BaseRepository",
    "PostgresUserRepository",
    "PostgresRoleRepository",
    "PostgresAccountRepository",
    "PostgresAccountShareRepository",
    "PostgresAuditLogRepository",
    "PostgresRefreshTokenRepository",
]
