"""Create audit log use case."""

from datetime import datetime
from uuid import uuid4

from app.application.dto.audit_dto import AuditLogOutput, CreateAuditLogInput
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.domain.entities.audit_log import AuditLog


class CreateAuditLogUseCase:
    """Use case for creating an audit log entry."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(self, input_dto: CreateAuditLogInput) -> AuditLogOutput:
        """
        Create a new audit log entry.

        Args:
            input_dto: Audit log data

        Returns:
            Created audit log entry

        Note:
            Audit logs are immutable after creation
        """
        async with self.uow:
            # Create audit log entity
            audit_log = AuditLog(
                id=uuid4(),
                user_id=input_dto.user_id,
                action=input_dto.action,
                entity_type=input_dto.entity_type,
                entity_id=input_dto.entity_id,
                changes=input_dto.changes,
                ip_address=input_dto.ip_address,
                user_agent=input_dto.user_agent,
                timestamp=datetime.utcnow(),
            )

            # Persist audit log
            created_log = await self.uow.audit_logs.add(audit_log)

            # Commit transaction
            await self.uow.commit()

            # Return DTO
            return AuditLogOutput.from_entity(created_log)
