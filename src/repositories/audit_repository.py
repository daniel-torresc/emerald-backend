"""
AuditLog repository for audit trail operations.

This module provides database operations for the AuditLog model.
Note: AuditLogs are IMMUTABLE - this repository only supports
creation and reading, not updates or deletes.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditAction, AuditStatus
from src.models.audit_log import AuditLog


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

    async def create(
        self,
        user_id: uuid.UUID | None,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        error_message: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        This is the ONLY way to add audit logs. They cannot be modified after creation.

        Args:
            user_id: User who performed the action (None for system actions)
            action: Type of action performed
            entity_type: Type of entity affected (e.g., "user", "transaction")
            entity_id: UUID of affected entity
            old_values: Values before the action (for UPDATE/DELETE)
            new_values: Values after the action (for CREATE/UPDATE)
            description: Human-readable description
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Correlation ID for request tracing
            status: Status of the action (SUCCESS, FAILURE, PARTIAL)
            error_message: Error message if status is FAILURE
            extra_metadata: Additional context as JSONB

        Returns:
            Created AuditLog instance

        Example:
            # Log successful login
            audit_log = await audit_repo.create(
                user_id=user.id,
                action=AuditAction.LOGIN,
                entity_type="user",
                entity_id=user.id,
                description="User logged in successfully",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0...",
                request_id=request.state.request_id,
                status=AuditStatus.SUCCESS,
            )

            # Log data modification
            audit_log = await audit_repo.create(
                user_id=current_user.id,
                action=AuditAction.UPDATE,
                entity_type="user",
                entity_id=target_user.id,
                old_values={"email": "old@example.com"},
                new_values={"email": "new@example.com"},
                description="User email updated",
                status=AuditStatus.SUCCESS,
            )

            # Log failed action
            audit_log = await audit_repo.create(
                user_id=user.id,
                action=AuditAction.DELETE,
                entity_type="transaction",
                entity_id=transaction_id,
                description="Attempted to delete transaction",
                status=AuditStatus.FAILURE,
                error_message="Insufficient permissions",
            )
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
            extra_metadata=extra_metadata,
        )

        self.session.add(audit_log)
        await self.session.flush()
        await self.session.refresh(audit_log)
        return audit_log

    async def get_user_logs(
        self,
        user_id: uuid.UUID,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        status: AuditStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Get audit logs for a specific user with filtering.

        Used for:
        - User viewing their own audit logs (GDPR right to access)
        - Admin viewing user's action history

        Args:
            user_id: UUID of the user
            action: Filter by action type
            entity_type: Filter by entity type
            status: Filter by status
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

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
        query = select(AuditLog).where(AuditLog.user_id == user_id)

        # Apply filters
        if action:
            query = query.where(AuditLog.action == action)

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        if status:
            query = query.where(AuditLog.status == status)

        if start_date:
            query = query.where(AuditLog.created_at >= start_date)

        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Order by created_at descending (newest first)
        query = query.order_by(AuditLog.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_entity_logs(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        action: AuditAction | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Get audit logs for a specific entity.

        Shows the complete history of actions performed on an entity.

        Args:
            entity_type: Type of entity (e.g., "user", "transaction")
            entity_id: UUID of the entity
            action: Filter by action type
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances

        Example:
            # Get all actions performed on a user
            logs = await audit_repo.get_entity_logs(
                entity_type="user",
                entity_id=user_id,
            )

            # Get all modifications to a transaction
            logs = await audit_repo.get_entity_logs(
                entity_type="transaction",
                entity_id=transaction_id,
                action=AuditAction.UPDATE,
            )
        """
        query = select(AuditLog).where(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
        )

        if action:
            query = query.where(AuditLog.action == action)

        # Order by created_at descending (newest first)
        query = query.order_by(AuditLog.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_user_logs(
        self,
        user_id: uuid.UUID,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        status: AuditStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Count audit logs for a user with filters.

        Used for pagination metadata.

        Args:
            user_id: UUID of the user
            action: Filter by action type
            entity_type: Filter by entity type
            status: Filter by status
            start_date: Filter logs after this date
            end_date: Filter logs before this date

        Returns:
            Total count of matching logs

        Example:
            total = await audit_repo.count_user_logs(user_id=user.id)
            total_pages = (total + limit - 1) // limit
        """
        query = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.user_id == user_id)
        )

        # Apply filters
        if action:
            query = query.where(AuditLog.action == action)

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        if status:
            query = query.where(AuditLog.status == status)

        if start_date:
            query = query.where(AuditLog.created_at >= start_date)

        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_all_logs(
        self,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        status: AuditStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Count all audit logs with filters (admin only).

        Used for pagination metadata.

        Args:
            action: Filter by action type
            entity_type: Filter by entity type
            status: Filter by status
            start_date: Filter logs after this date
            end_date: Filter logs before this date

        Returns:
            Total count of matching logs

        Example:
            total = await audit_repo.count_all_logs()
            total_pages = (total + limit - 1) // limit
        """
        query = select(func.count()).select_from(AuditLog)

        # Apply filters
        if action:
            query = query.where(AuditLog.action == action)

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        if status:
            query = query.where(AuditLog.status == status)

        if start_date:
            query = query.where(AuditLog.created_at >= start_date)

        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_all_logs(
        self,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        status: AuditStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Get all audit logs with filtering (admin only).

        Args:
            action: Filter by action type
            entity_type: Filter by entity type
            status: Filter by status
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances

        Example:
            # Get all failed login attempts in last week
            logs = await audit_repo.get_all_logs(
                action=AuditAction.LOGIN_FAILED,
                start_date=datetime.now(UTC) - timedelta(days=7),
            )
        """
        query = select(AuditLog)

        # Apply filters
        if action:
            query = query.where(AuditLog.action == action)

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        if status:
            query = query.where(AuditLog.status == status)

        if start_date:
            query = query.where(AuditLog.created_at >= start_date)

        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Order by created_at descending (newest first)
        query = query.order_by(AuditLog.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
