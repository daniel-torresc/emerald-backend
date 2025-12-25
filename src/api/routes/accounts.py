"""
Account management API routes.

This module provides:
- POST /api/v1/accounts - Create new account
- GET /api/v1/accounts - List user's accounts (paginated)
- GET /api/v1/accounts/{account_id} - Get account by ID
- PUT /api/v1/accounts/{account_id} - Update account
- DELETE /api/v1/accounts/{account_id} - Soft delete account
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Request, status

from api.dependencies import AccountServiceDep, CurrentUser
from schemas.account import (
    AccountCreate,
    AccountFilterParams,
    AccountListItem,
    AccountResponse,
    AccountUpdate,
)
from schemas.common import PaginatedResponse, PaginationParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new account",
    description="""
    Create a new financial account for the authenticated user.

    The account name must be unique per user (case-insensitive). Currency is
    immutable after creation.

    **Permission:** Authenticated user

    **Audit:** Creates audit log entry with account details
    """,
    responses={
        201: {
            "description": "Account created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                        "account_name": "Chase Checking",
                        "account_type": "savings",
                        "currency": "USD",
                        "opening_balance": "1000.00",
                        "current_balance": "1000.00",
                        "created_at": "2025-11-04T00:00:00Z",
                        "updated_at": "2025-11-04T00:00:00Z",
                    }
                }
            },
        },
        400: {"description": "Account name already exists or invalid currency"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_account(
    request: Request,
    current_user: CurrentUser,
    account_data: AccountCreate,
    account_service: AccountServiceDep,
) -> AccountResponse:
    """
    Create new account for authenticated user.

    Request body:
        - account_name: Account name (1-100 characters, unique per user)
        - account_type_id: Account type UUID (must reference active account type)
        - currency: ISO 4217 code (USD, EUR, GBP, etc.)
        - financial_institution_id: Financial institution UUID (REQUIRED, must be active)
        - opening_balance: Initial balance (can be negative for loans)
        - iban: IBAN account number (optional, will be encrypted, immutable)
        - color_hex: Hex color for UI display (optional, default #818E8F)
        - icon_url: URL to account icon (optional)
        - notes: Personal notes about the account (optional)

    Returns:
        AccountResponse with created account details including institution info

    Requires:
        - Valid access token
        - Active user account
        - Valid financial_institution_id referencing active institution

    Raises:
        - 400 Bad Request: If account name exists, currency invalid, or institution invalid/inactive
        - 422 Unprocessable Entity: If validation fails (invalid IBAN, color format, etc.)
    """
    account = await account_service.create_account(
        user=current_user,
        data=account_data,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return AccountResponse.model_validate(account)


@router.get(
    "",
    response_model=PaginatedResponse[AccountListItem],
    summary="List user's accounts",
    description="""
    List all accounts for the authenticated user with pagination and filtering.

    Supports filtering by account type and financial institution.
    Results are ordered by created_at descending (newest first).

    **Permission:** Authenticated user (can only list own accounts)
    """,
    responses={
        200: {
            "description": "Paginated list of accounts",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "account_name": "Chase Checking",
                                "account_type": "savings",
                                "currency": "USD",
                                "current_balance": "1234.56",
                                "created_at": "2025-11-04T00:00:00Z",
                            }
                        ],
                        "meta": {
                            "total": 42,
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 3,
                        },
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
    },
)
async def list_accounts(
    request: Request,
    current_user: CurrentUser,
    account_service: AccountServiceDep,
    filters: AccountFilterParams = Depends(),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[AccountListItem]:
    """
    List user's accounts with pagination and filtering.

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - account_type_id: Filter by account type ID (optional)
        - financial_institution_id: Filter by institution (optional)

    Returns:
        PaginatedResponse with list of AccountListItem and pagination metadata

    Requires:
        - Valid access token
        - Active user account
    """
    return await account_service.list_user_accounts(
        user_id=current_user.id,
        current_user=current_user,
        pagination=pagination,
        filters=filters,
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account by ID",
    description="""
    Get account details by ID.

    **Phase 2A:** Only account owner can access.
    **Phase 2B:** Owner, editors, and viewers can access.

    **Permission:** Account owner (or shared user in Phase 2B)
    """,
    responses={
        200: {
            "description": "Account details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                        "account_name": "Chase Checking",
                        "account_type": "savings",
                        "currency": "USD",
                        "opening_balance": "1000.00",
                        "current_balance": "1234.56",
                        "created_at": "2025-11-04T00:00:00Z",
                        "updated_at": "2025-11-04T00:00:00Z",
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
        404: {"description": "Account not found or no access"},
    },
)
async def get_account(
    request: Request,
    current_user: CurrentUser,
    account_id: uuid.UUID,
    account_service: AccountServiceDep,
) -> AccountResponse:
    """
    Get account details by ID.

    Path parameters:
        - account_id: UUID of the account

    Returns:
        AccountResponse with full account details

    Requires:
        - Valid access token
        - Active user account
        - Account ownership (or shared access in Phase 2B)

    Raises:
        - 404 Not Found: If account doesn't exist or user has no access
    """
    account = await account_service.get_account(
        account_id=account_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
    )

    return AccountResponse.model_validate(account)


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account",
    description="""
    Update account details.

    Updateable fields: account_name, account_type_id, financial_institution_id, color_hex, icon_url, notes
    Immutable fields: currency, balances, iban

    **Phase 2A:** Only owner can update.
    **Phase 2B:** Owner and editors can update.

    **Permission:** Account owner

    **Audit:** Creates audit log entry with changes
    """,
    responses={
        200: {"description": "Account updated successfully"},
        400: {"description": "Account name already exists"},
        401: {"description": "Not authenticated"},
        404: {"description": "Account not found or no access"},
        422: {"description": "Validation error"},
    },
)
async def update_account(
    request: Request,
    current_user: CurrentUser,
    account_id: uuid.UUID,
    update_data: AccountUpdate,
    account_service: AccountServiceDep,
) -> AccountResponse:
    """
    Update account details.

    Path parameters:
        - account_id: UUID of the account

    Request body:
        - account_name: New name (optional, validates uniqueness)
        - account_type_id: New account type ID (optional, must be accessible)
        - financial_institution_id: New institution (optional)
        - color_hex: New hex color (optional)
        - icon_url: New icon URL (optional)
        - notes: New notes (optional)

    Immutable fields (cannot be updated):
        - iban, currency, opening_balance

    Returns:
        AccountResponse with updated account details

    Requires:
        - Valid access token
        - Active user account
        - Account ownership

    Raises:
        - 400 Bad Request: If new name already exists or institution invalid/inactive
        - 404 Not Found: If account doesn't exist or user has no access
        - 422 Unprocessable Entity: If validation fails
    """
    account = await account_service.update_account(
        account_id=account_id,
        current_user=current_user,
        account_name=update_data.account_name,
        account_type_id=update_data.account_type_id,
        financial_institution_id=update_data.financial_institution_id,
        color_hex=update_data.color_hex,
        icon_url=update_data.icon_url,
        notes=update_data.notes,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return AccountResponse.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
    description="""
    Soft delete account.

    Sets deleted_at timestamp. Account is excluded from normal queries but
    transaction history is preserved for regulatory compliance.

    **Phase 2A:** Only owner can delete.
    **Phase 2B:** Only owner can delete (editors and viewers cannot).

    **Permission:** Account owner

    **Audit:** Creates audit log entry
    """,
    responses={
        204: {"description": "Account deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Account not found or no access"},
    },
)
async def delete_account(
    request: Request,
    current_user: CurrentUser,
    account_id: uuid.UUID,
    account_service: AccountServiceDep,
) -> None:
    """
    Soft delete account.

    Path parameters:
        - account_id: UUID of the account

    Returns:
        204 No Content

    Requires:
        - Valid access token
        - Active user account
        - Account ownership

    Raises:
        - 404 Not Found: If account doesn't exist or user has no access
    """
    await account_service.delete_account(
        account_id=account_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
