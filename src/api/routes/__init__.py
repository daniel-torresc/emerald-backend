"""
API routes for Emerald Finance Platform.

This package contains all API endpoint definitions organized by feature.
"""

from . import (
    account_shares,
    accounts,
    audit_logs,
    auth,
    cards,
    financial_institutions,
    health,
    metadata,
    root,
    transactions,
    users,
)

__all__ = [
    "account_shares",
    "accounts",
    "audit_logs",
    "auth",
    "cards",
    "financial_institutions",
    "health",
    "metadata",
    "root",
    "transactions",
    "users",
]
