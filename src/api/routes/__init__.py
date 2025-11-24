"""
API routes for Emerald Finance Platform.

This package contains all API endpoint definitions organized by feature.
"""

from src.api.routes import account_shares, accounts, audit_logs, auth, users

__all__ = ["account_shares", "accounts", "audit_logs", "auth", "users"]