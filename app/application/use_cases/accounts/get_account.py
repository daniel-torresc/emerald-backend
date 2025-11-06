"""Get account use case."""

from uuid import UUID

from app.application.dto.account_dto import AccountOutput
from app.application.exceptions import ForbiddenError, NotFoundError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class GetAccountUseCase:
    """Use case for retrieving account details."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, account_id: UUID, current_user_id: UUID
    ) -> AccountOutput:
        """
        Get account details.

        Args:
            account_id: Account's unique identifier
            current_user_id: ID of user requesting the account

        Returns:
            Account information

        Raises:
            NotFoundError: If account doesn't exist
            ForbiddenError: If user doesn't have access to the account
        """
        async with self.uow:
            # Get account
            account = await self.uow.accounts.get_by_id(account_id)

            if account is None:
                raise NotFoundError(
                    message="Account not found",
                    resource_type="Account",
                    resource_id=str(account_id),
                )

            # Check if user has access (owner or shared)
            if not account.can_be_accessed_by(current_user_id):
                raise ForbiddenError(
                    message="You don't have access to this account",
                    resource_type="Account",
                    resource_id=str(account_id),
                )

            # Return DTO
            return AccountOutput.from_entity(account)
