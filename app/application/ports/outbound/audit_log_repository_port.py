"""Audit log repository port interface."""

from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from app.domain.entities.audit_log import AuditLog


class AuditLogRepositoryPort(Protocol):
    """Repository interface for AuditLog entity."""

    async def add(self, audit_log: AuditLog) -> AuditLog:
        """
        Add a new audit log entry to the repository.

        Args:
            audit_log: AuditLog entity to add

        Returns:
            Created audit log entity with updated metadata

        Note:
            Audit logs are immutable after creation
        """
        ...

    async def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        """
        Retrieve audit log by ID.

        Args:
            log_id: AuditLog's unique identifier

        Returns:
            AuditLog entity if found, None otherwise
        """
        ...

    async def list_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[AuditLog]:
        """
        List audit logs for a specific user.

        Args:
            user_id: User's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            start_date: Filter logs after this date (inclusive)
            end_date: Filter logs before this date (inclusive)

        Returns:
            List of audit log entities ordered by timestamp (newest first)
        """
        ...

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
            entity_type: Type of entity (e.g., 'user', 'account')
            entity_id: Entity's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of audit log entities ordered by timestamp (newest first)
        """
        ...

    async def list_by_action(
        self,
        action: str,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[AuditLog]:
        """
        List audit logs by action type.

        Args:
            action: Action type (e.g., 'create', 'update', 'delete')
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            start_date: Filter logs after this date (inclusive)
            end_date: Filter logs before this date (inclusive)

        Returns:
            List of audit log entities ordered by timestamp (newest first)
        """
        ...

    async def search(
        self,
        user_id: Optional[UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Search audit logs with multiple filters.

        Args:
            user_id: Filter by user ID
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            action: Filter by action type
            start_date: Filter logs after this date (inclusive)
            end_date: Filter logs before this date (inclusive)
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of audit log entities ordered by timestamp (newest first)
        """
        ...

    async def count_by_user(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Count audit logs for a specific user.

        Args:
            user_id: User's unique identifier
            start_date: Count logs after this date (inclusive)
            end_date: Count logs before this date (inclusive)

        Returns:
            Number of audit log entries
        """
        ...
