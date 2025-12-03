"""
Enums for account management and transaction models.

This module defines:
- PermissionLevel: Permission levels for account sharing (owner, editor, viewer)
- TransactionType: Types of financial transactions (debit, credit, transfer, etc.)
- InstitutionType: Types of financial institutions (bank, credit_union, brokerage, fintech, other)

These enums are used by the AccountShare, Transaction, and FinancialInstitution models
and are also created as PostgreSQL ENUM types in the database for type safety.

Note: AccountType is no longer an enum. Account types are now stored in the account_types
table as flexible master data, allowing both system-defined and user-defined types.
"""

import enum


class PermissionLevel(str, enum.Enum):
    """
    Permission levels for account sharing.

    Defines the hierarchy of access permissions for shared accounts.
    Each user has exactly one permission level per account.

    Hierarchy (highest to lowest):
        OWNER > EDITOR > VIEWER

    Attributes:
        owner: Full access - read, write, delete, manage sharing
            - Can view account details and balance
            - Can update account name and status
            - Can delete account (soft delete)
            - Can share account with other users
            - Can update permissions for shared users
            - Can revoke access from shared users
            - Only one owner per account (the creator)

        editor: Read and write access - cannot delete or manage sharing
            - Can view account details and balance
            - Can update account name (but not is_active status)
            - Cannot delete account
            - Cannot share account or change permissions
            - Suitable for partners managing shared finances

        viewer: Read-only access
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

    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class TransactionType(str, enum.Enum):
    """
    Financial transaction types.

    Supported transaction types: income (money in), expense (money out),
    and transfer (between own accounts).

    Attributes:
        income: Money in - salary, deposits, refunds, transfers in
            - Increases account balance
            - Examples: salary deposits, refunds, incoming transfers
            - Amount is typically positive

        expense: Money out - purchases, bills, withdrawals, payments
            - Decreases account balance
            - Examples: grocery purchases, bill payments, cash withdrawals
            - Amount is typically negative

        transfer: Movement of money between user's own accounts
            - For internal transfers between accounts
            - One account debited, another credited
            - Neutral impact on total net worth

    Usage:
        transaction = Transaction(
            description="Salary Deposit",
            transaction_type=TransactionType.income,
            amount=5000.00,
            ...
        )

    Note:
        Transaction type affects how transactions are displayed and analyzed
        in reports and budgets. Choose the most appropriate type.
    """

    income = "income"
    expense = "expense"
    transfer = "transfer"

    @classmethod
    def to_dict_list(cls) -> list[dict[str, str]]:
        """
        Return list of dicts with 'key' and 'label' for API responses.

        Returns:
            List of dictionaries with 'key' (enum value) and 'label' (display name)

        Example:
            [
                {"key": "income", "label": "Income"},
                {"key": "expense", "label": "Expense"},
                {"key": "transfer", "label": "Transfer"}
            ]
        """
        return [
            {"key": item.value, "label": item.value.replace("_", " ").title()}
            for item in cls
        ]


class InstitutionType(str, enum.Enum):
    """
    Financial institution types.

    Supported institution types for the platform. Used to categorize
    financial institutions for filtering and reporting.

    Attributes:
        bank: Traditional banks (commercial, retail, universal banks)
            Examples: JPMorgan Chase, Bank of America, HSBC, Deutsche Bank,
            Wells Fargo, Citibank, Barclays

        credit_union: Credit unions and cooperative banks
            Examples: Navy Federal Credit Union, State Employees' Credit Union,
            Pentagon Federal Credit Union, Alliant Credit Union

        brokerage: Investment firms and brokerage houses
            Examples: Fidelity Investments, Vanguard, Charles Schwab,
            Goldman Sachs, Morgan Stanley, TD Ameritrade

        fintech: Financial technology companies
            Examples: Revolut, N26, Wise, Chime, Cash App, PayPal,
            Stripe, Square, Robinhood

        other: Other financial institutions not covered above
            Examples: Payment processors, specialized lenders, fintech startups,
            regional institutions

    Usage:
        institution = FinancialInstitution(
            name="JPMorgan Chase Bank, N.A.",
            short_name="Chase",
            institution_type=InstitutionType.bank,
            country_code="US",
            ...
        )

    Note:
        Institution types affect how institutions are categorized in the UI
        and enable filtering by type (e.g., "show only banks").
    """

    bank = "bank"
    credit_union = "credit_union"
    brokerage = "brokerage"
    fintech = "fintech"
    other = "other"

    @classmethod
    def to_dict_list(cls) -> list[dict[str, str]]:
        """
        Return list of dicts with 'key' and 'label' for API responses.

        Returns:
            List of dictionaries with 'key' (enum value) and 'label' (display name)

        Example:
            [
                {"key": "bank", "label": "Bank"},
                {"key": "credit_union", "label": "Credit Union"},
                {"key": "brokerage", "label": "Brokerage"},
                {"key": "fintech", "label": "Fintech"},
                {"key": "other", "label": "Other"}
            ]
        """
        return [
            {"key": item.value, "label": item.value.replace("_", " ").title()}
            for item in cls
        ]
