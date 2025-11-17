"""
AccountShare repository for database operations.

This module provides database operations for AccountShare model, including:
- Standard CRUD operations (inherited from BaseRepository)
- Permission lookups: get user's permission for an account
- Share queries: get all shares for an account, get all accounts shared with user
- Validation queries: check if share exists
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import AccountShare
from src.models.enums import PermissionLevel
from src.repositories.base import BaseRepository


class AccountShareRepository(BaseRepository[AccountShare]):
    """
    Repository for AccountShare model database operations.

    Provides share-specific queries in addition to base CRUD operations.
    Automatically filters soft-deleted shares in all queries.

    Usage:
        share_repo = AccountShareRepository(session)
        share = await share_repo.get_user_permission(user_id, account_id)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AccountShare repository.

        Args:
            session: Async database session
        """
        super().__init__(AccountShare, session)

    async def get_user_permission(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> AccountShare | None:
        """
        Get user's permission level for a specific account.

        This is the primary method for permission checking.

        Args:
            user_id: ID of the user
            account_id: ID of the account

        Returns:
            AccountShare instance with permission level, or None if no access

        Example:
            share = await share_repo.get_user_permission(user.id, account.id)
            if share and share.permission_level == PermissionLevel.OWNER:
                # User is owner
        """
        query = select(AccountShare).where(
            AccountShare.user_id == user_id,
            AccountShare.account_id == account_id,
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_account(
        self,
        account_id: uuid.UUID,
        permission_level: PermissionLevel | None = None,
    ) -> list[AccountShare]:
        """
        Get all shares for a specific account.

        Useful for listing who has access to an account.

        Args:
            account_id: ID of the account
            permission_level: Optional filter by permission level

        Returns:
            List of AccountShare instances

        Example:
            # Get all shares for account
            shares = await share_repo.get_by_account(account.id)

            # Get only viewers
            viewers = await share_repo.get_by_account(
                account.id,
                permission_level=PermissionLevel.VIEWER
            )
        """
        query = select(AccountShare).where(AccountShare.account_id == account_id)
        query = self._apply_soft_delete_filter(query)

        if permission_level is not None:
            query = query.where(AccountShare.permission_level == permission_level)

        # Order by permission level (owner first, then editor, then viewer)
        # and then by created_at
        query = query.order_by(
            AccountShare.permission_level.desc(),
            AccountShare.created_at.desc(),
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        permission_level: PermissionLevel | None = None,
    ) -> list[AccountShare]:
        """
        Get all accounts shared with a specific user.

        Useful for listing accounts a user has access to (besides their own).

        Args:
            user_id: ID of the user
            permission_level: Optional filter by permission level

        Returns:
            List of AccountShare instances

        Example:
            # Get all accounts shared with user
            shared_accounts = await share_repo.get_by_user(user.id)

            # Get only accounts where user is editor
            editor_accounts = await share_repo.get_by_user(
                user.id,
                permission_level=PermissionLevel.EDITOR
            )
        """
        query = select(AccountShare).where(AccountShare.user_id == user_id)
        query = self._apply_soft_delete_filter(query)

        if permission_level is not None:
            query = query.where(AccountShare.permission_level == permission_level)

        # Order by created_at descending (newest first)
        query = query.order_by(AccountShare.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def exists_share(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """
        Check if an active share exists for user and account.

        Useful for validating uniqueness before creating shares.

        Args:
            user_id: ID of the user
            account_id: ID of the account
            exclude_id: Optional share ID to exclude (for updates)

        Returns:
            True if active share exists, False otherwise

        Example:
            # Before creating share
            if await share_repo.exists_share(user.id, account.id):
                raise AlreadyExistsError("Account already shared with user")

            # Before updating share (exclude current one)
            if await share_repo.exists_share(
                user.id, account.id, exclude_id=share.id
            ):
                raise AlreadyExistsError("Duplicate share")
        """
        query = select(AccountShare).where(
            AccountShare.user_id == user_id,
            AccountShare.account_id == account_id,
        )
        query = self._apply_soft_delete_filter(query)

        # Exclude the share being updated
        if exclude_id is not None:
            query = query.where(AccountShare.id != exclude_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_owner_share(
        self,
        account_id: uuid.UUID,
    ) -> AccountShare | None:
        """
        Get the owner share for an account.

        Every account should have exactly one owner share.

        Args:
            account_id: ID of the account

        Returns:
            AccountShare instance with owner permission, or None if not found

        Example:
            owner_share = await share_repo.get_owner_share(account.id)
            if owner_share:
                owner_user_id = owner_share.user_id
        """
        query = select(AccountShare).where(
            AccountShare.account_id == account_id,
            AccountShare.permission_level == PermissionLevel.owner,
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
