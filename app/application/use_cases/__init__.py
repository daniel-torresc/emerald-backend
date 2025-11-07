"""Use cases (application layer business logic)."""

# Auth use cases
from app.application.use_cases.auth import (
    AuthenticateUserUseCase,
    ChangePasswordUseCase,
    LogoutUserUseCase,
    RefreshTokenUseCase,
    RegisterUserUseCase,
)

# User use cases
from app.application.use_cases.users import (
    DeleteUserUseCase,
    GetUserProfileUseCase,
    ListUsersUseCase,
    UpdateUserProfileUseCase,
)

# Account use cases
from app.application.use_cases.accounts import (
    CreateAccountUseCase,
    DeleteAccountUseCase,
    GetAccountUseCase,
    ListUserAccountsUseCase,
    ShareAccountUseCase,
    UpdateAccountUseCase,
)

# Audit use cases
from app.application.use_cases.audit import (
    CreateAuditLogUseCase,
    QueryAuditLogsUseCase,
)

__all__ = [
    # Auth
    "AuthenticateUserUseCase",
    "ChangePasswordUseCase",
    "LogoutUserUseCase",
    "RefreshTokenUseCase",
    "RegisterUserUseCase",
    # Users
    "DeleteUserUseCase",
    "GetUserProfileUseCase",
    "ListUsersUseCase",
    "UpdateUserProfileUseCase",
    # Accounts
    "CreateAccountUseCase",
    "DeleteAccountUseCase",
    "GetAccountUseCase",
    "ListUserAccountsUseCase",
    "ShareAccountUseCase",
    "UpdateAccountUseCase",
    # Audit
    "CreateAuditLogUseCase",
    "QueryAuditLogsUseCase",
]
