"""
Admin management API routes.

This module provides HTTP endpoints for admin operations:
- POST /api/v1/admin/users - Create admin user
- GET /api/v1/admin/users - List admin users
- GET /api/v1/admin/users/{user_id} - Get admin user details
- PUT /api/v1/admin/users/{user_id} - Update admin user
- DELETE /api/v1/admin/users/{user_id} - Delete admin user
- PUT /api/v1/admin/users/{user_id}/password - Reset admin password
- PUT /api/v1/admin/users/{user_id}/permissions - Update admin permissions

Note: Initial superuser is created automatically during database migration
via 'alembic upgrade head'. See SUPERADMIN_* environment variables in .env
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Request, status

from src.api.dependencies import (
    AdminUser,
    get_admin_service,
)
from src.schemas.admin import (
    AdminUserFilterParams,
    AdminUserListItem,
    AdminUserResponse,
    CreateAdminUserRequest,
    ResetPasswordRequest,
    UpdateAdminUserRequest,
    UpdatePermissionsRequest,
)
from src.schemas.common import PaginatedResponse
from src.services.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create admin user",
    description="Create a new admin user. Only accessible by existing admins. "
                "Password is optional - if not provided, a strong password will be generated. "
                "Returns the created admin user with temporary password if generated.",
)
async def create_admin_user(
    request_data: CreateAdminUserRequest,
    request: Request,
    current_user: AdminUser,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminUserResponse:
    """
    Create a new admin user.

    Requires admin authentication.
    Validates username/email uniqueness and password strength.
    Generates password if not provided.
    Assigns admin role and creates audit log entry.

    Args:
        request_data: Admin user creation request
        request: FastAPI request object (for IP, user-agent)
        current_user: Current authenticated admin
        admin_service: Admin service instance

    Returns:
        Created admin user with temporary password (if generated)

    Raises:
        409: If username or email already exists
        422: If validation fails
    """
    return await admin_service.create_admin_user(
        request=request_data,
        created_by=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/users",
    response_model=PaginatedResponse[AdminUserListItem],
    summary="List admin users",
    description="Get paginated list of admin users with optional filtering and search. "
                "Only accessible by admins. Supports searching by username, email, or full name.",
)
async def list_admin_users(
    current_user: AdminUser,
    admin_service: AdminService = Depends(get_admin_service),
    filters: AdminUserFilterParams = Depends(),
) -> PaginatedResponse[AdminUserListItem]:
    """
    List all admin users with pagination and filtering.

    Requires admin authentication.
    Supports search, active status filtering, and pagination.

    Args:
        filters: Filter parameters (search, is_active, skip, limit)
        current_user: Current authenticated admin
        admin_service: Admin service instance

    Returns:
        Paginated list of admin users

    Query Parameters:
        search: Search in username, email, or full_name (optional)
        is_active: Filter by active status (optional)
        skip: Number of records to skip (default: 0)
        limit: Maximum records to return (default: 20, max: 100)
        sort_by: Field to sort by - username or created_at (default: created_at)
    """
    return await admin_service.list_admin_users(filters=filters)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get admin user details",
    description="Get detailed information about a specific admin user. "
                "Only accessible by admins.",
)
async def get_admin_user(
    user_id: uuid.UUID,
    current_user: AdminUser,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminUserResponse:
    """
    Get admin user by ID.

    Requires admin authentication.

    Args:
        user_id: Admin user ID
        current_user: Current authenticated admin
        admin_service: Admin service instance

    Returns:
        Admin user details with permissions

    Raises:
        404: If admin user not found
    """
    return await admin_service.get_admin_user(
        user_id=user_id,
        current_user=current_user,
    )


@router.put(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update admin user",
    description="Update admin user information (full_name, is_active). "
                "Cannot update username or email via this endpoint. "
                "Cannot deactivate the last admin user.",
)
async def update_admin_user(
    user_id: uuid.UUID,
    request_data: UpdateAdminUserRequest,
    request: Request,
    current_user: AdminUser,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminUserResponse:
    """
    Update admin user information.

    Requires admin authentication.
    Only allows updating full_name and is_active.
    Cannot deactivate the last admin.

    Args:
        user_id: Admin user ID to update
        request_data: Update request data
        request: FastAPI request object
        current_user: Current authenticated admin
        admin_service: Admin service instance

    Returns:
        Updated admin user

    Raises:
        403: If trying to deactivate the last admin
        404: If admin user not found
    """
    return await admin_service.update_admin_user(
        user_id=user_id,
        request=request_data,
        updated_by=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete admin user",
    description="Soft delete an admin user. "
                "Cannot delete yourself or the last admin user. "
                "Deleted users are not permanently removed from the database.",
)
async def delete_admin_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: AdminUser,
    admin_service: AdminService = Depends(get_admin_service),
) -> None:
    """
    Soft delete admin user.

    Requires admin authentication.
    Cannot delete self or the last admin.
    User data is preserved (soft delete).

    Args:
        user_id: Admin user ID to delete
        request: FastAPI request object
        current_user: Current authenticated admin
        admin_service: Admin service instance

    Raises:
        403: If trying to delete self or last admin
        404: If admin user not found
    """
    await admin_service.delete_admin_user(
        user_id=user_id,
        deleted_by=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.put(
    "/users/{user_id}/password",
    response_model=AdminUserResponse,
    summary="Reset admin password",
    description="Reset admin user password. "
                "Password is optional - if not provided, a strong password will be generated. "
                "Returns the admin user with temporary password if generated.",
)
async def reset_admin_password(
    user_id: uuid.UUID,
    request_data: ResetPasswordRequest,
    request: Request,
    current_user: AdminUser,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminUserResponse:
    """
    Reset admin user password.

    Requires admin authentication.
    Generates password if not provided.
    Admin must change password on next login (future enhancement).

    Args:
        user_id: Admin user ID
        request_data: Password reset request (new_password optional)
        request: FastAPI request object
        current_user: Current authenticated admin
        admin_service: Admin service instance

    Returns:
        Admin user with temporary password (if generated)

    Raises:
        404: If admin user not found
        422: If password validation fails
    """
    return await admin_service.reset_admin_password(
        user_id=user_id,
        request=request_data,
        reset_by=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.put(
    "/users/{user_id}/permissions",
    response_model=AdminUserResponse,
    summary="Update admin permissions",
    description="Update admin user permissions. "
                "Cannot remove own admin privilege. "
                "Permissions follow format: resource:action[:scope]",
)
async def update_admin_permissions(
    user_id: uuid.UUID,
    request_data: UpdatePermissionsRequest,
    request: Request,
    current_user: AdminUser,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminUserResponse:
    """
    Update admin user permissions.

    Requires admin authentication.
    Cannot remove own admin privilege.
    Permissions format: resource:action[:scope]

    Examples:
        - users:read:all
        - users:write:all
        - accounts:delete:all
        - audit_logs:read:all

    Args:
        user_id: Admin user ID
        request_data: Permission update request
        request: FastAPI request object
        current_user: Current authenticated admin
        admin_service: Admin service instance

    Returns:
        Admin user with updated permissions

    Raises:
        403: If trying to remove own admin privilege
        404: If admin user not found
    """
    return await admin_service.update_admin_permissions(
        user_id=user_id,
        request=request_data,
        updated_by=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
