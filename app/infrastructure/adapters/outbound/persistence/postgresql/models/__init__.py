"""
SQLAlchemy models for PostgreSQL persistence.

This package contains all database models (ORM) for the Infrastructure layer.
These are pure SQLAlchemy models with NO business logic.

Business logic lives in the Domain layer (app.domain.entities).

Models:
- Base: Base class for all models with UUID primary key
- UserModel: User authentication and profile
- RoleModel: Role-based access control
- AccountModel: Financial accounts
- AccountShareModel: Account sharing permissions
- AuditLogModel: Immutable audit trail
- RefreshTokenModel: JWT refresh token management

Enums:
- AccountType: Account types (savings, credit_card, etc.)
- PermissionLevel: Share permission levels (owner, editor, viewer)
- AuditAction: Audit log action types
- AuditStatus: Audit log status types

Mixins:
- TimestampMixin: created_at and updated_at timestamps
- SoftDeleteMixin: Soft delete with deleted_at
- AuditFieldsMixin: created_by and updated_by tracking
"""

from app.infrastructure.adapters.outbound.persistence.postgresql.models.account_model import (
    AccountModel,
    AccountShareModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.audit_log_model import (
    AuditLogModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.base import Base
from app.infrastructure.adapters.outbound.persistence.postgresql.models.enums import (
    AccountType,
    AuditAction,
    AuditStatus,
    PermissionLevel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.mixins import (
    AuditFieldsMixin,
    SoftDeleteMixin,
    TimestampMixin,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.refresh_token_model import (
    RefreshTokenModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import (
    RoleModel,
    UserModel,
    user_roles,
)

__all__ = [
    # Base
    "Base",
    # Models
    "UserModel",
    "RoleModel",
    "AccountModel",
    "AccountShareModel",
    "AuditLogModel",
    "RefreshTokenModel",
    # Junction Tables
    "user_roles",
    # Enums
    "AccountType",
    "PermissionLevel",
    "AuditAction",
    "AuditStatus",
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditFieldsMixin",
]
