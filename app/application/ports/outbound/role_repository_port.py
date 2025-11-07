"""Role repository port interface."""

from typing import Optional, Protocol
from uuid import UUID

from app.domain.entities.role import Role


class RoleRepositoryPort(Protocol):
    """Repository interface for Role entity."""

    async def add(self, role: Role) -> Role:
        """
        Add a new role to the repository.

        Args:
            role: Role entity to add

        Returns:
            Created role entity with updated metadata

        Raises:
            AlreadyExistsError: If role with same name exists
        """
        ...

    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """
        Retrieve role by ID.

        Args:
            role_id: Role's unique identifier

        Returns:
            Role entity if found, None otherwise
        """
        ...

    async def get_by_name(self, name: str) -> Optional[Role]:
        """
        Retrieve role by name.

        Args:
            name: Role name

        Returns:
            Role entity if found, None otherwise
        """
        ...

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Role]:
        """
        List all roles with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of role entities
        """
        ...

    async def list_by_user(self, user_id: UUID) -> list[Role]:
        """
        List all roles assigned to a specific user.

        Args:
            user_id: User's unique identifier

        Returns:
            List of role entities assigned to the user
        """
        ...

    async def update(self, role: Role) -> Role:
        """
        Update existing role.

        Args:
            role: Role entity with updated data

        Returns:
            Updated role entity

        Raises:
            NotFoundError: If role doesn't exist
        """
        ...

    async def delete(self, role_id: UUID) -> None:
        """
        Delete role.

        Args:
            role_id: Role's unique identifier

        Raises:
            NotFoundError: If role doesn't exist
        """
        ...

    async def exists_by_name(self, name: str) -> bool:
        """
        Check if role with name exists.

        Args:
            name: Role name to check

        Returns:
            True if role exists, False otherwise
        """
        ...

    async def assign_to_user(self, role_id: UUID, user_id: UUID) -> None:
        """
        Assign role to a user.

        Args:
            role_id: Role's unique identifier
            user_id: User's unique identifier

        Raises:
            NotFoundError: If role or user doesn't exist
            AlreadyExistsError: If role already assigned to user
        """
        ...

    async def remove_from_user(self, role_id: UUID, user_id: UUID) -> None:
        """
        Remove role from a user.

        Args:
            role_id: Role's unique identifier
            user_id: User's unique identifier

        Raises:
            NotFoundError: If role or user doesn't exist
        """
        ...
