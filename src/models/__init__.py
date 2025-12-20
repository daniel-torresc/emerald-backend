"""
Database models for Emerald Finance Platform.

This module exports all SQLAlchemy models and the declarative base.
Import models from this module to ensure proper initialization.
"""

from models.account import Account, AccountShare
from models.account_type import AccountType
from models.audit_log import AuditLog
from models.base import Base
from models.card import Card
from models.enums import (
    AuditAction,
    AuditStatus,
    CardType,
    PermissionLevel,
    TransactionType,
)
from models.financial_institution import FinancialInstitution
from models.mixins import AuditFieldsMixin, SoftDeleteMixin, TimestampMixin
from models.refresh_token import RefreshToken
from models.transaction import Transaction
from models.user import User

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
    "TransactionType",
    # Master data models
    "FinancialInstitution",
]
