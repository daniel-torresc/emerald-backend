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
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.dependencies import get_account_service, require_active_user
from src.models.enums import AccountType
from src.models.user import User
from src.schemas.account import (
    AccountCreate,
    AccountFilterParams,
    AccountListItem,
    AccountResponse,
    AccountUpdate,
)
from src.services.account_service import AccountService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["accounts"])


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
                        "is_active": True,
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
    account_data: AccountCreate,
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """
    Create new account for authenticated user.

    Request body:
        - account_name: Account name (1-100 characters, unique per user)
        - account_type: Type (savings, credit_card, debit_card, loan, investment, other)
        - currency: ISO 4217 code (USD, EUR, GBP, etc.)
        - opening_balance: Initial balance (can be negative for loans)

    Returns:
        AccountResponse with created account details

    Requires:
        - Valid access token
        - Active user account

    Raises:
        - 400 Bad Request: If account name exists or currency invalid
        - 422 Unprocessable Entity: If validation fails
    """
    account = await account_service.create_account(
        user_id=current_user.id,
        account_name=account_data.account_name,
        account_type=account_data.account_type,
        currency=account_data.currency,
        opening_balance=account_data.opening_balance,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return AccountResponse.model_validate(account)


@router.get(
    "",
    response_model=list[AccountListItem],
    summary="List user's accounts",
    description="""
    List all accounts for the authenticated user with pagination and filtering.

    Supports filtering by active status and account type.
    Results are ordered by created_at descending (newest first).

    **Permission:** Authenticated user (can only list own accounts)
    """,
    responses={
        200: {
            "description": "List of accounts",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "account_name": "Chase Checking",
                            "account_type": "savings",
                            "currency": "USD",
                            "current_balance": "1234.56",
                            "is_active": True,
                            "created_at": "2025-11-04T00:00:00Z",
                        }
                    ]
                }
            },
        },
        401: {"description": "Not authenticated"},
    },
)
async def list_accounts(
    request: Request,
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum number of records to return")
    ] = 20,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true=active, false=inactive, null=all)"),
    ] = None,
    account_type: Annotated[
        AccountType | None, Query(description="Filter by account type")
    ] = None,
) -> list[AccountListItem]:
    """
    List user's accounts with pagination and filtering.

    Query parameters:
        - skip: Number of records to skip (default: 0)
        - limit: Max records to return (default: 20, max: 100)
        - is_active: Filter by status (optional)
        - account_type: Filter by type (optional)

    Returns:
        List of AccountListItem (optimized response)

    Requires:
        - Valid access token
        - Active user account
    """
    accounts = await account_service.list_accounts(
        user_id=current_user.id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        is_active=is_active,
        account_type=account_type,
    )

    return [AccountListItem.model_validate(account) for account in accounts]


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
                        "is_active": True,
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
    account_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
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

    Only account_name and is_active can be updated.
    Currency, balances, and account_type are immutable.

    **Phase 2A:** Only owner can update.
    **Phase 2B:** Owner and editors can update (only owner can change is_active).

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
    account_id: uuid.UUID,
    update_data: AccountUpdate,
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """
    Update account details.

    Path parameters:
        - account_id: UUID of the account

    Request body:
        - account_name: New name (optional, validates uniqueness)
        - is_active: New active status (optional)

    Returns:
        AccountResponse with updated account details

    Requires:
        - Valid access token
        - Active user account
        - Account ownership

    Raises:
        - 400 Bad Request: If new name already exists
        - 404 Not Found: If account doesn't exist or user has no access
        - 422 Unprocessable Entity: If validation fails
    """
    account = await account_service.update_account(
        account_id=account_id,
        current_user=current_user,
        account_name=update_data.account_name,
        is_active=update_data.is_active,
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
    account_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    account_service: AccountService = Depends(get_account_service),
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
