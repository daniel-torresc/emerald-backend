"""
Admin management service for admin user CRUD operations and management.

This module provides:
- Create admin users
- List and filter admin users
- Update admin user information
- Delete admin users (with safeguards)
- Reset admin passwords
- Manage admin permissions
"""

import logging
import secrets
import string
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.exceptions import (
    AlreadyExistsError,
    ForbiddenError,
    NotFoundError,
)
from src.models.audit_log import AuditAction
from src.models.user import User
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository
from src.schemas.admin import (
    AdminUserFilterParams,
    AdminUserListItem,
    AdminUserResponse,
    CreateAdminUserRequest,
    ResetPasswordRequest,
    UpdateAdminUserRequest,
    UpdatePermissionsRequest,
)
from src.schemas.common import PaginatedResponse, PaginationMeta
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


def generate_strong_password(length: int = 20) -> str:
    """
    Generate a cryptographically strong random password.

    Args:
        length: Length of password (default: 20 characters)

    Returns:
        Random password with letters, digits, and special characters
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))

    # Ensure password meets requirements
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower and has_digit and has_special):
        return generate_strong_password(length)

    return password


class AdminService:
    """
    Service class for admin user management operations.

    This service handles:
    - Admin user creation with role assignment
    - Admin user listing and filtering
    - Admin user updates (with business rule validation)
    - Admin user deletion (with last-admin protection)
    - Admin password resets
    - Admin permission management

    All operations are fully audited.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AdminService with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.audit_service = AuditService(session)

    async def has_any_admin(self) -> bool:
        """
        Check if any admin user exists in the system.

        Used to determine if bootstrap is needed.

        Returns:
            True if at least one admin exists, False otherwise
        """
        admin_count = await self.user_repo.count_admins()
        return admin_count > 0

    async def is_bootstrap_completed(self) -> bool:
        """
        Check if bootstrap has been completed.

        Checks the bootstrap_state table to see if initial setup was done.

        Returns:
            True if bootstrap completed, False otherwise
        """
        from sqlalchemy import select
        from src.models.bootstrap import BootstrapState

        result = await self.session.execute(select(BootstrapState))
        bootstrap = result.scalar_one_or_none()
        return bootstrap is not None and bootstrap.completed

    async def bootstrap_first_admin(
        self,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminUserResponse:
        """
        Bootstrap the first admin user using environment configuration.

        This is a special operation that can only be performed once,
        when no admin users exist in the system. All admin credentials
        are read from environment variables (BOOTSTRAP_ADMIN_*).

        Args:
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AdminUserResponse with created admin data (no password in response)

        Raises:
            ForbiddenError: If bootstrap already completed or admins exist
            AlreadyExistsError: If username or email already exists
        """
        from src.core.config import settings

        # Check if bootstrap already completed
        if await self.is_bootstrap_completed():
            raise ForbiddenError(
                "Bootstrap already completed. Only one admin user can be "
                "created via bootstrap. Use the admin API to create additional admins."
            )

        # Check if any admin users already exist (safety check)
        if await self.has_any_admin():
            raise ForbiddenError(
                "Admin user(s) already exist. Bootstrap is not needed."
            )

        # Read bootstrap configuration from environment
        username = settings.bootstrap_admin_username
        email = settings.bootstrap_admin_email
        password = settings.bootstrap_admin_password
        full_name = settings.bootstrap_admin_full_name
        permissions = settings.bootstrap_admin_permissions

        # Check username uniqueness
        if await self.user_repo.username_exists(username):
            raise AlreadyExistsError(f"Username '{username}' already exists")

        # Check email uniqueness
        if await self.user_repo.email_exists(email):
            raise AlreadyExistsError(f"Email '{email}' already exists")

        # Hash password
        password_hash = hash_password(password)

        # Get or create admin role
        admin_role = await self.role_repo.get_by_name("admin")
        if not admin_role:
            # Create default admin role if it doesn't exist
            admin_role = await self.role_repo.create(
                name="admin",
                description="System Administrator with full access",
                permissions=permissions,
            )

        # Create admin user using kwargs (BaseRepository.create expects **kwargs, not instance)
        admin_user = await self.user_repo.create(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            is_active=True,
            is_admin=True,
        )

        # Assign admin role using association table directly (avoid lazy-loading issues)
        from src.models.user import user_roles
        await self.session.execute(
            user_roles.insert().values(user_id=admin_user.id, role_id=admin_role.id)
        )
        await self.session.flush()

        # Create audit log
        await self.audit_service.log_event(
            user_id=None,  # System operation (no user context)
            action=AuditAction.CREATE,
            entity_type="user",
            entity_id=admin_user.id,
            new_values={
                "username": admin_user.username,
                "email": admin_user.email,
                "is_admin": True,
                "is_active": True,
                "full_name": admin_user.full_name,
                "bootstrap": True,
            },
            description=f"Bootstrap: Initial admin user '{admin_user.username}' created from environment config",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Mark bootstrap as completed
        from src.models.bootstrap import BootstrapState

        bootstrap = BootstrapState(
            completed=True,
            completed_at=datetime.now(UTC),
            admin_user_id=admin_user.id,
        )
        self.session.add(bootstrap)
        await self.session.flush()

        # Build response manually (User model doesn't have permissions field)
        response = AdminUserResponse(
            id=admin_user.id,
            username=admin_user.username,
            email=admin_user.email,
            full_name=admin_user.full_name,
            is_active=admin_user.is_active,
            is_admin=admin_user.is_admin,
            permissions=admin_role.permissions,
            created_at=admin_user.created_at,
            updated_at=admin_user.updated_at,
            last_login_at=admin_user.last_login_at,
            temporary_password=None,  # Never return password
        )

        return response

    async def create_admin_user(
        self,
        request: CreateAdminUserRequest,
        created_by: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminUserResponse:
        """
        Create a new admin user.

        Validates username/email uniqueness, generates password if not provided,
        assigns admin role, and creates audit log.

        Args:
            request: Admin user creation request
            created_by: Admin user creating the new admin
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AdminUserResponse with created admin data (includes temp password if generated)

        Raises:
            AlreadyExistsError: If username or email already exists
            NotFoundError: If admin role doesn't exist
        """
        # Check username uniqueness
        if await self.user_repo.username_exists(request.username):
            raise AlreadyExistsError(f"Username '{request.username}' already exists")

        # Check email uniqueness
        if await self.user_repo.email_exists(request.email):
            raise AlreadyExistsError(f"Email '{request.email}' already exists")

        # Generate password if not provided
        generated_password = None
        if request.password is None:
            password = generate_strong_password()
            generated_password = password
        else:
            password = request.password

        # Hash password
        password_hash = hash_password(password)

        # Get or create admin role
        admin_role = await self.role_repo.get_by_name("admin")
        if not admin_role:
            # Create default admin role if it doesn't exist
            admin_role = await self.role_repo.create(
                name="admin",
                description="System Administrator with full access",
                permissions=request.permissions or [
                    "users:read:all",
                    "users:write:all",
                    "users:delete:all",
                    "accounts:read:all",
                    "accounts:write:all",
                    "accounts:delete:all",
                    "transactions:read:all",
                    "transactions:write:all",
                    "transactions:delete:all",
                    "audit_logs:read:all",
                    "admin:manage:all",
                ],
            )

        # Create admin user using kwargs (BaseRepository.create expects **kwargs, not instance)
        admin_user = await self.user_repo.create(
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            full_name=request.full_name,
            is_active=True,
            is_admin=True,
        )

        # Assign admin role using association table directly (avoid lazy-loading issues)
        from src.models.user import user_roles
        await self.session.execute(
            user_roles.insert().values(user_id=admin_user.id, role_id=admin_role.id)
        )
        await self.session.flush()

        # Create audit log
        await self.audit_service.log_event(
            user_id=created_by.id,
            action=AuditAction.CREATE,
            entity_type="user",
            entity_id=admin_user.id,
            new_values={
                "username": admin_user.username,
                "email": admin_user.email,
                "is_admin": True,
                "is_active": True,
                "full_name": admin_user.full_name,
                "created_by": created_by.username,
            },
            description=f"Admin {created_by.username} created admin user {admin_user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Build response manually (User model doesn't have permissions field)
        response = AdminUserResponse(
            id=admin_user.id,
            username=admin_user.username,
            email=admin_user.email,
            full_name=admin_user.full_name,
            is_active=admin_user.is_active,
            is_admin=admin_user.is_admin,
            permissions=admin_role.permissions,
            created_at=admin_user.created_at,
            updated_at=admin_user.updated_at,
            last_login_at=admin_user.last_login_at,
            temporary_password=generated_password,
        )

        return response

    async def list_admin_users(
        self,
        filters: AdminUserFilterParams,
    ) -> PaginatedResponse[AdminUserListItem]:
        """
        List admin users with pagination and filtering.

        Args:
            filters: Filter parameters (search, is_active, pagination)

        Returns:
            Paginated response with admin user list items
        """
        # Get admin users
        users = await self.user_repo.filter_users(
            search=filters.search,
            is_active=filters.is_active,
            is_admin=True,  # Only admin users
            skip=filters.skip,
            limit=filters.limit,
        )

        # Get total count
        total = await self.user_repo.count_filtered(
            search=filters.search,
            is_active=filters.is_active,
            is_admin=True,
        )

        # Calculate pagination metadata
        total_pages = (total + filters.limit - 1) // filters.limit
        current_page = (filters.skip // filters.limit) + 1

        # Build response
        items = [AdminUserListItem.model_validate(user) for user in users]

        return PaginatedResponse(
            data=items,
            meta=PaginationMeta(
                total=total,
                page=current_page,
                page_size=filters.limit,
                total_pages=total_pages,
            ),
        )

    async def get_admin_user(
        self,
        user_id: uuid.UUID,
        current_user: User,
    ) -> AdminUserResponse:
        """
        Get admin user by ID.

        Args:
            user_id: Admin user ID
            current_user: Current authenticated admin

        Returns:
            AdminUserResponse with admin user data

        Raises:
            NotFoundError: If user not found or not an admin
        """
        user = await self.user_repo.get_with_roles(user_id)

        if not user:
            raise NotFoundError(f"User with ID {user_id}")

        if not user.is_admin:
            raise NotFoundError(f"Admin user with ID {user_id}")

        # Get permissions from roles
        permissions = [perm for role in user.roles for perm in role.permissions]

        # Build response manually (User model doesn't have permissions field)
        response = AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            permissions=permissions,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            temporary_password=None,
        )

        return response

    async def update_admin_user(
        self,
        user_id: uuid.UUID,
        request: UpdateAdminUserRequest,
        updated_by: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminUserResponse:
        """
        Update admin user information.

        Only allows updating full_name and is_active.
        Cannot deactivate the last admin.

        Args:
            user_id: Admin user ID to update
            request: Update request with fields to change
            updated_by: Admin user performing the update
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AdminUserResponse with updated admin data

        Raises:
            NotFoundError: If user not found or not an admin
            ForbiddenError: If trying to deactivate the last admin
        """
        # Get user
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundError(f"User with ID {user_id}")

        if not user.is_admin:
            raise NotFoundError(f"Admin user with ID {user_id}")

        # Check if deactivating last admin
        if request.is_active is False and user.is_active:
            admin_count = await self.user_repo.count_admins()
            if admin_count <= 1:
                raise ForbiddenError("Cannot deactivate the last admin user")

        # Store old values for audit
        old_values = {
            "full_name": user.full_name,
            "is_active": user.is_active,
        }

        # Update fields
        if request.full_name is not None:
            user.full_name = request.full_name

        if request.is_active is not None:
            user.is_active = request.is_active

        user.updated_at = datetime.now(UTC)

        await self.session.flush()

        # Create audit log
        await self.audit_service.log_event(
            user_id=updated_by.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user_id,
            old_values=old_values,
            new_values={
                "full_name": user.full_name,
                "is_active": user.is_active,
            },
            description=f"Admin {updated_by.username} updated admin user {user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Get updated user with roles
        user = await self.user_repo.get_with_roles(user_id)
        permissions = [perm for role in user.roles for perm in role.permissions]

        # Build response manually (User model doesn't have permissions field)
        response = AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            permissions=permissions,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            temporary_password=None,
        )

        return response

    async def delete_admin_user(
        self,
        user_id: uuid.UUID,
        deleted_by: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Soft delete admin user.

        Cannot delete self or the last admin.

        Args:
            user_id: Admin user ID to delete
            deleted_by: Admin user performing the deletion
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Raises:
            NotFoundError: If user not found or not an admin
            ForbiddenError: If trying to delete self or last admin
        """
        # Check if trying to delete self
        if user_id == deleted_by.id:
            raise ForbiddenError("Cannot delete your own admin account")

        # Get user
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundError(f"User with ID {user_id}")

        if not user.is_admin:
            raise NotFoundError(f"Admin user with ID {user_id}")

        # Check if deleting last admin
        admin_count = await self.user_repo.count_admins()
        if admin_count <= 1:
            raise ForbiddenError("Cannot delete the last admin user")

        # Soft delete user
        await self.user_repo.delete(user)

        # Create audit log
        await self.audit_service.log_event(
            user_id=deleted_by.id,
            action=AuditAction.DELETE,
            entity_type="user",
            entity_id=user_id,
            old_values={
                "username": user.username,
                "email": user.email,
                "is_admin": True,
            },
            description=f"Admin {deleted_by.username} deleted admin user {user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def reset_admin_password(
        self,
        user_id: uuid.UUID,
        request: ResetPasswordRequest,
        reset_by: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminUserResponse:
        """
        Reset admin user password.

        Generates a new password if not provided.

        Args:
            user_id: Admin user ID
            request: Password reset request
            reset_by: Admin user performing the reset
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AdminUserResponse with temporary password if generated

        Raises:
            NotFoundError: If user not found or not an admin
        """
        # Get user
        user = await self.user_repo.get_with_roles(user_id)

        if not user:
            raise NotFoundError(f"User with ID {user_id}")

        if not user.is_admin:
            raise NotFoundError(f"Admin user with ID {user_id}")

        # Generate password if not provided
        generated_password = None
        if request.new_password is None:
            password = generate_strong_password()
            generated_password = password
        else:
            password = request.new_password

        # Hash password
        user.password_hash = hash_password(password)
        user.updated_at = datetime.now(UTC)

        await self.session.flush()

        # Create audit log
        await self.audit_service.log_event(
            user_id=reset_by.id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user_id,
            description=f"Admin {reset_by.username} reset password for admin user {user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Get permissions
        permissions = [perm for role in user.roles for perm in role.permissions]

        # Build response manually (User model doesn't have permissions field)
        response = AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            permissions=permissions,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            temporary_password=generated_password,
        )

        return response

    async def update_admin_permissions(
        self,
        user_id: uuid.UUID,
        request: UpdatePermissionsRequest,
        updated_by: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminUserResponse:
        """
        Update admin user permissions.

        Cannot remove own admin privilege.

        Args:
            user_id: Admin user ID
            request: Permission update request
            updated_by: Admin user performing the update
            request_id: Request ID for audit logging
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            AdminUserResponse with updated permissions

        Raises:
            NotFoundError: If user not found or not an admin
            ForbiddenError: If trying to remove own admin privilege
        """
        # Check if updating self
        if user_id == updated_by.id:
            # Ensure not removing admin privilege
            has_admin_perm = any("admin:" in perm for perm in request.permissions)
            if not has_admin_perm:
                raise ForbiddenError("Cannot remove your own admin privileges")

        # Get user
        user = await self.user_repo.get_with_roles(user_id)

        if not user:
            raise NotFoundError(f"User with ID {user_id}")

        if not user.is_admin:
            raise NotFoundError(f"Admin user with ID {user_id}")

        # Get current permissions from all user's roles
        old_permissions = [perm for role in user.roles for perm in role.permissions]

        # Create or get a user-specific admin role
        user_role_name = f"admin_{user_id}"
        user_specific_role = await self.role_repo.get_by_name(user_role_name)

        if not user_specific_role:
            # Create new user-specific role with requested permissions
            user_specific_role = await self.role_repo.create(
                name=user_role_name,
                description=f"Custom admin permissions for {user.username}",
                permissions=request.permissions,
            )
            # Add to user's roles
            from src.models.user import user_roles
            await self.session.execute(
                user_roles.insert().values(user_id=user.id, role_id=user_specific_role.id)
            )
        else:
            # Update existing user-specific role
            user_specific_role.permissions = request.permissions

        await self.session.flush()

        # Create audit log
        await self.audit_service.log_event(
            user_id=updated_by.id,
            action=AuditAction.PERMISSION_GRANT,
            entity_type="user",
            entity_id=user_id,
            old_values={"permissions": old_permissions},
            new_values={"permissions": request.permissions},
            description=f"Admin {updated_by.username} updated permissions for admin user {user.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Build response manually (User model doesn't have permissions field)
        response = AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            permissions=request.permissions,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            temporary_password=None,
        )

        return response
