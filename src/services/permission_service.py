"""
Permission service for account access control.

This module provides centralized permission checking logic for accounts.
Implements a hierarchical permission model: OWNER > EDITOR > VIEWER.

Permission Levels:
    - OWNER: Full access (read, write, delete, manage sharing)
    - EDITOR: Read/write access (cannot delete or manage sharing)
    - VIEWER: Read-only access

Usage:
    permission_service = PermissionService(session)
    has_access = await permission_service.check_permission(
        user_id=user.id,
        account_id=account.id,
        required_permission=PermissionLevel.VIEWER
    )
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import InsufficientPermissionsError, NotFoundError
from src.models.enums import PermissionLevel
from src.repositories.account_repository import AccountRepository
from src.repositories.account_share_repository import AccountShareRepository


class PermissionService:
    """
    Service for checking account access permissions.

    Provides methods to check if a user has required permission for an account
    based on the hierarchical permission model.

    Permission Hierarchy:
        OWNER (3) > EDITOR (2) > VIEWER (1)

    A user with OWNER permission can do everything an EDITOR or VIEWER can do.
    A user with EDITOR permission can do everything a VIEWER can do.
    """

    # Permission hierarchy mapping (higher number = more permissions)
    PERMISSION_HIERARCHY = {
        PermissionLevel.viewer: 1,
        PermissionLevel.editor: 2,
        PermissionLevel.owner: 3,
    }

    def __init__(self, session: AsyncSession):
        """
        Initialize permission service.

        Args:
            session: Async database session
        """
        self.session = session
        self.account_repo = AccountRepository(session)
        self.share_repo = AccountShareRepository(session)

    async def get_user_permission(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> PermissionLevel | None:
        """
        Get user's permission level for an account.

        Checks implicit ownership first (via Account.user_id), then explicit shares.
        This means the account owner doesn't need an AccountShare entry.

        Args:
            user_id: ID of the user
            account_id: ID of the account

        Returns:
            PermissionLevel if user has access, None otherwise

        Example:
            permission = await permission_service.get_user_permission(
                user.id, account.id
            )
            if permission == PermissionLevel.OWNER:
                # User is owner
        """
        # First check: Is the user the account owner? (implicit ownership)
        account = await self.account_repo.get_by_id(account_id)
        if account and account.user_id == user_id:
            return PermissionLevel.owner

        # Second check: Is there an explicit share?
        share = await self.share_repo.get_user_permission(user_id, account_id)
        if share is None:
            return None

        return share.permission_level

    async def check_permission(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        required_permission: PermissionLevel,
    ) -> bool:
        """
        Check if user has required permission for account.

        Uses permission hierarchy: owner > editor > viewer.
        Returns True if user's permission level meets or exceeds the required level.

        Args:
            user_id: ID of the user
            account_id: ID of the account
            required_permission: Minimum required permission level

        Returns:
            True if user has sufficient permission, False otherwise

        Example:
            # Check if user can read account (viewer or higher)
            can_read = await permission_service.check_permission(
                user.id,
                account.id,
                PermissionLevel.VIEWER
            )

            # Check if user can modify account (editor or higher)
            can_write = await permission_service.check_permission(
                user.id,
                account.id,
                PermissionLevel.EDITOR
            )

            # Check if user is owner
            is_owner = await permission_service.check_permission(
                user.id,
                account.id,
                PermissionLevel.OWNER
            )
        """
        user_permission = await self.get_user_permission(user_id, account_id)

        if user_permission is None:
            return False

        # Check if user's permission level meets or exceeds required level
        return (
            self.PERMISSION_HIERARCHY[user_permission]
            >= self.PERMISSION_HIERARCHY[required_permission]
        )

    async def require_permission(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        required_permission: PermissionLevel,
    ) -> None:
        """
        Require user to have specific permission, raise exception if not.

        This is a convenience method for enforcing permissions in services.

        Args:
            user_id: ID of the user
            account_id: ID of the account
            required_permission: Required permission level

        Raises:
            NotFoundError: If user has no access to the account
            InsufficientPermissionsError: If user lacks required permission

        Example:
            # Require owner permission (raises exception if not owner)
            await permission_service.require_permission(
                user.id,
                account.id,
                PermissionLevel.OWNER
            )
            # If we get here, user is owner - proceed with operation
        """
        user_permission = await self.get_user_permission(user_id, account_id)

        if user_permission is None:
            raise NotFoundError("Account not found or you don't have access")

        if (
            self.PERMISSION_HIERARCHY[user_permission]
            < self.PERMISSION_HIERARCHY[required_permission]
        ):
            raise InsufficientPermissionsError(
                f"You don't have permission to perform this action. "
                f"Required: {required_permission.value}, "
                f"Current: {user_permission.value}"
            )

    async def is_owner(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> bool:
        """
        Check if user is the owner of an account.

        Convenience method for common owner check.

        Args:
            user_id: ID of the user
            account_id: ID of the account

        Returns:
            True if user is owner, False otherwise

        Example:
            if await permission_service.is_owner(user.id, account.id):
                # User is owner, can delete account
        """
        return await self.check_permission(
            user_id, account_id, PermissionLevel.owner
        )

    async def can_read(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> bool:
        """
        Check if user can read account (viewer or higher).

        Convenience method for read permission check.

        Args:
            user_id: ID of the user
            account_id: ID of the account

        Returns:
            True if user can read, False otherwise

        Example:
            if await permission_service.can_read(user.id, account.id):
                # Show account details
        """
        return await self.check_permission(
            user_id, account_id, PermissionLevel.viewer
        )

    async def can_write(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> bool:
        """
        Check if user can write to account (editor or higher).

        Convenience method for write permission check.

        Args:
            user_id: ID of the user
            account_id: ID of the account

        Returns:
            True if user can write, False otherwise

        Example:
            if await permission_service.can_write(user.id, account.id):
                # Allow account updates
        """
        return await self.check_permission(
            user_id, account_id, PermissionLevel.editor
        )
