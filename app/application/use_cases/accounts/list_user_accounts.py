"""List user accounts use case."""

from math import ceil
from uuid import UUID

from app.application.dto.account_dto import AccountListOutput, AccountOutput
from app.application.ports.outbound.unit_of_work_port import UnitOfWorkPort


class ListUserAccountsUseCase:
    """Use case for listing user's accounts."""

    def __init__(self, uow: UnitOfWorkPort):
        """
        Initialize use case.

        Args:
            uow: Unit of Work for managing transactions
        """
        self.uow = uow

    async def execute(
        self,
        current_user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
        include_shared: bool = True,
    ) -> AccountListOutput:
        """
        List accounts for the current user.

        Args:
            current_user_id: ID of user requesting accounts
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive accounts
            include_shared: Whether to include accounts shared with the user

        Returns:
            Paginated list of accounts
        """
        async with self.uow:
            # Get owned accounts
            owned_accounts = await self.uow.accounts.list_by_user(
                user_id=current_user_id,
                skip=skip,
                limit=limit,
                include_inactive=include_inactive,
            )

            accounts = owned_accounts

            # Optionally include shared accounts
            if include_shared:
                shared_accounts = await self.uow.accounts.list_shared_with_user(
                    user_id=current_user_id, skip=0, limit=limit
                )
                # Merge and limit
                accounts = owned_accounts + shared_accounts
                accounts = accounts[skip : skip + limit]

            # Calculate pagination metadata
            total = len(accounts) + skip  # Simplified estimation
            page = (skip // limit) + 1
            per_page = limit
            total_pages = ceil(total / per_page)

            # Convert to DTOs
            account_dtos = [AccountOutput.from_entity(account) for account in accounts]

            return AccountListOutput(
                accounts=account_dtos,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )
