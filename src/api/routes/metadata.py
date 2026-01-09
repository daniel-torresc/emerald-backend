"""
Metadata API endpoints.

This module provides:
- Account types metadata (for dropdowns)
- Currency metadata (for dropdowns)
- Transaction types metadata (for dropdowns)

These endpoints serve as the authoritative source for business data,
ensuring frontend and backend stay in sync.
"""

import logging
import uuid

from fastapi import APIRouter
from starlette import status
from starlette.requests import Request

from schemas import (
    AccountTypeCreate,
    AccountTypeListResponse,
    AccountTypeResponse,
    AccountTypeUpdate,
    CurrenciesResponse,
)
from ..dependencies import (
    AccountTypeServiceDep,
    AdminUser,
    CurrencyServiceDep,
    CurrentUser,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.get(
    "/currencies",
    response_model=CurrenciesResponse,
    summary="Get supported currencies",
    description="Returns list of supported currencies with ISO 4217 codes and symbols.",
)
async def get_currencies(
    currency_service: CurrencyServiceDep,
) -> CurrenciesResponse:
    """
    Get all supported currencies.

    Args:
        currency_service: Injected CurrencyService instance

    Returns:
        CurrenciesResponse with list of currency objects (code, symbol, name)

    Example Response:
        {
            "currencies": [
                {"code": "USD", "symbol": "$", "name": "US Dollar"},
                {"code": "EUR", "symbol": "€", "name": "Euro"},
                ...
            ]
        }
    """
    logger.debug("Fetching currencies metadata")
    currencies = currency_service.get_all()
    return CurrenciesResponse(currencies=currencies)


@router.post(
    "/account-types",
    response_model=AccountTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account type",
    description="Create a new account type (admin only)",
)
async def create_account_type(
    request: Request,
    current_user: AdminUser,
    data: AccountTypeCreate,
    service: AccountTypeServiceDep,
) -> AccountTypeResponse:
    """
    Create a new account type.

    Request body:
        - key: Unique identifier (lowercase, alphanumeric, underscore only) (required)
        - name: Display name (required)
        - description: Detailed description (optional)
        - icon_url: Icon URL (optional)
        - is_active: Active status (default: true)
        - sort_order: Display order (default: 0)

    Returns:
        AccountTypeResponse with created account type data

    Requires:
        - Valid access token
        - Admin privileges

    Raises:
        - 409 Conflict: If key already exists
        - 422 Unprocessable Entity: If validation fails
    """
    account_type = await service.create_account_type(
        data=data,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    return AccountTypeResponse.model_validate(account_type)


@router.get(
    "/account-types",
    response_model=list[AccountTypeListResponse],
    summary="List account types",
    description="List account types with optional filtering by active status",
)
async def list_account_types(
    current_user: CurrentUser,
    service: AccountTypeServiceDep,
) -> list[AccountTypeListResponse]:
    """
    List all account types.

    Returns:
        List of AccountTypeListItem instances ordered by sort_order, then name

    Requires:
        - Valid access token
        - Active user account
    """
    account_types = await service.list_account_types()

    return [
        AccountTypeListResponse.model_validate(account_type)
        for account_type in account_types
    ]


@router.get(
    "/account-types/{account_type_id}",
    response_model=AccountTypeResponse,
    summary="Get account type by ID",
    description="Get detailed information about a specific account type",
)
async def get_account_type(
    current_user: CurrentUser,
    account_type_id: uuid.UUID,
    service: AccountTypeServiceDep,
) -> AccountTypeResponse:
    """
    Get account type by ID.

    Path parameters:
        - account_type_id: UUID of the account type

    Returns:
        AccountTypeResponse with account type details

    Requires:
        - Valid access token
        - Active user account

    Returns account type regardless of is_active status.

    Raises:
        - 404 Not Found: If account type not found
    """
    account_type = await service.get_account_type(account_type_id=account_type_id)

    return AccountTypeResponse.model_validate(account_type)


@router.get(
    "/account-types/key/{key}",
    response_model=AccountTypeResponse,
    summary="Get account type by key",
    description="Lookup account type by unique key identifier",
)
async def get_by_key(
    current_user: CurrentUser,
    key: str,
    service: AccountTypeServiceDep,
) -> AccountTypeResponse:
    """
    Get account type by key.

    Path parameters:
        - key: Account type key (case-insensitive)

    Returns:
        AccountTypeResponse with account type details

    Requires:
        - Valid access token
        - Active user account

    Raises:
        - 404 Not Found: If account type not found
    """
    account_type = await service.get_by_key(key=key)

    return AccountTypeResponse.model_validate(account_type)


@router.patch(
    "/account-types/{account_type_id}",
    response_model=AccountTypeResponse,
    summary="Update account type",
    description="Update account type details (admin only)",
)
async def update_account_type(
    request: Request,
    account_type_id: uuid.UUID,
    data: AccountTypeUpdate,
    current_user: AdminUser,
    service: AccountTypeServiceDep,
) -> AccountTypeResponse:
    """
    Update account type.

    Path parameters:
        - account_type_id: UUID of the account type to update

    Request body (all fields optional):
        - name: New display name
        - description: New description
        - icon_url: New icon URL
        - is_active: New active status
        - sort_order: New sort order

    Note: The 'key' field is immutable and cannot be changed.

    Returns:
        AccountTypeResponse with updated account type data

    Requires:
        - Valid access token
        - Admin privileges

    Raises:
        - 404 Not Found: If account type not found
        - 422 Unprocessable Entity: If validation fails
    """
    account_type = await service.update_account_type(
        account_type_id=account_type_id,
        data=data,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    return AccountTypeResponse.model_validate(account_type)


@router.delete(
    "/account-types/{account_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account type",
    description="Delete account type (admin only) - hard deletes from database",
)
async def delete_account_type(
    request: Request,
    account_type_id: uuid.UUID,
    current_user: AdminUser,
    service: AccountTypeServiceDep,
) -> None:
    """
    Delete account type (hard delete).

    Permanently removes account type from database. Can only delete if no accounts
    reference this type (enforced by foreign key constraint).

    Path parameters:
        - account_type_id: UUID of the account type to delete

    Requires:
        - Valid access token
        - Admin privileges

    Raises:
        - 404 Not Found: If account type not found
        - 400 Bad Request: If accounts still reference this type
    """
    await service.delete_account_type(
        account_type_id=account_type_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
