"""
User management service for CRUD operations and profile management.

This module provides:
- Get user profile (self or admin)
- Update user profile
- List users with pagination and filters (admin only)
- Deactivate user (admin only)
- Soft delete user (admin only)
"""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    AlreadyExistsError,
    InsufficientPermissionsError,
    NotFoundError,
)
from models import AuditAction
from models.user import User
from repositories.refresh_token_repository import RefreshTokenRepository
from repositories.user_repository import UserRepository
from schemas.common import PaginatedResponse, PaginationMeta, PaginationParams
from schemas.user import UserFilterParams, UserListItem, UserResponse, UserUpdate
from services.audit_service import AuditService

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user management operations.

    This service handles:
    - User profile retrieval (with permission checks)
    - User profile updates (with uniqueness validation)
    - User listing and filtering (admin only)
    - User deactivation (admin only)
    - User soft deletion (admin only)

    All methods require an active database session.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize UserService with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.audit_service = AuditService(session)

    async def get_user_profile(
        self,
        user_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserResponse:
        """
        Get user profile by ID.

        Permission checks:
        - User can view their own profile
        - Admin can view any user's profile

        Args:
            user_id: User ID to retrieve
            current_user: Currently authenticated user
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            UserResponse with user data

        Raises:
            NotFoundError: If user not found
            InsufficientPermissionsError: If user lacks permission to view profile
        """
        # Check permissions: user can view self, admin can view anyone
        if user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to view user {user_id} profile without permission"
            )
            raise InsufficientPermissionsError(
                "You don't have permission to view this user's profile"
            )

        # Get user from database
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            logger.warning(f"User {user_id} not found")
            raise NotFoundError(f"User with ID {user_id}")

        # Log audit event (profile view by admin)
        if current_user.is_admin and user_id != current_user.id:
            await self.audit_service.log_event(
                user_id=current_user.id,
                action=AuditAction.READ,
                entity_type="user",
                entity_id=user_id,
                description=f"Admin {current_user.username} viewed user {user.username} profile",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )

        return UserResponse.model_validate(user)

    async def update_user_profile(
        self,
        user_id: uuid.UUID,
        update_data: UserUpdate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserResponse:
        """
        Update user profile.

        Permission checks:
        - User can update their own profile
        - Admin can update any user's profile

        Validates email and username uniqueness if changed.

        Args:
            user_id: User ID to update
            update_data: UserUpdate schema with fields to update
            current_user: Currently authenticated user
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            UserResponse with updated user data

        Raises:
            NotFoundError: If user not found
            InsufficientPermissionsError: If user lacks permission to update profile
            AlreadyExistsError: If email or username already in use
        """
        # Check permissions: user can update self, admin can update anyone
        if user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to update user {user_id} profile without permission"
            )
            raise InsufficientPermissionsError(
                "You don't have permission to update this user's profile"
            )

        # Get user from database
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            logger.warning(f"User {user_id} not found")
            raise NotFoundError(f"User with ID {user_id}")

        # Capture old values for audit log
        old_values: dict[str, Any] = {
            "email": user.email,
            "username": user.username,
        }

        # Check email uniqueness if changing email
        if update_data.email and update_data.email != user.email:
            existing_user = await self.user_repo.get_by_email(update_data.email)
            if existing_user:
                logger.warning(
                    f"Email {update_data.email} already in use by user {existing_user.id}"
                )
                raise AlreadyExistsError(
                    f"Email {update_data.email} is already registered"
                )

        # Check username uniqueness if changing username
        if update_data.username and update_data.username != user.username:
            existing_user = await self.user_repo.get_by_username(update_data.username)
            if existing_user:
                logger.warning(
                    f"Username {update_data.username} already in use by user {existing_user.id}"
                )
                raise AlreadyExistsError(
                    f"Username {update_data.username} is already taken"
                )

        # Update user fields
        update_dict = update_data.model_dump(exclude_unset=True)
        updated_user = await self.user_repo.update(user, **update_dict)

        # Capture new values for audit log
        new_values: dict[str, Any] = {
            "email": updated_user.email,
            "username": updated_user.username,
        }

        # Log audit event
        await self.audit_service.log_data_change(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user_id,
            old_values=old_values,
            new_values=new_values,
            description=f"User {current_user.username} updated profile",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        logger.info(f"User {user_id} profile updated by {current_user.id}")

        return UserResponse.model_validate(updated_user)

    async def list_users(
        self,
        pagination: PaginationParams,
        filters: UserFilterParams,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PaginatedResponse[UserListItem]:
        """
        List users with pagination and filtering.

        Permission: Admin only

        Args:
            pagination: Pagination parameters (page, page_size)
            filters: Filter parameters (is_superuser, search)
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            PaginatedResponse with list of users and pagination metadata

        Note: Soft-deleted users are automatically excluded by repository layer.

        Raises:
            InsufficientPermissionsError: If user is not admin
        """
        # Check admin permission
        if not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to list users without admin permission"
            )
            raise InsufficientPermissionsError(
                "Administrator privileges required to list users"
            )

        # Get filtered users
        users = await self.user_repo.filter_users(
            is_admin=filters.is_superuser,
            search=filters.search,
            skip=(pagination.page - 1) * pagination.page_size,
            limit=pagination.page_size,
        )

        # Get total count
        total_count = await self.user_repo.count_filtered(
            is_admin=filters.is_superuser,
            search=filters.search,
        )

        # Calculate total pages
        total_pages = (total_count + pagination.page_size - 1) // pagination.page_size

        # Convert to UserListItem schemas
        user_items = [UserListItem.model_validate(user) for user in users]

        # Log audit event
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.READ,
            entity_type="user",
            entity_id=None,
            description=f"Admin {current_user.username} listed users (page {pagination.page}, filters: {filters.model_dump(exclude_none=True)})",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        logger.info(
            f"Admin {current_user.id} listed users: page {pagination.page}, total {total_count}"
        )

        return PaginatedResponse(
            data=user_items,
            meta=PaginationMeta(
                total=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
            ),
        )

    async def deactivate_user(
        self,
        user_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Deactivate a user (soft delete).

        Permission: Admin only

        When a user is deactivated:
        - deleted_at timestamp is set (soft delete)
        - All refresh tokens are revoked
        - User cannot log in (filtered by repository)

        Args:
            user_id: User ID to deactivate
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Raises:
            InsufficientPermissionsError: If user is not admin
            NotFoundError: If user not found
        """
        # Check admin permission
        if not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to deactivate user {user_id} without admin permission"
            )
            raise InsufficientPermissionsError(
                "Administrator privileges required to deactivate users"
            )

        # Get user from database
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            logger.warning(f"User {user_id} not found")
            raise NotFoundError(f"User with ID {user_id}")

        # Soft delete the user
        await self.user_repo.delete(user)

        # Revoke all refresh tokens
        await self.token_repo.revoke_user_tokens(user_id)

        # Log audit event
        await self.audit_service.log_data_change(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="user",
            entity_id=user_id,
            old_values={},
            new_values={},
            description=f"Admin {current_user.username} deactivated (soft deleted) user {user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        logger.info(f"User {user_id} deactivated by admin {current_user.id}")

    async def soft_delete_user(
        self,
        user_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Soft delete a user (set deleted_at timestamp).

        Permission: Admin only

        When a user is soft deleted:
        - deleted_at timestamp is set
        - User is excluded from all queries (via soft delete filter)
        - All refresh tokens are revoked
        - User cannot log in
        - Data is preserved for audit/compliance (7+ years retention)

        Args:
            user_id: User ID to delete
            current_user: Currently authenticated user (must be admin)
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Raises:
            InsufficientPermissionsError: If user is not admin
            NotFoundError: If user not found
        """
        # Check admin permission
        if not current_user.is_admin:
            logger.warning(
                f"User {current_user.id} attempted to delete user {user_id} without admin permission"
            )
            raise InsufficientPermissionsError(
                "Administrator privileges required to delete users"
            )

        # Get user from database
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            logger.warning(f"User {user_id} not found")
            raise NotFoundError(f"User with ID {user_id}")

        # Soft delete user
        old_values = {"deleted_at": None}
        deleted_user = await self.user_repo.soft_delete(user)
        new_values = {
            "deleted_at": deleted_user.deleted_at.isoformat()
            if deleted_user.deleted_at
            else None
        }

        # Revoke all refresh tokens
        await self.token_repo.revoke_user_tokens(user_id)

        # Log audit event
        await self.audit_service.log_data_change(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="user",
            entity_id=user_id,
            old_values=old_values,
            new_values=new_values,
            description=f"Admin {current_user.username} soft deleted user {user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        logger.info(f"User {user_id} soft deleted by admin {current_user.id}")
