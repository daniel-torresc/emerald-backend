"""
Audit log API routes.

This module provides:
- GET /api/v1/audit-logs/users/me - Get current user's audit logs
- GET /api/v1/audit-logs/users - Get all audit logs (admin only)
"""

import logging

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import (
    get_audit_service,
    require_active_user,
    require_admin,
)
from src.models.user import User
from src.schemas.audit import AuditLogFilterParams, AuditLogResponse
from src.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "/users/me",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="Get current user's audit logs",
    description="Get audit logs for the currently authenticated user (GDPR right to access)",
)
async def get_current_user_audit_logs(
    request: Request,
    pagination: PaginationParams = Depends(),
    filters: AuditLogFilterParams = Depends(),
    current_user: User = Depends(require_active_user),
    audit_service: AuditService = Depends(get_audit_service),
) -> PaginatedResponse[AuditLogResponse]:
    """
    Get audit logs for current user.

    This endpoint implements GDPR right to access:
    - Users can view all actions performed on their account
    - Users can see who accessed their data and when

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - action: Filter by action type (e.g., "LOGIN", "UPDATE")
        - entity_type: Filter by entity type (e.g., "user", "transaction")
        - status: Filter by status ("SUCCESS", "FAILURE")
        - start_date: Filter logs after this date
        - end_date: Filter logs before this date

    Returns:
        PaginatedResponse with list of audit logs and pagination metadata

    Requires:
        - Valid access token
        - Active user account
    """

    # Get logs and total count
    logs, total = await audit_service.get_user_audit_logs(
        user_id=current_user.id,
        action=filters.action,
        entity_type=filters.entity_type,
        status=filters.status,
        start_date=filters.start_date,
        end_date=filters.end_date,
        skip=pagination.offset,
        limit=pagination.page_size,
    )

    # Convert to response schemas
    log_responses = [AuditLogResponse.model_validate(log) for log in logs]

    # Calculate total pages
    total_pages = PaginationParams.calculate_total_pages(total, pagination.page_size)

    return PaginatedResponse(
        data=log_responses,
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/users",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="Get all audit logs",
    description="Get all audit logs with filtering (admin only)",
)
async def get_all_audit_logs(
    request: Request,
    pagination: PaginationParams = Depends(),
    filters: AuditLogFilterParams = Depends(),
    current_user: User = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service),
) -> PaginatedResponse[AuditLogResponse]:
    """
    Get all audit logs with filtering (admin only).

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - action: Filter by action type (e.g., "LOGIN", "UPDATE")
        - entity_type: Filter by entity type (e.g., "user", "transaction")
        - status: Filter by status ("SUCCESS", "FAILURE")
        - start_date: Filter logs after this date
        - end_date: Filter logs before this date

    Returns:
        PaginatedResponse with list of audit logs and pagination metadata

    Requires:
        - Valid access token
        - Active user account
        - Admin privileges

    Raises:
        - 403 Forbidden: If user is not admin
    """

    # Get logs and total count
    logs, total = await audit_service.get_all_audit_logs(
        action=filters.action,
        entity_type=filters.entity_type,
        status=filters.status,
        start_date=filters.start_date,
        end_date=filters.end_date,
        skip=pagination.offset,
        limit=pagination.page_size,
    )

    # Convert to response schemas
    log_responses = [AuditLogResponse.model_validate(log) for log in logs]

    # Calculate total pages
    total_pages = PaginationParams.calculate_total_pages(total, pagination.page_size)

    return PaginatedResponse(
        data=log_responses,
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )
