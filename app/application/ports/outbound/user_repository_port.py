"""User repository port interface."""

from typing import Optional, Protocol
from uuid import UUID

from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username


class UserRepositoryPort(Protocol):
    """Repository interface for User entity."""

    async def add(self, user: User) -> User:
        """
        Add a new user to the repository.

        Args:
            user: User entity to add

        Returns:
            Created user entity with updated metadata

        Raises:
            AlreadyExistsError: If user with same email/username exists
        """
        ...

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User entity if found, None otherwise
        """
        ...

    async def get_by_email(self, email: Email) -> Optional[User]:
        """
        Retrieve user by email address.

        Args:
            email: User's email value object

        Returns:
            User entity if found, None otherwise
        """
        ...

    async def get_by_username(self, username: Username) -> Optional[User]:
        """
        Retrieve user by username.

        Args:
            username: User's username value object

        Returns:
            User entity if found, None otherwise
        """
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[User]:
        """
        List users with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            include_inactive: Whether to include deactivated users

        Returns:
            List of user entities
        """
        ...

    async def update(self, user: User) -> User:
        """
        Update existing user.

        Args:
            user: User entity with updated data

        Returns:
            Updated user entity

        Raises:
            NotFoundError: If user doesn't exist
        """
        ...

    async def delete(self, user_id: UUID) -> None:
        """
        Hard delete user (use soft delete in practice).

        Args:
            user_id: User's unique identifier

        Raises:
            NotFoundError: If user doesn't exist
        """
        ...

    async def soft_delete(self, user_id: UUID) -> None:
        """
        Soft delete user (set deleted_at timestamp).

        Args:
            user_id: User's unique identifier

        Raises:
            NotFoundError: If user doesn't exist
        """
        ...

    async def exists_by_email(self, email: Email) -> bool:
        """
        Check if user with email exists.

        Args:
            email: Email to check

        Returns:
            True if user exists, False otherwise
        """
        ...

    async def exists_by_username(self, username: Username) -> bool:
        """
        Check if user with username exists.

        Args:
            username: Username to check

        Returns:
            True if user exists, False otherwise
        """
        ...
