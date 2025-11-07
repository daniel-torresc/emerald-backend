"""Share account use case."""

from datetime import datetime
from uuid import UUID, uuid4

from app.application.dto.account_dto import AccountShareOutput, ShareAccountInput
from app.application.exceptions import (
    AlreadyExistsError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.domain.entities.account_share import AccountShare
from app.domain.value_objects.permission import Permission


class ShareAccountUseCase:
    """Use case for sharing an account with another user."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, input_dto: ShareAccountInput, current_user_id: UUID
    ) -> AccountShareOutput:
        """
        Share account with another user.

        Args:
            input_dto: Account share data
            current_user_id: ID of user sharing the account

        Returns:
            Created account share information

        Raises:
            NotFoundError: If account or shared user doesn't exist
            ForbiddenError: If user is not the owner
            AlreadyExistsError: If account is already shared with the user
            ValidationError: If trying to share with self
        """
        async with self.uow:
            # Get account
            account = await self.uow.accounts.get_by_id(input_dto.account_id)

            if account is None:
                raise NotFoundError(
                    message="Account not found",
                    resource_type="Account",
                    resource_id=str(input_dto.account_id),
                )

            # Check if user is the owner (only owners can share)
            if account.user_id != current_user_id:
                raise ForbiddenError(
                    message="Only the account owner can share the account",
                    resource_type="Account",
                    resource_id=str(input_dto.account_id),
                )

            # Validate not sharing with self
            if input_dto.shared_with_user_id == current_user_id:
                raise ValidationError(
                    message="Cannot share account with yourself",
                    field="shared_with_user_id",
                )

            # Check if shared user exists
            shared_user = await self.uow.users.get_by_id(input_dto.shared_with_user_id)

            if shared_user is None:
                raise NotFoundError(
                    message="User to share with not found",
                    resource_type="User",
                    resource_id=str(input_dto.shared_with_user_id),
                )

            # Check if already shared
            existing_share = await self.uow.account_shares.find_by_account_and_user(
                account_id=input_dto.account_id,
                shared_with_user_id=input_dto.shared_with_user_id,
            )

            if existing_share:
                raise AlreadyExistsError(
                    message="Account is already shared with this user",
                    resource_type="AccountShare",
                )

            # Create value object for permission
            permission = Permission(input_dto.permission)

            # Create account share entity
            account_share = AccountShare(
                id=uuid4(),
                account_id=input_dto.account_id,
                shared_with_user_id=input_dto.shared_with_user_id,
                permission=permission,
                created_at=datetime.utcnow(),
                expires_at=input_dto.expires_at,
            )

            # Persist account share
            created_share = await self.uow.account_shares.add(account_share)

            # Commit transaction
            await self.uow.commit()

            # Return DTO
            return AccountShareOutput.from_entity(created_share)
