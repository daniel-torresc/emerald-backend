"""
Enums for account management models.

This module defines:
- AccountType: Types of financial accounts (savings, credit_card, etc.)
- PermissionLevel: Permission levels for account sharing (owner, editor, viewer)

These enums are used by the Account and AccountShare models and are also
created as PostgreSQL ENUM types in the database for type safety.
"""

import enum


class AccountType(str, enum.Enum):
    """
    Financial account types.

    Standard account types supported by the platform. Each account must have
    exactly one type. The type is informational and used for:
    - UI categorization and icons
    - Reporting and analytics
    - Future business logic (e.g., different balance calculations for credit cards)

    Attributes:
        SAVINGS: Savings or checking accounts with positive balances
        CREDIT_CARD: Credit card accounts (typically negative balance = debt)
        DEBIT_CARD: Prepaid or debit card accounts
        LOAN: Loan accounts (mortgage, personal, auto) - negative balance = debt
        INVESTMENT: Investment or brokerage accounts (stocks, bonds, mutual funds)
        OTHER: User-defined account types not covered by standard types

    Usage:
        account = Account(
            account_name="My Savings",
            account_type=AccountType.SAVINGS,
            ...
        )
    """

    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    LOAN = "loan"
    INVESTMENT = "investment"
    OTHER = "other"


class PermissionLevel(str, enum.Enum):
    """
    Permission levels for account sharing.

    Defines the hierarchy of access permissions for shared accounts.
    Each user has exactly one permission level per account.

    Hierarchy (highest to lowest):
        OWNER > EDITOR > VIEWER

    Attributes:
        OWNER: Full access - read, write, delete, manage sharing
            - Can view account details and balance
            - Can update account name and status
            - Can delete account (soft delete)
            - Can share account with other users
            - Can update permissions for shared users
            - Can revoke access from shared users
            - Only one owner per account (the creator)

        EDITOR: Read and write access - cannot delete or manage sharing
            - Can view account details and balance
            - Can update account name (but not is_active status)
            - Cannot delete account
            - Cannot share account or change permissions
            - Suitable for partners managing shared finances

        VIEWER: Read-only access
            - Can view account details and balance
            - Cannot modify anything
            - Cannot delete account
            - Cannot share account or change permissions
            - Suitable for financial advisors or read-only access

    Permission Matrix:
        | Operation              | Owner | Editor | Viewer |
        |------------------------|-------|--------|--------|
        | View account details   |   ✓   |   ✓    |   ✓    |
        | View balance           |   ✓   |   ✓    |   ✓    |
        | Update account name    |   ✓   |   ✓    |   ✗    |
        | Update is_active       |   ✓   |   ✗    |   ✗    |
        | Delete account         |   ✓   |   ✗    |   ✗    |
        | Share account          |   ✓   |   ✗    |   ✗    |
        | Update permissions     |   ✓   |   ✗    |   ✗    |
        | Revoke access          |   ✓   |   ✗    |   ✗    |

    Usage:
        share = AccountShare(
            account_id=account.id,
            user_id=partner.id,
            permission_level=PermissionLevel.EDITOR,
            ...
        )

    Note:
        Permission levels are enforced in the service layer (PermissionService).
        All service methods must check permissions before performing operations.
    """

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
