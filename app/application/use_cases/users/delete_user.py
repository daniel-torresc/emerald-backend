"""Delete user use case."""

from uuid import UUID

from app.application.exceptions import ForbiddenError, NotFoundError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class DeleteUserUseCase:
    """Use case for deleting a user."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, user_id: UUID, current_user_id: UUID, soft_delete: bool = True
    ) -> None:
        """
        Delete user account.

        Args:
            user_id: User's unique identifier to delete
            current_user_id: ID of user performing the deletion
            soft_delete: Whether to soft delete (True) or hard delete (False)

        Raises:
            NotFoundError: If user doesn't exist
            ForbiddenError: If user tries to delete another user without admin privileges
        """
        async with self.uow:
            # Get the user to delete
            user = await self.uow.users.get_by_id(user_id)

            if user is None:
                raise NotFoundError(
                    message="User not found",
                    resource_type="User",
                    resource_id=str(user_id),
                )

            # Get current user for permission check
            current_user = await self.uow.users.get_by_id(current_user_id)

            if current_user is None:
                raise NotFoundError(
                    message="Current user not found",
                    resource_type="User",
                    resource_id=str(current_user_id),
                )

            # Check permissions: users can only delete themselves unless admin
            if user_id != current_user_id and not current_user.is_admin:
                raise ForbiddenError(
                    message="You don't have permission to delete other users",
                    required_permission="admin",
                    resource_type="User",
                    resource_id=str(user_id),
                )

            # Perform deletion
            if soft_delete:
                await self.uow.users.soft_delete(user_id)
            else:
                await self.uow.users.delete(user_id)

            # Revoke all refresh tokens
            await self.uow.refresh_tokens.revoke_all_for_user(user_id)

            # Commit transaction
            await self.uow.commit()
