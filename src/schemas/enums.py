from enum import Enum


class AccountSortField(str, Enum):
    """
    Allowed sort fields for account list queries.

    Whitelists fields that can be used for sorting to prevent SQL injection.
    Values must match SQLAlchemy model attribute names exactly.
    """

    ACCOUNT_NAME = "account_name"
    CURRENT_BALANCE = "current_balance"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class AuditLogSortField(str, Enum):
    """
    Allowed sort fields for audit log list queries.

    Whitelists fields that can be used for sorting to prevent SQL injection.
    Values must match SQLAlchemy model attribute names exactly.
    """

    CREATED_AT = "created_at"
    ACTION = "action"
    ENTITY_TYPE = "entity_type"


class CardSortField(str, Enum):
    """
    Allowed sort fields for card list queries.

    Whitelists fields that can be used for sorting to prevent SQL injection.
    Values must match SQLAlchemy model attribute names exactly.
    """

    NAME = "name"
    LAST_FOUR_DIGITS = "last_four_digits"
    EXPIRY_YEAR = "expiry_year"
    CREATED_AT = "created_at"


class SortOrder(str, Enum):
    """
    Sort direction for list queries.

    Values:
        ASC: Ascending order (A-Z, 0-9, oldest first)
        DESC: Descending order (Z-A, 9-0, newest first)
    """

    ASC = "asc"
    DESC = "desc"


class FinancialInstitutionSortField(str, Enum):
    """
    Allowed sort fields for financial institution list queries.

    Whitelists fields that can be used for sorting to prevent SQL injection.
    Values must match SQLAlchemy model attribute names exactly.
    """

    NAME = "name"
    SHORT_NAME = "short_name"
    COUNTRY_CODE = "country_code"
    CREATED_AT = "created_at"


class TransactionSortField(str, Enum):
    """
    Allowed sort fields for transaction list queries.

    Whitelists fields that can be used for sorting to prevent SQL injection.
    Values must match SQLAlchemy model attribute names exactly.
    """

    TRANSACTION_DATE = "transaction_date"
    AMOUNT = "amount"
    DESCRIPTION = "description"
    CREATED_AT = "created_at"


class UserSortField(str, Enum):
    """
    Allowed sort fields for user list queries.

    Whitelists fields that can be used for sorting to prevent SQL injection.
    Values must match SQLAlchemy model attribute names exactly.
    """

    USERNAME = "username"
    EMAIL = "email"
    CREATED_AT = "created_at"
    LAST_LOGIN_AT = "last_login_at"
