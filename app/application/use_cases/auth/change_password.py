"""Change password use case."""

from uuid import UUID

from app.application.dto.auth_dto import ChangePasswordInput
from app.application.exceptions import NotFoundError, UnauthorizedError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.domain.value_objects.password_hash import PasswordHash


class ChangePasswordUseCase:
    """Use case for changing user password."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self,
        user_id: UUID,
        input_dto: ChangePasswordInput,
        password_verifier,
        password_hasher,
    ) -> None:
        """
        Change user's password.

        Args:
            user_id: User's unique identifier
            input_dto: Password change data
            password_verifier: Callable to verify password (injected from infrastructure)
            password_hasher: Callable to hash password (injected from infrastructure)

        Raises:
            NotFoundError: If user doesn't exist
            UnauthorizedError: If current password is incorrect
        """
        async with self.uow:
            # Get user
            user = await self.uow.users.get_by_id(user_id)

            if user is None:
                raise NotFoundError(
                    message="User not found",
                    resource_type="User",
                    resource_id=str(user_id),
                )

            # Verify current password
            is_valid = password_verifier(
                input_dto.current_password, user.password_hash.value
            )

            if not is_valid:
                raise UnauthorizedError(message="Current password is incorrect")

            # Hash new password
            hashed_password = password_hasher(input_dto.new_password)
            new_password_hash = PasswordHash(hashed_password)

            # Change password using domain method
            user.change_password(new_password_hash)

            # Update user
            await self.uow.users.update(user)

            # Revoke all refresh tokens to force re-login
            await self.uow.refresh_tokens.revoke_all_for_user(user_id)

            # Commit transaction
            await self.uow.commit()
