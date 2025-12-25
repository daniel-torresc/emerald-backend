"""
Base repository with generic CRUD operations.

This module provides a generic repository pattern for database operations.
All specific repositories should inherit from BaseRepository.

Type Parameters:
    ModelType: The SQLAlchemy model class (e.g., User, Role, etc.)
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base

# Type variable for the model class
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository for database operations.

    Provides common CRUD operations that work with any SQLAlchemy model.
    Automatically handles soft deletes by filtering out deleted records.

    Type Parameters:
        ModelType: The SQLAlchemy model class

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)

            # Add custom methods here
            async def get_by_email(self, email: str) -> User | None:
                ...
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """
        Initialize repository.

        Args:
            model: The SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    def _apply_soft_delete_filter(self, query: Select[Any]) -> Select[Any]:
        """
        Apply soft delete filter to query if model supports it.

        Args:
            query: SQLAlchemy select statement

        Returns:
            Query with soft delete filter applied
        """
        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        return query

    async def add(self, instance: ModelType) -> ModelType:
        """
        Persist a model instance.

        Args:
            instance: Model instance to persist

        Returns:
            Persisted model instance (with ID and timestamps populated)
        """
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """
        Get a record by ID.

        Automatically filters out soft-deleted records.

        Args:
            id: UUID of the record

        Returns:
            Model instance or None if not found

        Example:
            user = await user_repo.get_by_id(user_id)
            if user is None:
                raise NotFoundError("User")
        """
        query = select(self.model).where(self.model.id == id)
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Get all records with pagination.

        Automatically filters out soft-deleted records.

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of model instances

        Example:
            users = await user_repo.get_all(skip=0, limit=20)
        """
        query = select(self.model).offset(offset).limit(limit)
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, instance: ModelType) -> ModelType:
        """
        Persist changes to an already-modified model instance.

        The caller is responsible for modifying the instance attributes
        before calling this method. This method only handles persistence
        (flush + refresh).

        Args:
            instance: Model instance with changes already applied

        Returns:
            Updated model instance (with refreshed timestamps)

        Example:
            user = await user_repo.get_by_id(user_id)
            user.full_name = "New Name"
            user.email = "new@example.com"
            user = await user_repo.update(user)
        """
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def soft_delete(self, instance: ModelType) -> ModelType:
        """
        Soft delete a record (set deleted_at timestamp).

        Only works if model has deleted_at attribute (SoftDeleteMixin).

        Args:
            instance: Model instance to soft delete

        Returns:
            Soft-deleted model instance

        Raises:
            AttributeError: If model doesn't support soft delete

        Example:
            user = await user_repo.get_by_id(user_id)
            await user_repo.soft_delete(user)
        """
        if not hasattr(instance, "deleted_at"):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")

        instance.deleted_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """
        Hard delete a record (permanent removal from database).

        WARNING: This permanently deletes the record. Use soft_delete() instead
        for models that support it (models with SoftDeleteMixin).

        Args:
            instance: Model instance to delete

        Example:
            # Only use for cleanup, testing, or models without soft delete
            await repo.delete(temp_record)
        """
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self) -> int:
        """
        Count total records.

        Returns:
            Total count

        Example:
            total_users = await user_repo.count()
            total_including_deleted = await user_repo.count(include_deleted=True)
        """
        query = select(func.count()).select_from(self.model)
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def exists(self, id: uuid.UUID) -> bool:
        """
        Check if a record exists by ID.

        Automatically filters out soft-deleted records.

        Args:
            id: UUID of the record

        Returns:
            True if exists, False otherwise

        Example:
            if not await user_repo.exists(user_id):
                raise NotFoundError("User")
        """
        record = await self.get_by_id(id)
        return record is not None
