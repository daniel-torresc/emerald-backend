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
    AccountEmbeddedResponse,
    AccountFilterParams,
    AccountListResponse,
    AccountResponse,
    AccountSortParams,
    AccountUpdate,
)
from .account_share import (
    AccountShareCreate,
    AccountShareListResponse,
    AccountShareResponse,
    AccountShareUpdate,
)
from .account_type import (
    AccountTypeCreate,
    AccountTypeEmbeddedResponse,
    AccountTypeListResponse,
    AccountTypeResponse,
    AccountTypeUpdate,
)
from .audit import (
    AuditLogFilterParams,
    AuditLogListResponse,
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
    CardEmbeddedResponse,
    CardFilterParams,
    CardListResponse,
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
    SortParams,
)
from .currency import (
    CurrenciesResponse,
    Currency,
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
    FinancialInstitutionEmbeddedResponse,
    FinancialInstitutionFilterParams,
    FinancialInstitutionListResponse,
    FinancialInstitutionResponse,
    FinancialInstitutionSortParams,
    FinancialInstitutionUpdate,
)
from .transaction import (
    TransactionSplitCreateItem,
    TransactionBase,
    TransactionCreate,
    TransactionFilterParams,
    TransactionListResponse,
    TransactionResponse,
    TransactionSortParams,
    TransactionSplitCreate,
    TransactionUpdate,
)
from .user import (
    UserCreate,
    UserEmbeddedResponse,
    UserFilterParams,
    UserListResponse,
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
    "ErrorDetail",
    "ErrorResponse",
    "SortOrder",
    "SortParams",
    # Currency schemas
    "Currency",
    "CurrenciesResponse",
    # User schemas
    "UserCreate",
    "UserEmbeddedResponse",
    "UserFilterParams",
    "UserListResponse",
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
    "AuditLogListResponse",
    # Account Type schemas
    "AccountTypeCreate",
    "AccountTypeEmbeddedResponse",
    "AccountTypeUpdate",
    "AccountTypeResponse",
    "AccountTypeListResponse",
    # Financial Institution schemas
    "FinancialInstitutionCreate",
    "FinancialInstitutionUpdate",
    "FinancialInstitutionResponse",
    "FinancialInstitutionListResponse",
    "FinancialInstitutionFilterParams",
    "FinancialInstitutionEmbeddedResponse",
    "FinancialInstitutionSortParams",
    # Account schemas
    "AccountEmbeddedResponse",
    "AccountListResponse",
    "AccountSortParams",
    "AccountResponse",
    "AccountCreate",
    "AccountUpdate",
    "AccountBase",
    "AccountFilterParams",
    "AccountSortField",
    # Account Share schemas
    "AccountShareCreate",
    "AccountShareListResponse",
    "AccountShareResponse",
    "AccountShareUpdate",
    # Card schemas
    "CardCreate",
    "CardFilterParams",
    "CardListResponse",
    "CardResponse",
    "CardSortParams",
    "CardUpdate",
    "CardBase",
    "CardEmbeddedResponse",
    "CardSortField",
    # Transaction schemas
    "TransactionBase",
    "TransactionSortField",
    "TransactionResponse",
    "TransactionSortParams",
    "TransactionSplitCreate",
    "TransactionUpdate",
    "TransactionCreate",
    "TransactionFilterParams",
    "TransactionListResponse",
    "TransactionSplitCreateItem",
]
