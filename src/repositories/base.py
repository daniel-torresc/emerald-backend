"""
Base repository with generic CRUD operations.

This module provides a generic repository pattern for database operations.
All specific repositories should inherit from BaseRepository.

Type Parameters:
    ModelType: The SQLAlchemy model class (e.g., User, Role, etc.)
"""

import logging
import uuid
from abc import ABC
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import ColumnElement, Select, UnaryExpression, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.strategy_options import _AbstractLoad

from models import Base

logger = logging.getLogger(__name__)

# Type variable for the model class
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType], ABC):
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

    # ========================================================================
    # CORE CRUD OPERATIONS
    # ========================================================================

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

    async def create(self, instance: ModelType) -> ModelType:
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

    # ========================================================================
    # SOFT DELETE HANDLING
    # ========================================================================

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

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def _list_and_count(
        self,
        filters: list[ColumnElement[bool]] | None = None,
        order_by: list[UnaryExpression[Any]] | None = None,
        load_relationships: list[_AbstractLoad] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[list[ModelType], int]:
        records = await self._list(
            filters=filters,
            order_by=order_by,
            load_relationships=load_relationships,
            offset=offset,
            limit=limit,
        )

        count = await self._count(
            filters=filters,
        )

        return records, count

    async def _list(
        self,
        filters: list[ColumnElement[bool]] | None = None,
        order_by: list[UnaryExpression[Any]] | None = None,
        load_relationships: list[_AbstractLoad] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[ModelType]:
        """
        Get records with optional filtering, sorting, and pagination.

        This is the primary method for list operations. Uses pre-built
        filters and order_by expressions from build_filters() and build_order_by().

        Args:
            filters: List of SQLAlchemy filter expressions
            order_by: List of SQLAlchemy order_by expressions
            load_relationships: SQLAlchemy load options for eager relationship loading
            offset: Number of records to skip
            limit: Maximum number of records to return (default to 100)

        Returns:
            List of model instances

        Example:
            filters = repo.build_filters(filter_params, user_id=user.id)
            order_by = repo.build_order_by(sort_params)
            items = await repo.find_all(
                filters=filters,
                order_by=order_by,
                offset=pagination.offset,
                limit=pagination.page_size,
            )
        """
        query = select(self.model)

        # Apply soft-delete filter
        query = self._apply_soft_delete_filter(query)

        # Apply eager loading options
        if load_relationships:
            query = query.options(*load_relationships)

        # Apply filters
        if filters:
            query = query.where(and_(*filters))

        # Apply ordering
        if order_by:
            query = query.order_by(*order_by)

        # Apply pagination
        if offset is not None and limit is not None:
            query = query.offset(offset).limit(limit)
        else:
            logger.warning(
                f"Listing {self.model.__name__} without pagination. Beware of performance issues."
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _count(
        self,
        filters: list[ColumnElement[bool]] | None = None,
    ) -> int:
        """
        Count records with optional filtering.

        Uses pre-built filters from build_filters().

        Args:
            filters: List of SQLAlchemy filter expressions

        Returns:
            Total count of matching records

        Example:
            filters = repo.build_filters(filter_params, user_id=user.id)
            total = await repo.count_with_filters(filters)
        """
        query = select(func.count()).select_from(self.model)

        # Apply soft-delete filter
        query = self._apply_soft_delete_filter(query)

        # Apply filters
        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        return result.scalar_one() or 0

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
