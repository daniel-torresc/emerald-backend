"""
Account type API routes.

This module provides:
- POST /api/v1/account-types - Create account type (admin only)
- GET /api/v1/account-types - List account types with filtering
- GET /api/v1/account-types/{id} - Get account type by ID
- GET /api/v1/account-types/key/{key} - Get by key
- PATCH /api/v1/account-types/{id} - Update account type (admin only)
- POST /api/v1/account-types/{id}/deactivate - Deactivate account type (admin only)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.dependencies import (
    get_account_type_service,
    require_active_user,
    require_admin,
)
from src.models.user import User
from src.schemas.account_type import (
    AccountTypeCreate,
    AccountTypeListItem,
    AccountTypeResponse,
    AccountTypeUpdate,
)
from src.services.account_type_service import AccountTypeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account-types", tags=["Account Types"])


@router.post(
    "",
    response_model=AccountTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account type",
    description="Create a new account type (admin only)",
)
async def create_account_type(
    request: Request,
    data: AccountTypeCreate,
    current_user: User = Depends(require_admin),
    service: AccountTypeService = Depends(get_account_type_service),
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
    return await service.create_account_type(
        data=data,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "",
    response_model=list[AccountTypeListItem],
    summary="List account types",
    description="List account types with optional filtering by active status",
)
async def list_account_types(
    is_active: bool | None = Query(
        default=True,
        description="Filter by active status (true=active only, false=inactive only, null=all)",
    ),
    current_user: User = Depends(require_active_user),
    service: AccountTypeService = Depends(get_account_type_service),
) -> list[AccountTypeListItem]:
    """
    List account types with optional active status filtering.

    Query parameters:
        - is_active: Filter by active status (default: true)
          - true: Only active types
          - false: Only inactive types
          - null: All types (active and inactive)

    Returns:
        List of AccountTypeListItem instances ordered by sort_order, then name

    Requires:
        - Valid access token
        - Active user account

    Returns active account types by default.
    """
    return await service.list_account_types(is_active=is_active)


@router.get(
    "/{account_type_id}",
    response_model=AccountTypeResponse,
    summary="Get account type by ID",
    description="Get detailed information about a specific account type",
)
async def get_account_type(
    account_type_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    service: AccountTypeService = Depends(get_account_type_service),
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
    return await service.get_account_type(account_type_id=account_type_id)


@router.get(
    "/key/{key}",
    response_model=AccountTypeResponse,
    summary="Get account type by key",
    description="Lookup account type by unique key identifier",
)
async def get_by_key(
    key: str,
    current_user: User = Depends(require_active_user),
    service: AccountTypeService = Depends(get_account_type_service),
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
    return await service.get_by_key(key=key)


@router.patch(
    "/{account_type_id}",
    response_model=AccountTypeResponse,
    summary="Update account type",
    description="Update account type details (admin only)",
)
async def update_account_type(
    request: Request,
    account_type_id: uuid.UUID,
    data: AccountTypeUpdate,
    current_user: User = Depends(require_admin),
    service: AccountTypeService = Depends(get_account_type_service),
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
    return await service.update_account_type(
        account_type_id=account_type_id,
        data=data,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/{account_type_id}/deactivate",
    response_model=AccountTypeResponse,
    summary="Deactivate account type",
    description="Deactivate account type (admin only) - sets is_active to false",
)
async def deactivate_account_type(
    request: Request,
    account_type_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    service: AccountTypeService = Depends(get_account_type_service),
) -> AccountTypeResponse:
    """
    Deactivate account type.

    Sets is_active = False. Account type remains in database for
    historical references but won't appear in default listings.

    Path parameters:
        - account_type_id: UUID of the account type to deactivate

    Returns:
        AccountTypeResponse with deactivated account type data

    Requires:
        - Valid access token
        - Admin privileges

    Raises:
        - 404 Not Found: If account type not found
    """
    return await service.deactivate_account_type(
        account_type_id=account_type_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
