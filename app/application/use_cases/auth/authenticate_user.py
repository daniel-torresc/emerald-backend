"""Authenticate user use case."""

from app.application.dto.auth_dto import LoginInput, LoginOutput, UserProfileOutput
from app.application.exceptions import NotFoundError, UnauthorizedError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.domain.value_objects.email import Email


class AuthenticateUserUseCase:
    """Use case for authenticating a user."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self,
        input_dto: LoginInput,
        password_verifier,
        token_generator,
        token_expires_in: int = 1800,
    ) -> LoginOutput:
        """
        Authenticate user and generate tokens.

        Args:
            input_dto: Login credentials
            password_verifier: Callable to verify password (injected from infrastructure)
            token_generator: Callable to generate JWT tokens (injected from infrastructure)
            token_expires_in: Token expiry time in seconds (default 30 minutes)

        Returns:
            Login response with access token, refresh token, and user profile

        Raises:
            UnauthorizedError: If credentials are invalid
            NotFoundError: If user doesn't exist
        """
        async with self.uow:
            # Create value object
            email = Email(input_dto.email)

            # Get user by email
            user = await self.uow.users.get_by_email(email)

            if user is None:
                raise NotFoundError(
                    message="Invalid email or password",
                    resource_type="User",
                )

            # Check if user is active
            if not user.is_active:
                raise UnauthorizedError(message="User account is inactive")

            # Verify password
            is_valid = password_verifier(
                input_dto.password, user.password_hash.value
            )

            if not is_valid:
                raise UnauthorizedError(message="Invalid email or password")

            # Generate tokens
            tokens = token_generator(user.id, user.email.value, user.is_admin)

            # Commit transaction (for audit logging if implemented)
            await self.uow.commit()

            # Return login response
            return LoginOutput(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_type="bearer",
                expires_in=token_expires_in,
                user=UserProfileOutput.from_entity(user),
            )
