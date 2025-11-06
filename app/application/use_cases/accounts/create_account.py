"""Create account use case."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.application.dto.account_dto import AccountOutput, CreateAccountInput
from app.application.exceptions import AlreadyExistsError
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort
from app.domain.entities.account import Account
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.money import Money


class CreateAccountUseCase:
    """Use case for creating a new financial account."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self, input_dto: CreateAccountInput, current_user_id: UUID
    ) -> AccountOutput:
        """
        Create a new account for the current user.

        Args:
            input_dto: Account creation data
            current_user_id: ID of user creating the account

        Returns:
            Created account data

        Raises:
            AlreadyExistsError: If account with same name exists for user
        """
        async with self.uow:
            # Check if account with same name already exists for this user
            existing = await self.uow.accounts.find_by_user_and_name(
                user_id=current_user_id, name=input_dto.name
            )
            if existing:
                raise AlreadyExistsError(
                    message=f"Account with name '{input_dto.name}' already exists",
                    resource_type="Account",
                    field="name",
                    value=input_dto.name,
                )

            # Create domain entity
            account = Account(
                id=uuid4(),
                user_id=current_user_id,
                name=input_dto.name,
                description=input_dto.description,
                balance=Money(
                    amount=Decimal("0.00"), currency=Currency.USD
                ),  # Start at zero
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                deleted_at=None,
                shared_with_user_ids=[],
            )

            # Persist through repository
            saved_account = await self.uow.accounts.add(account)

            # Commit transaction
            await self.uow.commit()

            # Convert to output DTO
            return AccountOutput.from_entity(saved_account)
