"""
Database models for Emerald Finance Platform.

This module exports all SQLAlchemy models and the declarative base.
Import models from this module to ensure proper initialization.
"""

from .account import Account
from .account_share import AccountShare
from .account_type import AccountType
from .audit_log import AuditLog
from .base import Base
from .card import Card
from .enums import (
    AuditAction,
    AuditStatus,
    CardType,
    InstitutionType,
    PermissionLevel,
    TransactionReviewStatus,
)
from .financial_institution import FinancialInstitution
from .mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin
from .refresh_token import RefreshToken
from .transaction import Transaction
from .user import User

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
    # Transaction models
    "Transaction",
    "TransactionReviewStatus",
    # Master data models
    "FinancialInstitution",
    "InstitutionType",
]
