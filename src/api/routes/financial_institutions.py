"""
Financial institution API routes.

This module provides:
- POST /api/v1/financial-institutions - Create institution (admin only)
- GET /api/v1/financial-institutions - List institutions with filtering
- GET /api/v1/financial-institutions/{id} - Get institution by ID
- GET /api/v1/financial-institutions/swift/{code} - Get by SWIFT code
- GET /api/v1/financial-institutions/routing/{number} - Get by routing number
- PATCH /api/v1/financial-institutions/{id} - Update institution (admin only)
- DELETE /api/v1/financial-institutions/{id} - Delete institution (admin only)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Request, status

from schemas import (
    FinancialInstitutionCreate,
    FinancialInstitutionFilterParams,
    FinancialInstitutionListResponse,
    FinancialInstitutionResponse,
    FinancialInstitutionSortParams,
    FinancialInstitutionUpdate,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
)
from ..dependencies import AdminUser, CurrentUser, FinancialInstitutionServiceDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/financial-institutions", tags=["Financial Institutions"])


@router.post(
    "",
    response_model=FinancialInstitutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create financial institution",
    description="Create a new financial institution (admin only)",
)
async def create_institution(
    request: Request,
    data: FinancialInstitutionCreate,
    current_user: AdminUser,
    service: FinancialInstitutionServiceDep,
) -> FinancialInstitutionResponse:
    """
    Create a new financial institution.

    Request body:
        - name: Official legal name (required)
        - short_name: Display name (required)
        - swift_code: SWIFT/BIC code (optional, must be unique)
        - routing_number: ABA routing number (optional, must be unique, US only)
        - country_code: ISO 3166-1 alpha-2 code (required)
        - institution_type: Institution type (required)
        - logo_url: Logo URL (optional)
        - website_url: Website URL (optional)

    Returns:
        FinancialInstitutionResponse with created institution data

    Requires:
        - Valid access token
        - Admin privileges

    Raises:
        - 409 Conflict: If SWIFT code or routing number already exists
        - 422 Unprocessable Entity: If validation fails
    """
    # Extract client info
    request_id = getattr(request.state, "request_id", None)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    institution = await service.create_institution(
        data=data,
        current_user=current_user,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return FinancialInstitutionResponse.model_validate(institution)


@router.get(
    "",
    response_model=PaginatedResponse[FinancialInstitutionListResponse],
    summary="List financial institutions",
    description="List financial institutions with optional filtering, pagination, and sorting",
)
async def list_institutions(
    current_user: CurrentUser,
    service: FinancialInstitutionServiceDep,
    filters: FinancialInstitutionFilterParams = Depends(),
    pagination: PaginationParams = Depends(),
    sorting: FinancialInstitutionSortParams = Depends(),
) -> PaginatedResponse[FinancialInstitutionListResponse]:
    """
    List financial institutions with filtering.

    Query parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - country_code: Filter by country (2-letter ISO code)
        - institution_type: Filter by type (bank, credit_union, brokerage, fintech, other)
        - is_active: Filter by active status (default: true)
        - search: Search in name and short_name fields
        - sort_by: Sort field (name, short_name, country_code, created_at)
        - sort_order: Sort direction (asc or desc)

    Returns:
        PaginatedResponse with list of institutions and metadata

    Requires:
        - Valid access token
        - Active user account

    Returns active institutions by default.
    """
    financial_institutions, count = await service.list_institutions(
        filters=filters,
        pagination=pagination,
        sorting=sorting,
    )

    return PaginatedResponse(
        data=[
            FinancialInstitutionListResponse.model_validate(fi)
            for fi in financial_institutions
        ],
        meta=PaginationMeta(
            total=count,
            page=pagination.page,
            page_size=pagination.page_size,
        ),
    )


@router.get(
    "/{institution_id}",
    response_model=FinancialInstitutionResponse,
    summary="Get financial institution by ID",
    description="Get detailed information about a specific institution",
)
async def get_institution(
    institution_id: uuid.UUID,
    current_user: CurrentUser,
    service: FinancialInstitutionServiceDep,
) -> FinancialInstitutionResponse:
    """
    Get financial institution by ID.

    Path parameters:
        - institution_id: UUID of the institution

    Returns:
        FinancialInstitutionResponse with institution details

    Requires:
        - Valid access token
        - Active user account

    Returns institution regardless of is_active status.

    Raises:
        - 404 Not Found: If institution not found
    """
    institution = await service.get_institution(institution_id=institution_id)

    return FinancialInstitutionResponse.model_validate(institution)


@router.get(
    "/swift/{swift_code}",
    response_model=FinancialInstitutionResponse,
    summary="Get institution by SWIFT code",
    description="Lookup institution by SWIFT/BIC code",
)
async def get_by_swift_code(
    swift_code: str,
    current_user: CurrentUser,
    service: FinancialInstitutionServiceDep,
) -> FinancialInstitutionResponse:
    """
    Get financial institution by SWIFT/BIC code.

    Path parameters:
        - swift_code: SWIFT/BIC code (8 or 11 characters, case-insensitive)

    Returns:
        FinancialInstitutionResponse with institution details

    Requires:
        - Valid access token
        - Active user account

    Raises:
        - 404 Not Found: If institution not found
        - 422 Unprocessable Entity: If SWIFT code format invalid
    """
    institution = await service.get_by_swift_code(swift_code=swift_code)

    return FinancialInstitutionResponse.model_validate(institution)


@router.get(
    "/routing/{routing_number}",
    response_model=FinancialInstitutionResponse,
    summary="Get institution by routing number",
    description="Lookup US bank by ABA routing number",
)
async def get_by_routing_number(
    routing_number: str,
    current_user: CurrentUser,
    service: FinancialInstitutionServiceDep,
) -> FinancialInstitutionResponse:
    """
    Get financial institution by ABA routing number.

    Path parameters:
        - routing_number: ABA routing number (9 digits)

    Returns:
        FinancialInstitutionResponse with institution details

    Requires:
        - Valid access token
        - Active user account

    Only works for US banks.

    Raises:
        - 404 Not Found: If institution not found
        - 422 Unprocessable Entity: If routing number format invalid
    """
    institution = await service.get_by_routing_number(routing_number=routing_number)

    return FinancialInstitutionResponse.model_validate(institution)


@router.patch(
    "/{institution_id}",
    response_model=FinancialInstitutionResponse,
    summary="Update financial institution",
    description="Update financial institution details (admin only)",
)
async def update_institution(
    request: Request,
    institution_id: uuid.UUID,
    data: FinancialInstitutionUpdate,
    current_user: AdminUser,
    service: FinancialInstitutionServiceDep,
) -> FinancialInstitutionResponse:
    """
    Update financial institution.

    Path parameters:
        - institution_id: UUID of the institution to update

    Request body (all fields optional):
        - name: New official name
        - short_name: New display name
        - swift_code: New SWIFT code (must be unique)
        - routing_number: New routing number (must be unique)
        - country_code: New country code
        - institution_type: New institution type
        - logo_url: New logo URL
        - website_url: New website URL
        - is_active: New active status

    Returns:
        FinancialInstitutionResponse with updated institution data

    Requires:
        - Valid access token
        - Admin privileges

    Raises:
        - 404 Not Found: If institution not found
        - 409 Conflict: If new SWIFT code or routing number already exists
        - 422 Unprocessable Entity: If validation fails
    """
    # Extract client info
    request_id = getattr(request.state, "request_id", None)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    institution = await service.update_institution(
        institution_id=institution_id,
        data=data,
        current_user=current_user,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return FinancialInstitutionResponse.model_validate(institution)


@router.delete(
    "/{institution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete financial institution",
    description="Delete institution (admin only) - soft deletes via deleted_at timestamp",
)
async def delete_institution(
    request: Request,
    institution_id: uuid.UUID,
    current_user: AdminUser,
    service: FinancialInstitutionServiceDep,
) -> None:
    """
    Delete financial institution (soft delete).

    Soft deletes by setting deleted_at timestamp. Institution remains in database for
    historical references but is filtered from queries.

    Path parameters:
        - institution_id: UUID of the institution to delete

    Requires:
        - Valid access token
        - Admin privileges

    Raises:
        - 404 Not Found: If institution not found
    """
    # Extract client info
    request_id = getattr(request.state, "request_id", None)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    await service.delete_institution(
        institution_id=institution_id,
        current_user=current_user,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
