"""Logout user use case."""

from uuid import UUID

from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class LogoutUserUseCase:
    """Use case for logging out a user."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(self, user_id: UUID, refresh_token: str | None = None) -> None:
        """
        Logout user by revoking refresh tokens.

        Args:
            user_id: User's unique identifier
            refresh_token: Specific refresh token to revoke (if None, revoke all)
        """
        async with self.uow:
            if refresh_token:
                # Revoke specific token
                await self.uow.refresh_tokens.revoke_token(refresh_token)
            else:
                # Revoke all tokens for user (logout from all devices)
                await self.uow.refresh_tokens.revoke_all_for_user(user_id)

            # Commit transaction
            await self.uow.commit()
