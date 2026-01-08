"""
AuditLog repository for audit trail operations.

This module provides database operations for the AuditLog model.
Note: AuditLogs are IMMUTABLE - this repository only supports
creation and reading, not updates or deletes.
"""

import logging
from typing import Any

from sqlalchemy import ColumnElement, UnaryExpression, and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.strategy_options import _AbstractLoad

from models import AuditLog
from schemas import (
    AuditLogFilterParams,
    AuditLogSortParams,
    PaginationParams,
    SortOrder,
)

logger = logging.getLogger(__name__)


class AuditLogRepository:
    """
    Repository for AuditLog model operations.

    IMPORTANT: This repository does NOT extend BaseRepository because
    audit logs are immutable. Only create() and read operations are supported.

    Operations:
    - Create audit log entries
    - Query audit logs by user, entity, action, date range
    - Count audit logs for pagination

    NO UPDATE OR DELETE OPERATIONS - audit logs are immutable for compliance.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AuditLogRepository.

        Args:
            session: Async database session
        """
        self.session = session

    @staticmethod
    def _build_filters(
        params: AuditLogFilterParams,
    ) -> list[ColumnElement[bool]]:
        """
        Convert AuditLogFilterParams to SQLAlchemy filter expressions.

        Args:
            params: Filter parameters from request

        Returns:
            List of SQLAlchemy filter expressions
        """
        filters: list[ColumnElement[bool]] = []

        # User filter
        if params.user_id is not None:
            filters.append(AuditLog.user_id == params.user_id)

        # Action filter
        if params.action is not None:
            filters.append(AuditLog.action == params.action)

        # Entity type filter
        if params.entity_type is not None:
            filters.append(AuditLog.entity_type == params.entity_type)

        # Entity ID filter
        if params.entity_id is not None:
            filters.append(AuditLog.entity_id == params.entity_id)

        # Status filter
        if params.status is not None:
            filters.append(AuditLog.status == params.status)

        # Date range filters
        if params.start_date is not None:
            filters.append(AuditLog.created_at >= params.start_date)

        if params.end_date is not None:
            filters.append(AuditLog.created_at <= params.end_date)

        return filters

    @staticmethod
    def _build_order_by(
        params: AuditLogSortParams,
    ) -> list[UnaryExpression]:
        """
        Convert AuditLogSortParams to SQLAlchemy order_by expressions.

        Args:
            params: Sort parameters with sort_by and sort_order

        Returns:
            List of SQLAlchemy order_by expressions
        """
        order_by: list[UnaryExpression] = []

        # Get the model column from enum value
        sort_column = getattr(AuditLog, params.sort_by.value)

        # Apply sort direction
        if params.sort_order == SortOrder.ASC:
            order_by.append(asc(sort_column))
        else:
            order_by.append(desc(sort_column))

        # Add secondary sort by id for deterministic pagination
        order_by.append(desc(AuditLog.id))

        return order_by

    async def add(self, instance: AuditLog) -> AuditLog:
        """
        Persist a new audit log entry.

        This is the ONLY way to add audit logs. They cannot be modified after creation.

        Args:
            instance: AuditLog instance to persist

        Returns:
            Persisted AuditLog instance
        """
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def list_user_logs(
        self,
        filter_params: AuditLogFilterParams,
        sort_params: AuditLogSortParams,
        pagination_params: PaginationParams,
    ) -> tuple[list[AuditLog], int]:
        """
        Get audit logs for a specific user with filtering.

        Used for:
        - User viewing their own audit logs (GDPR right to access)
        - Admin viewing user's action history

        Args:
            user_id: UUID of the user
            filter_params:
            sort_params:
            pagination_params:

        Returns:
            List of AuditLog instances

        Example:
            # Get user's login history
            logs = await audit_repo.get_user_logs(
                user_id=user.id,
                action=AuditAction.LOGIN,
                skip=0,
                limit=20
            )

            # Get user's failed actions in last 24 hours
            from datetime import timedelta, UTC
            logs = await audit_repo.get_user_logs(
                user_id=user.id,
                status=AuditStatus.FAILURE,
                start_date=datetime.now(UTC) - timedelta(days=1),
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
    ) -> tuple[list[AuditLog], int]:
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
    ) -> list[AuditLog]:
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
        query = select(AuditLog)

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
                f"Listing {AuditLog.__name__} without pagination. Beware of performance issues."
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
        query = select(func.count()).select_from(AuditLog)

        # Apply filters
        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        return result.scalar_one() or 0
