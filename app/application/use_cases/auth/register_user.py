"""Register user use case."""

from datetime import datetime
from uuid import uuid4

from app.application.dto.auth_dto import RegisterUserInput, UserProfileOutput
from app.application.exceptions import AlreadyExistsError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.value_objects.username import Username


class RegisterUserUseCase:
    """Use case for registering a new user."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, input_dto: RegisterUserInput, password_hasher
    ) -> UserProfileOutput:
        """
        Register a new user account.

        Args:
            input_dto: User registration data
            password_hasher: Callable to hash password (injected from infrastructure)

        Returns:
            Created user profile

        Raises:
            AlreadyExistsError: If user with email or username already exists
        """
        async with self.uow:
            # Create value objects
            email = Email(input_dto.email)
            username = Username(input_dto.username)

            # Check if user already exists
            if await self.uow.users.exists_by_email(email):
                raise AlreadyExistsError(
                    message=f"User with email '{email.value}' already exists",
                    resource_type="User",
                    field="email",
                    value=email.value,
                )

            if await self.uow.users.exists_by_username(username):
                raise AlreadyExistsError(
                    message=f"User with username '{username.value}' already exists",
                    resource_type="User",
                    field="username",
                    value=username.value,
                )

            # Hash password
            hashed_password = password_hasher(input_dto.password)
            password_hash = PasswordHash(hashed_password)

            # Create user entity
            user = User(
                id=uuid4(),
                email=email,
                username=username,
                password_hash=password_hash,
                full_name=input_dto.full_name,
                is_active=True,
                is_admin=False,
                roles=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                deleted_at=None,
            )

            # Persist user
            created_user = await self.uow.users.add(user)

            # Commit transaction
            await self.uow.commit()

            # Return DTO
            return UserProfileOutput.from_entity(created_user)
