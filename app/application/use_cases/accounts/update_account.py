"""Update account use case."""

from uuid import UUID

from app.application.dto.account_dto import AccountOutput, UpdateAccountInput
from app.application.exceptions import AlreadyExistsError, ForbiddenError, NotFoundError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class UpdateAccountUseCase:
    """Use case for updating account information."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, account_id: UUID, input_dto: UpdateAccountInput, current_user_id: UUID
    ) -> AccountOutput:
        """
        Update account information.

        Args:
            account_id: Account's unique identifier
            input_dto: Account update data
            current_user_id: ID of user updating the account

        Returns:
            Updated account information

        Raises:
            NotFoundError: If account doesn't exist
            ForbiddenError: If user is not the owner
            AlreadyExistsError: If new name conflicts with existing account
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

            # Check if user is the owner (only owners can update)
            if account.user_id != current_user_id:
                raise ForbiddenError(
                    message="Only the account owner can update account settings",
                    resource_type="Account",
                    resource_id=str(account_id),
                )

            # Update name if provided
            if input_dto.name is not None and input_dto.name != account.name:
                # Check if new name conflicts with another account
                existing = await self.uow.accounts.find_by_user_and_name(
                    user_id=current_user_id, name=input_dto.name
                )
                if existing and existing.id != account_id:
                    raise AlreadyExistsError(
                        message=f"Account with name '{input_dto.name}' already exists",
                        resource_type="Account",
                        field="name",
                        value=input_dto.name,
                    )
                account.name = input_dto.name

            # Update description if provided
            if input_dto.description is not None:
                account.description = input_dto.description

            # Update is_active if provided
            if input_dto.is_active is not None:
                if input_dto.is_active:
                    account.activate()
                else:
                    account.deactivate()

            # Update account
            updated_account = await self.uow.accounts.update(account)

            # Commit transaction
            await self.uow.commit()

            # Return DTO
            return AccountOutput.from_entity(updated_account)
