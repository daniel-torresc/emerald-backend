"""
Pydantic schemas for API request/response validation.

This package provides all Pydantic models used for:
- Request validation
- Response serialization
- API documentation
"""

from src.schemas.account_type import (
    AccountTypeCreate,
    AccountTypeListItem,
    AccountTypeResponse,
    AccountTypeUpdate,
)
from src.schemas.audit import AuditLogFilterParams, AuditLogResponse
from src.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from src.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    ResponseMeta,
    SuccessResponse,
)
from src.schemas.financial_institution import (
    FinancialInstitutionCreate,
    FinancialInstitutionFilterParams,
    FinancialInstitutionListItem,
    FinancialInstitutionResponse,
    FinancialInstitutionUpdate,
)
from src.schemas.user import (
    UserCreate,
    UserFilterParams,
    UserListItem,
    UserPasswordChange,
    UserResponse,
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
]
