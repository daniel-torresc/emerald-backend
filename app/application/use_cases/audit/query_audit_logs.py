"""Query audit logs use case."""

from math import ceil
from uuid import UUID

from app.application.dto.audit_dto import AuditLogListOutput, AuditLogOutput, QueryAuditLogsInput
from app.application.exceptions import ForbiddenError, NotFoundError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class QueryAuditLogsUseCase:
    """Use case for querying audit logs."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, input_dto: QueryAuditLogsInput, current_user_id: UUID
    ) -> AuditLogListOutput:
        """
        Query audit logs with filters.

        Args:
            input_dto: Query parameters
            current_user_id: ID of user performing the query

        Returns:
            Paginated list of audit logs

        Raises:
            ForbiddenError: If non-admin tries to view other users' logs
            NotFoundError: If current user doesn't exist
        """
        async with self.uow:
            # Get current user for permission check
            current_user = await self.uow.users.get_by_id(current_user_id)

            if current_user is None:
                raise NotFoundError(
                    message="Current user not found",
                    resource_type="User",
                    resource_id=str(current_user_id),
                )

            # Check permissions: non-admins can only view their own logs
            if input_dto.user_id is not None:
                if input_dto.user_id != current_user_id and not current_user.is_admin:
                    raise ForbiddenError(
                        message="You can only view your own audit logs",
                        required_permission="admin",
                    )
            else:
                # If no user_id filter, default to current user for non-admins
                if not current_user.is_admin:
                    input_dto = QueryAuditLogsInput(
                        user_id=current_user_id,
                        entity_type=input_dto.entity_type,
                        entity_id=input_dto.entity_id,
                        action=input_dto.action,
                        start_date=input_dto.start_date,
                        end_date=input_dto.end_date,
                        skip=input_dto.skip,
                        limit=input_dto.limit,
                    )

            # Search audit logs with filters
            logs = await self.uow.audit_logs.search(
                user_id=input_dto.user_id,
                entity_type=input_dto.entity_type,
                entity_id=input_dto.entity_id,
                action=input_dto.action,
                start_date=input_dto.start_date,
                end_date=input_dto.end_date,
                skip=input_dto.skip,
                limit=input_dto.limit,
            )

            # Calculate pagination metadata
            total = len(logs) + input_dto.skip  # Simplified estimation
            page = (input_dto.skip // input_dto.limit) + 1
            per_page = input_dto.limit
            total_pages = ceil(total / per_page)

            # Convert to DTOs
            log_dtos = [AuditLogOutput.from_entity(log) for log in logs]

            return AuditLogListOutput(
                logs=log_dtos,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )
