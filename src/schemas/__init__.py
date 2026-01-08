"""
Pydantic schemas for API request/response validation.

This package provides all Pydantic models used for:
- Request validation
- Response serialization
- API documentation
"""

from .account import (
    AccountBase,
    AccountCreate,
    AccountEmbedded,
    AccountFilterParams,
    AccountListItem,
    AccountResponse,
    AccountSortParams,
    AccountUpdate,
)
from .account_share import (
    AccountShareCreate,
    AccountShareListItem,
    AccountShareResponse,
    AccountShareUpdate,
)
from .account_type import (
    AccountTypeCreate,
    AccountTypeEmbedded,
    AccountTypeListItem,
    AccountTypeResponse,
    AccountTypeUpdate,
)
from .audit import (
    AuditLogFilterParams,
    AuditLogListItem,
    AuditLogResponse,
    AuditLogSortParams,
)
from .auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
)
from .card import (
    CardBase,
    CardCreate,
    CardEmbedded,
    CardFilterParams,
    CardListItem,
    CardResponse,
    CardSortParams,
    CardUpdate,
)
from .common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    ResponseMeta,
    SearchResult,
    SortParams,
    SuccessResponse,
)
from .currency import (
    CurrenciesResponse,
    Currency,
    CurrencyResponse,
)
from .enums import (
    AccountSortField,
    AuditLogSortField,
    CardSortField,
    SortOrder,
    TransactionSortField,
)
from .financial_institution import (
    FinancialInstitutionCreate,
    FinancialInstitutionEmbedded,
    FinancialInstitutionFilterParams,
    FinancialInstitutionListItem,
    FinancialInstitutionResponse,
    FinancialInstitutionSortParams,
    FinancialInstitutionUpdate,
)
from .transaction import (
    SplitItem,
    TransactionBase,
    TransactionCreate,
    TransactionFilterParams,
    TransactionListItem,
    TransactionResponse,
    TransactionSortParams,
    TransactionSplitRequest,
    TransactionUpdate,
)
from .user import (
    UserCreate,
    UserEmbedded,
    UserFilterParams,
    UserListItem,
    UserPasswordChange,
    UserResponse,
    UserSortParams,
    UserUpdate,
)

__all__ = [
    # Common schemas
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "ResponseMeta",
    "SuccessResponse",
    "ErrorDetail",
    "ErrorResponse",
    "SortOrder",
    "SortParams",
    "SearchResult",
    # Currency schemas
    "Currency",
    "CurrencyResponse",
    "CurrenciesResponse",
    # User schemas
    "UserCreate",
    "UserEmbedded",
    "UserFilterParams",
    "UserListItem",
    "UserPasswordChange",
    "UserResponse",
    "UserUpdate",
    "UserSortParams",
    # Auth schemas
    "LoginRequest",
    "RefreshTokenRequest",
    "AccessTokenResponse",
    "LogoutRequest",
    # Audit schemas
    "AuditLogResponse",
    "AuditLogFilterParams",
    "AuditLogSortParams",
    "AuditLogSortField",
    "AuditLogListItem",
    # Account Type schemas
    "AccountTypeCreate",
    "AccountTypeEmbedded",
    "AccountTypeUpdate",
    "AccountTypeResponse",
    "AccountTypeListItem",
    # Financial Institution schemas
    "FinancialInstitutionCreate",
    "FinancialInstitutionUpdate",
    "FinancialInstitutionResponse",
    "FinancialInstitutionListItem",
    "FinancialInstitutionFilterParams",
    "FinancialInstitutionEmbedded",
    "FinancialInstitutionSortParams",
    # Account schemas
    "AccountEmbedded",
    "AccountListItem",
    "AccountSortParams",
    "AccountResponse",
    "AccountCreate",
    "AccountUpdate",
    "AccountBase",
    "AccountFilterParams",
    "AccountSortField",
    # Account Share schemas
    "AccountShareCreate",
    "AccountShareListItem",
    "AccountShareResponse",
    "AccountShareUpdate",
    # Card schemas
    "CardCreate",
    "CardFilterParams",
    "CardListItem",
    "CardResponse",
    "CardSortParams",
    "CardUpdate",
    "CardBase",
    "CardEmbedded",
    "CardSortField",
    # Transaction schemas
    "TransactionBase",
    "TransactionSortField",
    "TransactionResponse",
    "TransactionSortParams",
    "TransactionSplitRequest",
    "TransactionUpdate",
    "TransactionCreate",
    "TransactionFilterParams",
    "TransactionListItem",
    "SplitItem",
]
