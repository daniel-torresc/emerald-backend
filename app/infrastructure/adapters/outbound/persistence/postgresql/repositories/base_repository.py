"""
Base repository class for common database operations.

This provides generic CRUD operations that all repositories can inherit from.
It uses SQLAlchemy AsyncSession and handles common patterns like:
- Soft delete filtering
- Pagination
- Entity ↔ Model conversion via mappers
"""

from typing import Generic, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.adapters.outbound.persistence.postgresql.models.base import Base

# Type variables for generic repository
TModel = TypeVar("TModel", bound=Base)  # SQLAlchemy model type
TEntity = TypeVar("TEntity")  # Domain entity type


class BaseRepository(Generic[TModel, TEntity]):
    """
    Base repository providing common CRUD operations.

    Generic base class that all specific repositories inherit from.
    Provides standard operations:
    - add: Insert new entity
    - get_by_id: Retrieve by UUID
    - update: Update existing entity
    - delete: Hard delete (rarely used)
    - soft_delete: Soft delete (set deleted_at)
    - list_all: List with pagination

    Type Parameters:
        TModel: SQLAlchemy model type (e.g., UserModel)
        TEntity: Domain entity type (e.g., User)

    Attributes:
        session: SQLAlchemy AsyncSession for database operations
        model_class: SQLAlchemy model class
        mapper_class: Mapper class for entity ↔ model conversion

    Usage:
        class PostgresUserRepository(BaseRepository[UserModel, User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, UserModel, UserMapper)

            # Add specific methods here
            async def get_by_email(self, email: Email) -> Optional[User]:
                # Implementation
    """

    def __init__(
        self,
        session: AsyncSession,
        model_class: Type[TModel],
        mapper_class,  # Type is Any to avoid circular imports
    ):
        """
        Initialize base repository.

        Args:
            session: SQLAlchemy async session
            model_class: SQLAlchemy model class
            mapper_class: Mapper class with to_entity() and to_model() methods
        """
        self.session = session
        self.model_class = model_class
        self.mapper = mapper_class

    async def add(self, entity: TEntity) -> TEntity:
        """
        Add a new entity to the database.

        Args:
            entity: Domain entity to persist

        Returns:
            Created entity with updated metadata

        Example:
            user = User(...)
            created_user = await repo.add(user)
        """
        model = self.mapper.to_model(entity)
        self.session.add(model)
        await self.session.flush()  # Flush to get generated ID
        await self.session.refresh(model)  # Refresh to get all fields
        return self.mapper.to_entity(model)

    async def get_by_id(self, entity_id: UUID, include_deleted: bool = False) -> Optional[TEntity]:
        """
        Retrieve entity by ID.

        Args:
            entity_id: Entity's unique identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            Domain entity if found, None otherwise

        Example:
            user = await repo.get_by_id(user_id)
            if user:
                print(f"Found: {user.email}")
        """
        # Build query
        stmt = select(self.model_class).where(self.model_class.id == entity_id)

        # Add soft delete filter if model has deleted_at column
        if hasattr(self.model_class, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model_class.deleted_at.is_(None))

        # Execute query
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)

    async def update(self, entity: TEntity) -> TEntity:
        """
        Update existing entity.

        Args:
            entity: Domain entity with updated data

        Returns:
            Updated entity

        Raises:
            NotFoundError: If entity doesn't exist

        Example:
            user.full_name = "New Name"
            updated_user = await repo.update(user)
        """
        # Get existing model
        entity_id = entity.id  # type: ignore  # All entities have id
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        existing_model = result.scalar_one_or_none()

        if existing_model is None:
            from app.application.exceptions import NotFoundError

            raise NotFoundError(f"{self.model_class.__name__} with id {entity_id} not found")

        # Update model using mapper
        updated_model = self.mapper.to_model(entity, existing_model=existing_model)
        await self.session.flush()
        await self.session.refresh(updated_model)

        return self.mapper.to_entity(updated_model)

    async def delete(self, entity_id: UUID) -> None:
        """
        Hard delete entity from database.

        Warning: This permanently removes the record. Use soft_delete() instead
        for most cases to maintain audit trail and referential integrity.

        Args:
            entity_id: Entity's unique identifier

        Raises:
            NotFoundError: If entity doesn't exist

        Example:
            await repo.delete(user_id)  # Permanent deletion!
        """
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            from app.application.exceptions import NotFoundError

            raise NotFoundError(f"{self.model_class.__name__} with id {entity_id} not found")

        await self.session.delete(model)
        await self.session.flush()

    async def soft_delete(self, entity_id: UUID) -> None:
        """
        Soft delete entity (set deleted_at timestamp).

        This is the preferred deletion method as it:
        - Maintains audit trail
        - Preserves referential integrity
        - Allows recovery if needed
        - Meets compliance requirements

        Args:
            entity_id: Entity's unique identifier

        Raises:
            NotFoundError: If entity doesn't exist
            ValueError: If model doesn't support soft delete

        Example:
            await repo.soft_delete(user_id)  # Sets deleted_at
        """
        if not hasattr(self.model_class, "deleted_at"):
            raise ValueError(f"{self.model_class.__name__} does not support soft delete")

        stmt = select(self.model_class).where(
            self.model_class.id == entity_id,
            self.model_class.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            from app.application.exceptions import NotFoundError

            raise NotFoundError(f"{self.model_class.__name__} with id {entity_id} not found")

        # Set deleted_at timestamp
        from datetime import UTC, datetime

        model.deleted_at = datetime.now(UTC)
        await self.session.flush()

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[TEntity]:
        """
        List entities with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of domain entities

        Example:
            # Get first 20 active users
            users = await repo.list_all(skip=0, limit=20)

            # Get next 20 users
            users = await repo.list_all(skip=20, limit=20)
        """
        # Build query
        stmt = select(self.model_class)

        # Add soft delete filter if model has deleted_at column
        if hasattr(self.model_class, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model_class.deleted_at.is_(None))

        # Add pagination
        stmt = stmt.offset(skip).limit(limit)

        # Order by created_at if available, otherwise by id
        if hasattr(self.model_class, "created_at"):
            stmt = stmt.order_by(self.model_class.created_at.desc())
        else:
            stmt = stmt.order_by(self.model_class.id)

        # Execute query
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def count(self, include_deleted: bool = False) -> int:
        """
        Count total number of entities.

        Args:
            include_deleted: Whether to include soft-deleted records

        Returns:
            Total count of entities

        Example:
            total_users = await repo.count()
            print(f"Total users: {total_users}")
        """
        from sqlalchemy import func

        # Build query
        stmt = select(func.count(self.model_class.id))

        # Add soft delete filter if model has deleted_at column
        if hasattr(self.model_class, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model_class.deleted_at.is_(None))

        # Execute query
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, entity_id: UUID, include_deleted: bool = False) -> bool:
        """
        Check if entity exists.

        Args:
            entity_id: Entity's unique identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            True if entity exists, False otherwise

        Example:
            if await repo.exists(user_id):
                print("User exists")
        """
        from sqlalchemy import exists, select

        # Build query
        stmt = select(
            exists(self.model_class).where(self.model_class.id == entity_id)
        )

        # Add soft delete filter if model has deleted_at column
        if hasattr(self.model_class, "deleted_at") and not include_deleted:
            stmt = select(
                exists(self.model_class).where(
                    self.model_class.id == entity_id,
                    self.model_class.deleted_at.is_(None),
                )
            )

        # Execute query
        result = await self.session.execute(stmt)
        return result.scalar()
