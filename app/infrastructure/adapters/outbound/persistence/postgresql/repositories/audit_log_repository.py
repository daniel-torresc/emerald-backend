"""
PostgreSQL implementation of AuditLogRepositoryPort.

This repository handles all database operations for AuditLog entities using PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.outbound.audit_log_repository_port import AuditLogRepositoryPort
from app.domain.entities.audit_log import AuditLog
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.audit_log_mapper import (
    AuditLogMapper,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.audit_log_model import (
    AuditLogModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.base_repository import (
    BaseRepository,
)


class PostgresAuditLogRepository(
    BaseRepository[AuditLogModel, AuditLog], AuditLogRepositoryPort
):
    """
    PostgreSQL implementation of AuditLogRepositoryPort.

    Inherits common CRUD operations from BaseRepository and implements
    AuditLog-specific operations defined in AuditLogRepositoryPort.

    Note: AuditLog is immutable, so update() and delete() should not be used.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize PostgreSQL audit log repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, AuditLogModel, AuditLogMapper)

    async def list_by_user_id(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        List audit logs for a specific user.

        Args:
            user_id: User's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of audit log entities
        """
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(AuditLogModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        List audit logs for a specific entity.

        Args:
            entity_type: Type of entity (e.g., "user", "account")
            entity_id: Entity's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of audit log entities
        """
        stmt = (
            select(AuditLogModel)
            .where(
                AuditLogModel.entity_type == entity_type,
                AuditLogModel.entity_id == entity_id,
            )
            .offset(skip)
            .limit(limit)
            .order_by(AuditLogModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def list_by_action(
        self,
        action: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        List audit logs by action type.

        Args:
            action: Action type
            start_date: Optional start date filter
            end_date: Optional end date filter
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of audit log entities
        """
        from app.infrastructure.adapters.outbound.persistence.postgresql.models.enums import (
            AuditAction,
        )

        # Convert string to enum if possible
        try:
            action_enum = AuditAction(action)
            stmt = select(AuditLogModel).where(AuditLogModel.action == action_enum)
        except ValueError:
            # If not a valid enum, search by string in description
            stmt = select(AuditLogModel).where(AuditLogModel.description.contains(action))

        # Add date filters if provided
        if start_date:
            stmt = stmt.where(AuditLogModel.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AuditLogModel.created_at <= end_date)

        stmt = stmt.offset(skip).limit(limit).order_by(AuditLogModel.created_at.desc())

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def list_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        List audit logs within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of audit log entities
        """
        stmt = (
            select(AuditLogModel)
            .where(
                AuditLogModel.created_at >= start_date,
                AuditLogModel.created_at <= end_date,
            )
            .offset(skip)
            .limit(limit)
            .order_by(AuditLogModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    # Override update and delete to prevent modification of audit logs
    async def update(self, entity: AuditLog) -> AuditLog:
        """
        Update is not allowed for audit logs (immutable).

        Raises:
            ValueError: Always raises as audit logs cannot be modified
        """
        raise ValueError("Audit logs are immutable and cannot be updated")

    async def delete(self, entity_id: UUID) -> None:
        """
        Delete is not allowed for audit logs (immutable).

        Raises:
            ValueError: Always raises as audit logs cannot be deleted
        """
        raise ValueError("Audit logs are immutable and cannot be deleted")

    async def soft_delete(self, entity_id: UUID) -> None:
        """
        Soft delete is not allowed for audit logs (immutable).

        Raises:
            ValueError: Always raises as audit logs cannot be deleted
        """
        raise ValueError("Audit logs are immutable and cannot be soft deleted")
