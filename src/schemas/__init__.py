"""
Pydantic schemas for API request/response validation.

This package provides all Pydantic models used for:
- Request validation
- Response serialization
- API documentation
"""

from schemas.account_type import (
    AccountTypeCreate,
    AccountTypeListItem,
    AccountTypeResponse,
    AccountTypeUpdate,
)
from schemas.audit import AuditLogFilterParams, AuditLogResponse
from schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    ResponseMeta,
    SearchResult,
    SortOrder,
    SortParams,
    SuccessResponse,
)
from schemas.currency import (
    Currency,
    CurrenciesResponse,
    CurrencyResponse,
)
from schemas.financial_institution import (
    FinancialInstitutionCreate,
    FinancialInstitutionEmbedded,
    FinancialInstitutionFilterParams,
    FinancialInstitutionListItem,
    FinancialInstitutionResponse,
    FinancialInstitutionUpdate,
)
from schemas.user import (
    UserCreate,
    UserEmbedded,
    UserFilterParams,
    UserListItem,
    UserPasswordChange,
    UserResponse,
    UserUpdate,
)
from schemas.account import (
    AccountEmbedded,
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
    "UserUpdate",
    "UserPasswordChange",
    "UserResponse",
    "UserListItem",
    "UserFilterParams",
    # Auth schemas
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "AccessTokenResponse",
    "LogoutRequest",
    # Audit schemas
    "AuditLogResponse",
    "AuditLogFilterParams",
    # Account Type schemas
    "AccountTypeCreate",
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
    # Account schemas
    "AccountEmbedded",
    # User schemas (additional)
    "UserEmbedded",
]
