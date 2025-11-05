"""Get user profile use case."""

from uuid import UUID

from app.application.dto.user_dto import UserProfileOutput
from app.application.exceptions import NotFoundError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class GetUserProfileUseCase:
    """Use case for retrieving user profile."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(self, user_id: UUID) -> UserProfileOutput:
        """
        Get user profile by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User profile information

        Raises:
            NotFoundError: If user doesn't exist
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

            # Return DTO
            return UserProfileOutput.from_entity(user)
