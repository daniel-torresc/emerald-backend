"""
Audit log API routes.

This module provides:
- GET /api/v1/audit-logs/users/me - Get current user's audit logs
- GET /api/v1/audit-logs/users - Get all audit logs (admin only)
"""

import logging

from fastapi import APIRouter, Depends, Request

from schemas import (
    AuditLogFilterParams,
    AuditLogListItem,
    AuditLogSortParams,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
)
from ..dependencies import AdminUser, AuditServiceDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "/users",
    response_model=PaginatedResponse[AuditLogListItem],
    summary="Get all audit logs",
    description="Get all audit logs with filtering (admin only)",
)
async def get_all_audit_logs(
    request: Request,
    current_user: AdminUser,
    audit_service: AuditServiceDep,
    filters: AuditLogFilterParams = Depends(),
    pagination: PaginationParams = Depends(),
    sorting: AuditLogSortParams = Depends(),
) -> PaginatedResponse[AuditLogListItem]:
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
    logs, count = await audit_service.list_user_audit_logs(
        filters=filters,
        pagination=pagination,
        sorting=sorting,
    )

    return PaginatedResponse(
        data=[AuditLogListItem.model_validate(log) for log in logs],
        meta=PaginationMeta(
            total=count,
            page=pagination.page,
            page_size=pagination.page_size,
        ),
    )
