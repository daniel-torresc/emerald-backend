"""Refresh token use case."""

from app.application.dto.auth_dto import RefreshTokenInput, RefreshTokenOutput
from app.application.exceptions import UnauthorizedError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class RefreshTokenUseCase:
    """Use case for refreshing access tokens."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self,
        input_dto: RefreshTokenInput,
        token_validator,
        token_generator,
        token_expires_in: int = 1800,
    ) -> RefreshTokenOutput:
        """
        Refresh access token using refresh token.

        Args:
            input_dto: Refresh token data
            token_validator: Callable to validate and decode token (injected from infrastructure)
            token_generator: Callable to generate new tokens (injected from infrastructure)
            token_expires_in: Token expiry time in seconds (default 30 minutes)

        Returns:
            New access token and refresh token

        Raises:
            UnauthorizedError: If refresh token is invalid or expired
        """
        async with self.uow:
            # Validate refresh token
            try:
                token_data = token_validator(input_dto.refresh_token)
            except Exception:
                raise UnauthorizedError(message="Invalid or expired refresh token")

            # Check if refresh token is revoked in database
            is_valid = await self.uow.refresh_tokens.is_token_valid(
                input_dto.refresh_token
            )

            if not is_valid:
                raise UnauthorizedError(message="Refresh token has been revoked")

            # Get user to ensure they still exist and are active
            user = await self.uow.users.get_by_id(token_data["user_id"])

            if user is None:
                raise UnauthorizedError(message="User not found")

            if not user.is_active:
                raise UnauthorizedError(message="User account is inactive")

            # Generate new tokens
            tokens = token_generator(user.id, user.email.value, user.is_admin)

            # Optionally revoke old refresh token and store new one
            await self.uow.refresh_tokens.revoke_token(input_dto.refresh_token)

            # Commit transaction
            await self.uow.commit()

            # Return new tokens
            return RefreshTokenOutput(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_type="bearer",
                expires_in=token_expires_in,
            )
