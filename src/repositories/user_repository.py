"""
User repository for user-specific database operations.

This module provides database operations for the User model,
including authentication queries, profile management, and user filtering.
"""

import uuid

from pydantic import EmailStr
from sqlalchemy import ColumnElement, UnaryExpression, asc, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from schemas import PaginationParams, SortOrder, UserFilterParams, UserSortParams
from .base import BaseRepository


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

    @staticmethod
    def _build_filters(
        params: UserFilterParams,
    ) -> list[ColumnElement[bool]]:
        """
        Convert UserFilterParams to SQLAlchemy filter expressions.

        Args:
            params: Filter parameters from request

        Returns:
            List of SQLAlchemy filter expressions
        """
        filters: list[ColumnElement[bool]] = []

        # Admin status filter
        if params.is_admin is not None:
            filters.append(User.is_admin == params.is_admin)

        # Search filter (email, username, or full_name)
        if params.search:
            search_term = f"%{params.search}%"
            filters.append(
                or_(
                    User.email.ilike(search_term),
                    User.username.ilike(search_term),
                    User.full_name.ilike(search_term),
                )
            )

        return filters

    @staticmethod
    def _build_order_by(
        params: UserSortParams,
    ) -> list[UnaryExpression]:
        """
        Convert UserSortParams to SQLAlchemy order_by expressions.

        Args:
            params: Sort parameters with sort_by and sort_order

        Returns:
            List of SQLAlchemy order_by expressions
        """
        order_by: list[UnaryExpression] = []

        # Get the model column from enum value
        sort_column = getattr(User, params.sort_by.value)

        # Apply sort direction
        if params.sort_order == SortOrder.ASC:
            order_by.append(asc(sort_column))
        else:
            order_by.append(desc(sort_column))

        # Add secondary sort by id for deterministic pagination
        order_by.append(desc(User.id))

        return order_by

    async def list_users(
        self,
        filter_params: UserFilterParams,
        sort_params: UserSortParams,
        pagination_params: PaginationParams,
    ) -> tuple[list[User], int]:
        """
        Filter users with multiple criteria and pagination.

        Used for admin user list view with search and filtering.
        Automatically filters out soft-deleted users via BaseRepository.

        Args:
            filter_params:
            sort_params:
            pagination_params:

        Returns:
            List of User instances matching the criteria

        Example:
            # Get non-admin users with "john" in name/email
            users = await user_repo.filter_users(
                search="john",
                is_admin=False,
                skip=0,
                limit=20
            )
        """
        filters = self._build_filters(params=filter_params)
        order_by = self._build_order_by(params=sort_params)

        return await self._list_and_count(
            filters=filters,
            order_by=order_by,
            offset=pagination_params.offset,
            limit=pagination_params.page_size,
        )

    async def get_by_email(self, email: EmailStr) -> User | None:
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
        query = select(User).where(User.email == email)
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
        query = select(User).where(User.username == username)
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

    async def email_exists(
        self, email: EmailStr, exclude_user_id: uuid.UUID | None = None
    ) -> bool:
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

    async def username_exists(
        self, username: str, exclude_user_id: uuid.UUID | None = None
    ) -> bool:
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
