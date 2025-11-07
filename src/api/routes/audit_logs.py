"""
Audit log API routes.

This module provides:
- GET /api/v1/audit-logs/users/me - Get current user's audit logs
- GET /api/v1/audit-logs/users - Get all audit logs (admin only)
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request

from src.api.dependencies import (
    get_audit_service,
    require_active_user,
    require_admin,
)
from src.models.audit_log import AuditAction, AuditStatus
from src.models.user import User
from src.schemas.audit import AuditLogResponse
from src.schemas.common import PaginatedResponse, PaginationMeta
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
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    action: str | None = Query(default=None, description="Filter by action type"),
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    status: str | None = Query(default=None, description="Filter by status"),
    start_date: datetime | None = Query(
        default=None,
        description="Filter logs after this date (ISO 8601)",
    ),
    end_date: datetime | None = Query(
        default=None,
        description="Filter logs before this date (ISO 8601)",
    ),
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

    # Convert string parameters to enums if provided
    action_enum = AuditAction[action] if action else None
    status_enum = AuditStatus[status] if status else None

    logs, total = await audit_service.get_user_audit_logs(
        user_id=current_user.id,
        action=action_enum,
        entity_type=entity_type,
        status=status_enum,
        start_date=start_date,
        end_date=end_date,
        skip=(page - 1) * page_size,
        limit=page_size,
    )

    # Convert to response schemas
    log_responses = [AuditLogResponse.model_validate(log) for log in logs]

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        data=log_responses,
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
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
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    action: str | None = Query(default=None, description="Filter by action type"),
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    status: str | None = Query(default=None, description="Filter by status"),
    start_date: datetime | None = Query(
        default=None,
        description="Filter logs after this date (ISO 8601)",
    ),
    end_date: datetime | None = Query(
        default=None,
        description="Filter logs before this date (ISO 8601)",
    ),
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

    # Convert string parameters to enums if provided
    action_enum = AuditAction[action] if action else None
    status_enum = AuditStatus[status] if status else None

    # Note: get_all_audit_logs doesn't return total, so we need to get it separately
    logs = await audit_service.get_all_audit_logs(
        action=action_enum,
        entity_type=entity_type,
        status=status_enum,
        start_date=start_date,
        end_date=end_date,
        skip=(page - 1) * page_size,
        limit=page_size,
    )

    # TODO: Add count method to audit service for total count
    # For now, return the actual count of returned logs
    total = len(logs)
    total_pages = 1 if logs else 0

    # Convert to response schemas
    log_responses = [AuditLogResponse.model_validate(log) for log in logs]

    return PaginatedResponse(
        data=log_responses,
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )
