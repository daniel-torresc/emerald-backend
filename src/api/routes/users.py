"""
User management API routes.

This module provides:
- GET /api/v1/users/me - Get current user profile
- PATCH /api/v1/users/me - Update current user profile
- GET /api/v1/users/{user_id} - Get specific user profile (admin or self)
- GET /api/v1/users - List all users (admin only, paginated)
- POST /api/v1/users/{user_id}/deactivate - Deactivate user (admin only)
- DELETE /api/v1/users/{user_id} - Soft delete user (admin only)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Request, status

from src.api.dependencies import AdminUser, CurrentUser, UserServiceDep
from src.schemas.common import PaginatedResponse, PaginationParams
from src.schemas.user import UserFilterParams, UserListItem, UserResponse, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user",
)
async def get_current_user_profile(
    request: Request,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> UserResponse:
    """
    Get current user's profile.

    Returns:
        UserResponse with current user's data

    Requires:
        - Valid access token
        - Active user account
    """

    return await user_service.get_user_profile(
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
    current_user: CurrentUser,
    user_service: UserServiceDep,
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

    return await user_service.update_user_profile(
        user_id=current_user.id,
        update_data=update_data,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# ============================================================================
# User Lookup Endpoints
# ============================================================================


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get specific user profile",
    description="Get a specific user's profile (admin can view any, users can view self)",
)
async def get_user_by_id(
    request: Request,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    user_service: UserServiceDep,
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

    return await user_service.get_user_profile(
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
    current_user: AdminUser,
    user_service: UserServiceDep,
    pagination: PaginationParams = Depends(),
    filters: UserFilterParams = Depends(),
) -> PaginatedResponse[UserListItem]:
    """
    List all users with pagination and filtering.

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
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

    return await user_service.list_users(
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
    current_user: AdminUser,
    user_service: UserServiceDep,
) -> None:
    """
    Deactivate a user account.

    Path parameters:
        - user_id: UUID of user to deactivate

    Effects:
        - Soft deletes user (sets deleted_at timestamp)
        - Revokes all refresh tokens
        - User cannot log in (filtered by repository)

    Requires:
        - Valid access token
        - Active user account
        - Admin privileges

    Raises:
        - 403 Forbidden: If user is not admin
        - 404 Not Found: If user not found
    """

    await user_service.deactivate_user(
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
    current_user: AdminUser,
    user_service: UserServiceDep,
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

    await user_service.soft_delete_user(
        user_id=user_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
