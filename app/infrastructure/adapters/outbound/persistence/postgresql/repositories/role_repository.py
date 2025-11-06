"""
PostgreSQL implementation of RoleRepositoryPort.

This repository handles all database operations for Role entities using PostgreSQL.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.outbound.role_repository_port import RoleRepositoryPort
from app.domain.entities.role import Role
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.role_mapper import (
    RoleMapper,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import (
    RoleModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.base_repository import (
    BaseRepository,
)


class PostgresRoleRepository(BaseRepository[RoleModel, Role], RoleRepositoryPort):
    """
    PostgreSQL implementation of RoleRepositoryPort.

    Inherits common CRUD operations from BaseRepository and implements
    Role-specific operations defined in RoleRepositoryPort.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize PostgreSQL role repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, RoleModel, RoleMapper)

    async def get_by_name(self, name: str) -> Optional[Role]:
        """
        Retrieve role by name.

        Args:
            name: Role name

        Returns:
            Role entity if found, None otherwise
        """
        stmt = select(RoleModel).where(RoleModel.name == name)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)

    async def list_by_user_id(self, user_id: UUID) -> list[Role]:
        """
        List all roles assigned to a user.

        Args:
            user_id: User's unique identifier

        Returns:
            List of role entities
        """
        from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import (
            UserModel,
            user_roles,
        )

        stmt = (
            select(RoleModel)
            .join(user_roles, RoleModel.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def exists_by_name(self, name: str) -> bool:
        """
        Check if role with name exists.

        Args:
            name: Role name to check

        Returns:
            True if role exists, False otherwise
        """
        from sqlalchemy import exists

        stmt = select(exists(RoleModel).where(RoleModel.name == name))
        result = await self.session.execute(stmt)
        return result.scalar()
