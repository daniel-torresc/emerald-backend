"""
User repository for user-specific database operations.

This module provides database operations for the User model,
including authentication queries, profile management, and user filtering.
"""

import uuid

from pydantic import EmailStr
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Repository for User model operations.

    Extends BaseRepository with user-specific queries:
    - Email and username lookups (for authentication)
    - User filtering (for admin list view)
    - Role loading (for permission checks)
    - Activity tracking (last login updates)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize UserRepository.

        Args:
            session: Async database session
        """
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Automatically filters out soft-deleted users.
        Eager loads user roles for permission checks.

        Args:
            email: Email address to search for

        Returns:
            User instance or None if not found

        Example:
            user = await user_repo.get_by_email("john@example.com")
            if user is None:
                raise InvalidCredentialsError()
        """
        query = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.roles))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """
        Get user by username.

        Automatically filters out soft-deleted users.
        Eager loads user roles for permission checks.

        Args:
            username: Username to search for

        Returns:
            User instance or None if not found

        Example:
            user = await user_repo.get_by_username("johndoe")
        """
        query = (
            select(User)
            .where(User.username == username)
            .options(selectinload(User.roles))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: uuid.UUID) -> User | None:
        """
        Get user by ID with roles eager loaded.

        Useful when you need to check permissions immediately after
        fetching the user.

        Args:
            user_id: UUID of the user

        Returns:
            User instance with roles loaded, or None if not found

        Example:
            user = await user_repo.get_with_roles(user_id)
            if user is None:
                raise NotFoundError("User")

            # Roles are already loaded, no additional query
            permissions = [perm for role in user.roles for perm in role.permissions]
        """
        query = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """
        Update user's last login timestamp to current time.

        This is called after successful authentication to track
        user activity.

        Args:
            user_id: UUID of the user

        Example:
            # After successful login
            await user_repo.update_last_login(user.id)
        """
        from datetime import UTC, datetime

        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(UTC)
            await self.session.flush()

    async def filter_users(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """
        Filter users with multiple criteria and pagination.

        Used for admin user list view with search and filtering.
        Automatically filters out soft-deleted users.

        Args:
            search: Search term for username, email, or full_name
            is_active: Filter by active status
            is_admin: Filter by admin status
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of User instances matching the criteria

        Example:
            # Get active non-admin users with "john" in name/email
            users = await user_repo.filter_users(
                search="john",
                is_active=True,
                is_admin=False,
                skip=0,
                limit=20
            )
        """
        query = select(User).options(selectinload(User.roles))
        query = self._apply_soft_delete_filter(query)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern),
                )
            )

        # Apply status filters
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        if is_admin is not None:
            query = query.where(User.is_admin == is_admin)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Order by created_at descending (newest first)
        query = query.order_by(User.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> int:
        """
        Count users matching filter criteria.

        Used for pagination metadata in admin user list.

        Args:
            search: Search term for username, email, or full_name
            is_active: Filter by active status
            is_admin: Filter by admin status

        Returns:
            Total count of users matching criteria

        Example:
            total = await user_repo.count_filtered(
                search="john",
                is_active=True
            )
            total_pages = (total + limit - 1) // limit
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(User)
        query = self._apply_soft_delete_filter(query)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern),
                )
            )

        # Apply status filters
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        if is_admin is not None:
            query = query.where(User.is_admin == is_admin)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def email_exists(self, email: EmailStr, exclude_user_id: uuid.UUID | None = None) -> bool:
        """
        Check if email is already in use by another user.

        Useful for validation during user creation and profile updates.
        Automatically filters out soft-deleted users.

        Args:
            email: Email address to check
            exclude_user_id: User ID to exclude from check (for updates)

        Returns:
            True if email exists, False otherwise

        Example:
            # During user creation
            if await user_repo.email_exists(email):
                raise AlreadyExistsError("User with this email")

            # During profile update
            if await user_repo.email_exists(new_email, exclude_user_id=user.id):
                raise AlreadyExistsError("User with this email")
        """
        query = select(User).where(User.email == email)
        query = self._apply_soft_delete_filter(query)

        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def username_exists(self, username: str, exclude_user_id: uuid.UUID | None = None) -> bool:
        """
        Check if username is already in use by another user.

        Useful for validation during user creation and profile updates.
        Automatically filters out soft-deleted users.

        Args:
            username: Username to check
            exclude_user_id: User ID to exclude from check (for updates)

        Returns:
            True if username exists, False otherwise

        Example:
            # During user creation
            if await user_repo.username_exists(username):
                raise AlreadyExistsError("User with this username")

            # During profile update
            if await user_repo.username_exists(new_username, exclude_user_id=user.id):
                raise AlreadyExistsError("User with this username")
        """
        query = select(User).where(User.username == username)
        query = self._apply_soft_delete_filter(query)

        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
