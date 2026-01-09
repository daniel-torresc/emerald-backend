"""
Enums for account management and transaction models.

This module defines:
- PermissionLevel: Permission levels for account sharing (owner, editor, viewer)
- TransactionType: Types of financial transactions (debit, credit, transfer, etc.)
- InstitutionType: Types of financial institutions (bank, credit_union, brokerage, fintech, other)
- CardType: Types of cards (credit_card, debit_card)

These enums are used by the AccountShare, Transaction, FinancialInstitution, and Card models
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


class TransactionReviewStatus(str, enum.Enum):
    """
    Review status for transactions.

    Tracks whether a transaction has been reviewed by the user.
    New transactions default to TO_REVIEW status.

    Attributes:
        to_review: Transaction needs user review (default for new transactions)
            - Set automatically when transaction is created
            - Indicates user hasn't reviewed/verified the transaction
            - Used for filtering transactions that need attention

        reviewed: Transaction has been reviewed by user
            - User has verified the transaction details
            - May have edited description, added notes, etc.
            - Indicates transaction is finalized

    Future extensions may include:
        - pending_payment: Awaiting payment confirmation
        - disputed: Transaction is being disputed
        - reconciled: Matched with bank statement

    Usage:
        transaction = Transaction(
            original_description="Amazon Purchase",
            review_status=TransactionReviewStatus.to_review,
            ...
        )

        # After user reviews
        transaction.review_status = TransactionReviewStatus.reviewed

    Note:
        Review status is used for filtering and workflow management.
        Users can filter to see only transactions that need review.
    """

    to_review = "to_review"
    reviewed = "reviewed"

    @classmethod
    def to_dict_list(cls) -> list[dict[str, str]]:
        """
        Return list of dicts with 'key' and 'label' for API responses.

        Returns:
            List of dictionaries with 'key' (enum value) and 'label' (display name)

        Example:
            [
                {"key": "to_review", "label": "To Review"},
                {"key": "reviewed", "label": "Reviewed"}
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


class CardType(str, enum.Enum):
    """
    Card type classification.

    Supported card types for the platform. Used to differentiate between
    credit and debit cards for proper account linking and spending analysis.

    Attributes:
        credit_card: Credit cards issued by financial institutions
            - Linked to credit card accounts
            - Have credit limits
            - Monthly billing cycles
            - Examples: Chase Sapphire Reserve, American Express Platinum,
            Citi Double Cash, Capital One Venture

        debit_card: Debit cards linked to checking or savings accounts
            - Draw funds directly from account balance
            - No credit limit (limited by account balance)
            - Immediate transaction settlement
            - Examples: Chase Checking Debit, Bank of America Debit,
            Wells Fargo Debit

    Usage:
        card = Card(
            name="Chase Sapphire Reserve",
            card_type=CardType.credit_card,
            account_id=account.id,
            ...
        )

    Note:
        Card type affects which accounts can be linked (credit cards must link
        to credit accounts, debit cards to checking/savings accounts).
    """

    credit_card = "credit_card"
    debit_card = "debit_card"

    @classmethod
    def to_dict_list(cls) -> list[dict[str, str]]:
        """
        Return list of dicts with 'key' and 'label' for API responses.

        Returns:
            List of dictionaries with 'key' (enum value) and 'label' (display name)

        Example:
            [
                {"key": "credit_card", "label": "Credit Card"},
                {"key": "debit_card", "label": "Debit Card"}
            ]
        """
        return [
            {"key": item.value, "label": item.value.replace("_", " ").title()}
            for item in cls
        ]


class AuditAction(str, enum.Enum):
    """
    Enumeration of audit log action types.

    These actions are logged for compliance and security monitoring.
    """

    # Authentication actions
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    TOKEN_REFRESH = "TOKEN_REFRESH"

    # CRUD actions (data modifications)
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    # Transaction-specific actions
    SPLIT_TRANSACTION = "SPLIT_TRANSACTION"
    JOIN_TRANSACTION = "JOIN_TRANSACTION"

    # Financial institution actions
    CREATE_FINANCIAL_INSTITUTION = "CREATE_FINANCIAL_INSTITUTION"
    UPDATE_FINANCIAL_INSTITUTION = "UPDATE_FINANCIAL_INSTITUTION"
    DEACTIVATE_FINANCIAL_INSTITUTION = "DEACTIVATE_FINANCIAL_INSTITUTION"

    # Account type actions
    CREATE_ACCOUNT_TYPE = "CREATE_ACCOUNT_TYPE"
    UPDATE_ACCOUNT_TYPE = "UPDATE_ACCOUNT_TYPE"
    DEACTIVATE_ACCOUNT_TYPE = "DEACTIVATE_ACCOUNT_TYPE"

    # Authorization actions
    PERMISSION_GRANT = "PERMISSION_GRANT"
    PERMISSION_REVOKE = "PERMISSION_REVOKE"

    # Administrative actions
    ACCOUNT_ACTIVATE = "ACCOUNT_ACTIVATE"
    ACCOUNT_DEACTIVATE = "ACCOUNT_DEACTIVATE"
    ACCOUNT_LOCK = "ACCOUNT_LOCK"
    ACCOUNT_UNLOCK = "ACCOUNT_UNLOCK"

    # Security events
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_TOKEN = "INVALID_TOKEN"
    PERMISSION_DENIED = "PERMISSION_DENIED"


class AuditStatus(str, enum.Enum):
    """Status of the audited action."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"
