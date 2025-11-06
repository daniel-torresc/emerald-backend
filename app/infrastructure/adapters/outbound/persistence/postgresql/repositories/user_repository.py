"""
PostgreSQL implementation of UserRepositoryPort.

This repository handles all database operations for User entities using PostgreSQL.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.ports.outbound.user_repository_port import UserRepositoryPort
from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.user_mapper import (
    UserMapper,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import (
    UserModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.base_repository import (
    BaseRepository,
)


class PostgresUserRepository(BaseRepository[UserModel, User], UserRepositoryPort):
    """
    PostgreSQL implementation of UserRepositoryPort.

    Inherits common CRUD operations from BaseRepository and implements
    User-specific operations defined in UserRepositoryPort.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize PostgreSQL user repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, UserModel, UserMapper)

    async def get_by_email(self, email: Email) -> Optional[User]:
        """
        Retrieve user by email address.

        Args:
            email: User's email value object

        Returns:
            User entity if found, None otherwise
        """
        stmt = (
            select(UserModel)
            .where(
                UserModel.email == email.value,
                UserModel.deleted_at.is_(None),
            )
            .options(selectinload(UserModel.roles))  # Eager load roles
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)

    async def get_by_username(self, username: Username) -> Optional[User]:
        """
        Retrieve user by username.

        Args:
            username: User's username value object

        Returns:
            User entity if found, None otherwise
        """
        stmt = (
            select(UserModel)
            .where(
                UserModel.username == username.value,
                UserModel.deleted_at.is_(None),
            )
            .options(selectinload(UserModel.roles))  # Eager load roles
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)

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
        # Build query
        stmt = select(UserModel).options(selectinload(UserModel.roles))

        # Filter soft-deleted users
        stmt = stmt.where(UserModel.deleted_at.is_(None))

        # Filter inactive users if needed
        if not include_inactive:
            stmt = stmt.where(UserModel.is_active.is_(True))

        # Add pagination
        stmt = stmt.offset(skip).limit(limit)

        # Order by created_at
        stmt = stmt.order_by(UserModel.created_at.desc())

        # Execute query
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def exists_by_email(self, email: Email) -> bool:
        """
        Check if user with email exists.

        Args:
            email: Email to check

        Returns:
            True if user exists, False otherwise
        """
        from sqlalchemy import exists

        stmt = select(
            exists(UserModel).where(
                UserModel.email == email.value,
                UserModel.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def exists_by_username(self, username: Username) -> bool:
        """
        Check if user with username exists.

        Args:
            username: Username to check

        Returns:
            True if user exists, False otherwise
        """
        from sqlalchemy import exists

        stmt = select(
            exists(UserModel).where(
                UserModel.username == username.value,
                UserModel.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    # Override get_by_id to include eager loading of roles
    async def get_by_id(self, user_id: UUID, include_deleted: bool = False) -> Optional[User]:
        """
        Retrieve user by ID with eager loaded roles.

        Args:
            user_id: User's unique identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            User entity if found, None otherwise
        """
        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.roles))  # Eager load roles
        )

        if not include_deleted:
            stmt = stmt.where(UserModel.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)
