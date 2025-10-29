"""
Role repository for role-based access control operations.

This module provides database operations for the Role model,
including role lookups and permission management.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import Role, User
from src.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """
    Repository for Role model operations.

    Extends BaseRepository with role-specific queries:
    - Role name lookups
    - User permission retrieval
    - Role assignment operations
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize RoleRepository.

        Args:
            session: Async database session
        """
        super().__init__(Role, session)

    async def get_by_name(self, name: str) -> Role | None:
        """
        Get role by name.

        Args:
            name: Role name to search for (e.g., "admin", "user")

        Returns:
            Role instance or None if not found

        Example:
            admin_role = await role_repo.get_by_name("admin")
            if admin_role is None:
                raise NotFoundError("Role")
        """
        query = select(Role).where(Role.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_permissions(self, user_id: uuid.UUID) -> set[str]:
        """
        Get all permissions for a user across all their roles.

        This aggregates permissions from all roles assigned to the user.
        Used for permission checking in authorization logic.

        Args:
            user_id: UUID of the user

        Returns:
            Set of permission strings

        Example:
            permissions = await role_repo.get_user_permissions(user_id)
            if "users:write:all" not in permissions:
                raise InsufficientPermissionsError()
        """
        # Query user with roles loaded
        user_query = select(User).where(User.id == user_id)
        user_result = await self.session.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            return set()

        # Aggregate permissions from all roles
        permissions: set[str] = set()
        for role in user.roles:
            permissions.update(role.permissions)

        return permissions

    async def get_default_user_role(self) -> Role | None:
        """
        Get the default "user" role.

        This role is assigned to all new users during registration.

        Returns:
            Role instance for "user" role, or None if not found

        Example:
            default_role = await role_repo.get_default_user_role()
            if default_role:
                user.roles.append(default_role)
        """
        return await self.get_by_name("user")

    async def get_all_roles(self) -> list[Role]:
        """
        Get all roles in the system.

        Used for admin role management UI.

        Returns:
            List of all Role instances

        Example:
            roles = await role_repo.get_all_roles()
            for role in roles:
                print(f"{role.name}: {role.permissions}")
        """
        query = select(Role).order_by(Role.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())
