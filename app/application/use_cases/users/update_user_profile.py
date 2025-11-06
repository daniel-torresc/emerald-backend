"""Update user profile use case."""

from uuid import UUID

from app.application.dto.user_dto import UpdateUserProfileInput, UserProfileOutput
from app.application.exceptions import AlreadyExistsError, NotFoundError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.domain.value_objects.email import Email
from app.domain.value_objects.username import Username


class UpdateUserProfileUseCase:
    """Use case for updating user profile."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, user_id: UUID, input_dto: UpdateUserProfileInput
    ) -> UserProfileOutput:
        """
        Update user profile.

        Args:
            user_id: User's unique identifier
            input_dto: Profile update data

        Returns:
            Updated user profile

        Raises:
            NotFoundError: If user doesn't exist
            AlreadyExistsError: If email or username is already taken
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

            # Update email if provided
            if input_dto.email is not None:
                new_email = Email(input_dto.email)
                if new_email != user.email:
                    # Check if email is already taken
                    if await self.uow.users.exists_by_email(new_email):
                        raise AlreadyExistsError(
                            message=f"Email '{new_email.value}' is already taken",
                            resource_type="User",
                            field="email",
                            value=new_email.value,
                        )
                    user.email = new_email

            # Update username if provided
            if input_dto.username is not None:
                new_username = Username(input_dto.username)
                if new_username != user.username:
                    # Check if username is already taken
                    if await self.uow.users.exists_by_username(new_username):
                        raise AlreadyExistsError(
                            message=f"Username '{new_username.value}' is already taken",
                            resource_type="User",
                            field="username",
                            value=new_username.value,
                        )
                    user.username = new_username

            # Update full name if provided
            if input_dto.full_name is not None:
                user.full_name = input_dto.full_name

            # Update user in repository
            updated_user = await self.uow.users.update(user)

            # Commit transaction
            await self.uow.commit()

            # Return DTO
            return UserProfileOutput.from_entity(updated_user)
