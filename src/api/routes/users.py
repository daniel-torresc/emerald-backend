"""
User management and audit log API routes.

This module provides:
- GET /api/v1/users/me - Get current user profile
- PATCH /api/v1/users/me - Update current user profile
- GET /api/v1/users/{user_id} - Get specific user profile (admin or self)
- GET /api/v1/users - List all users (admin only, paginated)
- POST /api/v1/users/{user_id}/deactivate - Deactivate user (admin only)
- DELETE /api/v1/users/{user_id} - Soft delete user (admin only)
- GET /api/v1/audit-logs/me - Get current user's audit logs
- GET /api/v1/audit-logs - Get all audit logs (admin only)
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import ActiveUser, AdminUser, require_active_user, require_admin
from src.core.database import get_db
from src.models.audit_log import AuditAction, AuditLog, AuditStatus
from src.models.user import User
from src.schemas.audit import AuditLogResponse
from src.schemas.common import PaginatedResponse, PaginationMeta, PaginationParams
from src.schemas.user import UserFilterParams, UserListItem, UserResponse, UserUpdate
from src.services.audit_service import AuditService
from src.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user",
)
async def get_current_user_profile(
    request: Request,
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get current user's profile.

    Returns:
        UserResponse with current user's data

    Requires:
        - Valid access token
        - Active user account
    """
    service = UserService(db)

    return await service.get_user_profile(
        user_id=current_user.id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update the profile of the currently authenticated user",
)
async def update_current_user_profile(
    request: Request,
    update_data: UserUpdate,
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update current user's profile.

    Request body:
        - email: New email address (optional, must be unique)
        - username: New username (optional, must be unique)

    Returns:
        UserResponse with updated user data

    Requires:
        - Valid access token
        - Active user account

    Raises:
        - 409 Conflict: If email or username already in use
        - 422 Unprocessable Entity: If validation fails
    """
    service = UserService(db)

    return await service.update_user_profile(
        user_id=current_user.id,
        update_data=update_data,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get specific user profile",
    description="Get a specific user's profile (admin can view any, users can view self)",
)
async def get_user_by_id(
    request: Request,
    user_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get specific user profile by ID.

    Path parameters:
        - user_id: UUID of user to retrieve

    Returns:
        UserResponse with user data

    Requires:
        - Valid access token
        - Active user account
        - Admin privileges OR requesting own profile

    Raises:
        - 403 Forbidden: If non-admin user tries to view another user
        - 404 Not Found: If user not found
    """
    service = UserService(db)

    return await service.get_user_profile(
        user_id=user_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "",
    response_model=PaginatedResponse[UserListItem],
    summary="List all users",
    description="List all users with pagination and filtering (admin only)",
)
async def list_users(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    is_superuser: bool | None = Query(
        default=None,
        description="Filter by superuser status",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Search in email or username",
    ),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserListItem]:
    """
    List all users with pagination and filtering.

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - is_active: Filter by active status (optional)
        - is_superuser: Filter by superuser status (optional)
        - search: Search in email or username (optional)

    Returns:
        PaginatedResponse with list of users and pagination metadata

    Requires:
        - Valid access token
        - Active user account
        - Admin privileges

    Raises:
        - 403 Forbidden: If user is not admin
    """
    service = UserService(db)

    pagination = PaginationParams(page=page, page_size=page_size)
    filters = UserFilterParams(
        is_active=is_active,
        is_superuser=is_superuser,
        search=search,
    )

    return await service.list_users(
        pagination=pagination,
        filters=filters,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/{user_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate user",
    description="Deactivate a user account (admin only)",
)
async def deactivate_user(
    request: Request,
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deactivate a user account.

    Path parameters:
        - user_id: UUID of user to deactivate

    Effects:
        - Sets is_active = False
        - Revokes all refresh tokens
        - User cannot log in until reactivated

    Requires:
        - Valid access token
        - Active user account
        - Admin privileges

    Raises:
        - 403 Forbidden: If user is not admin
        - 404 Not Found: If user not found
    """
    service = UserService(db)

    await service.deactivate_user(
        user_id=user_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete user",
    description="Soft delete a user account (admin only)",
)
async def delete_user(
    request: Request,
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft delete a user account.

    Path parameters:
        - user_id: UUID of user to delete

    Effects:
        - Sets deleted_at timestamp
        - User excluded from all queries
        - Revokes all refresh tokens
        - User cannot log in
        - Data preserved for audit/compliance (7+ years retention)

    Requires:
        - Valid access token
        - Active user account
        - Admin privileges

    Raises:
        - 403 Forbidden: If user is not admin
        - 404 Not Found: If user not found
    """
    service = UserService(db)

    await service.soft_delete_user(
        user_id=user_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# ============================================================================
# Audit Log Endpoints
# ============================================================================

audit_router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@audit_router.get(
    "/me",
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
    db: AsyncSession = Depends(get_db),
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
    service = AuditService(db)

    # Convert string parameters to enums if provided
    action_enum = AuditAction[action] if action else None
    status_enum = AuditStatus[status] if status else None

    logs, total = await service.get_user_audit_logs(
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


@audit_router.get(
    "",
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
    db: AsyncSession = Depends(get_db),
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
    service = AuditService(db)

    # Convert string parameters to enums if provided
    action_enum = AuditAction[action] if action else None
    status_enum = AuditStatus[status] if status else None

    # Note: get_all_audit_logs doesn't return total, so we need to get it separately
    logs = await service.get_all_audit_logs(
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


# Register audit router
router.include_router(audit_router)
