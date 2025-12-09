"""
Database models for Emerald Finance Platform.

This module exports all SQLAlchemy models and the declarative base.
Import models from this module to ensure proper initialization.
"""

from src.models.account import Account, AccountShare
from src.models.account_type import AccountType
from src.models.audit_log import AuditAction, AuditLog, AuditStatus
from src.models.base import Base
from src.models.card import Card
from src.models.enums import CardType, PermissionLevel
from src.models.financial_institution import FinancialInstitution
from src.models.mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin
from src.models.refresh_token import RefreshToken
from src.models.user import User

__all__ = [
    # Base
    "Base",
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditFieldsMixin",
    # User models
    "User",
    # Token models
    "RefreshToken",
    # Audit models
    "AuditLog",
    "AuditAction",
    "AuditStatus",
    # Account models
    "Account",
    "AccountShare",
    "AccountType",  # Master data table (replaces enum)
    "PermissionLevel",
    # Card models
    "Card",
    "CardType",
    # Master data models
    "FinancialInstitution",
]
