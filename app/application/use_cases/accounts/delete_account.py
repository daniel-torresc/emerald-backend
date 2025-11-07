"""Delete account use case."""

from uuid import UUID

from app.application.exceptions import ForbiddenError, NotFoundError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class DeleteAccountUseCase:
    """Use case for deleting an account."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, account_id: UUID, current_user_id: UUID, soft_delete: bool = True
    ) -> None:
        """
        Delete account.

        Args:
            account_id: Account's unique identifier
            current_user_id: ID of user deleting the account
            soft_delete: Whether to soft delete (True) or hard delete (False)

        Raises:
            NotFoundError: If account doesn't exist
            ForbiddenError: If user is not the owner
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

            # Check if user is the owner (only owners can delete)
            if account.user_id != current_user_id:
                raise ForbiddenError(
                    message="Only the account owner can delete the account",
                    resource_type="Account",
                    resource_id=str(account_id),
                )

            # Perform deletion
            if soft_delete:
                await self.uow.accounts.soft_delete(account_id)
            else:
                await self.uow.accounts.delete(account_id)

            # Commit transaction
            await self.uow.commit()
