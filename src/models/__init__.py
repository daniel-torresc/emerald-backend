"""
Database models for Emerald Finance Platform.

This module exports all SQLAlchemy models and the declarative base.
Import models from this module to ensure proper initialization.
"""

from src.models.account import Account, AccountShare
from src.models.audit_log import AuditAction, AuditLog, AuditStatus
from src.models.base import Base
from src.models.bootstrap import BootstrapState
from src.models.enums import AccountType, PermissionLevel
from src.models.mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin
from src.models.refresh_token import RefreshToken
from src.models.user import Role, User, user_roles

__all__ = [
    # Base
    "Base",
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditFieldsMixin",
    # User models
    "User",
    "Role",
    "user_roles",
    # Token models
    "RefreshToken",
    # Audit models
    "AuditLog",
    "AuditAction",
    "AuditStatus",
    # Account models
    "Account",
    "AccountShare",
    "AccountType",
    "PermissionLevel",
    # Bootstrap
    "BootstrapState",
]
