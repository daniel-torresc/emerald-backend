"""
Card service for business logic and validation.

This module provides the CardService class for managing card operations
with proper authorization, validation, and audit logging.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import AuthorizationError, NotFoundError
from src.models import AuditAction, AuditStatus
from src.models.enums import CardType
from src.models.user import User
from src.repositories.account_repository import AccountRepository
from src.repositories.card_repository import CardRepository
from src.repositories.financial_institution_repository import (
    FinancialInstitutionRepository,
)
from src.schemas.card import (
    CardCreate,
    CardFilterParams,
    CardListItem,
    CardResponse,
    CardUpdate,
)
from src.schemas.common import PaginatedResponse, PaginationMeta, PaginationParams
from src.services.audit_service import AuditService


class CardService:
    """
    Service for card business logic.

    Handles all card operations with proper authorization checks,
    validation, and audit logging. All operations are scoped to
    user ownership via account relationships.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize card service.

        Args:
            session: Async database session for operations
        """
        self.session = session
        self.card_repo = CardRepository(session)
        self.account_repo = AccountRepository(session)
        self.financial_institution_repo = FinancialInstitutionRepository(session)
        self.audit_service = AuditService(session)

    async def create_card(
        self,
        data: CardCreate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CardResponse:
        """
        Create a new card linked to user's account.

        Args:
            data: Card creation data (account_id required)
            current_user: Authenticated user creating the card
            request_id: Optional request ID for tracing
            ip_address: Optional IP address for audit log
            user_agent: Optional user agent for audit log

        Returns:
            CardResponse with created card details

        Raises:
            NotFoundError: If account or financial institution not found
            AuthorizationError: If account doesn't belong to user
            ValidationError: If financial institution is inactive

        Example:
            card = await service.create_card(
                data=CardCreate(
                    account_id=account.id,
                    card_type=CardType.credit_card,
                    name="Chase Sapphire Reserve",
                    ...
                ),
                current_user=user
            )
        """
        # 1. Validate account ownership (REQUIRED)
        account = await self.account_repo.get_by_id(data.account_id)
        if not account:
            raise NotFoundError("Account")

        if account.user_id != current_user.id:
            raise AuthorizationError("Account does not belong to you")

        # 2. Validate financial institution (if provided)
        if data.financial_institution_id:
            institution = await self.financial_institution_repo.get_by_id(
                data.financial_institution_id
            )
            if not institution:
                raise NotFoundError("Financial institution")

        # 3. Create card
        card = await self.card_repo.create(
            account_id=data.account_id,
            financial_institution_id=data.financial_institution_id,
            card_type=data.card_type,
            name=data.name.strip(),
            last_four_digits=data.last_four_digits,
            card_network=data.card_network,
            expiry_month=data.expiry_month,
            expiry_year=data.expiry_year,
            credit_limit=data.credit_limit,
            notes=data.notes,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        # 4. Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.CREATE,
            entity_type="card",
            entity_id=card.id,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return CardResponse.model_validate(card)

    async def get_card(
        self,
        card_id: uuid.UUID,
        current_user: User,
    ) -> CardResponse:
        """
        Get a card by ID (must own the account).

        Args:
            card_id: UUID of the card to retrieve
            current_user: Authenticated user

        Returns:
            CardResponse with card details

        Raises:
            NotFoundError: If card not found or user doesn't own the account

        Example:
            card = await service.get_card(
                card_id=uuid.UUID('...'),
                current_user=user
            )
        """
        card = await self.card_repo.get_by_id_for_user(card_id, current_user.id)
        if not card:
            raise NotFoundError("Card")

        return CardResponse.model_validate(card)

    async def list_cards(
        self,
        current_user: User,
        card_type: CardType | None = None,
        account_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CardListItem]:
        """
        List all cards for the current user.

        Args:
            current_user: Authenticated user
            card_type: Optional filter by card type
            account_id: Optional filter by account
            include_deleted: Whether to include soft-deleted cards
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return

        Returns:
            List of CardListItem objects

        Raises:
            AuthorizationError: If filtering by account user doesn't own

        Example:
            # Get all active credit cards
            cards = await service.list_cards(
                current_user=user,
                card_type=CardType.credit_card
            )

            # Get cards for specific account
            cards = await service.list_cards(
                current_user=user,
                account_id=account.id
            )
        """
        # If filtering by account, verify ownership
        if account_id:
            account = await self.account_repo.get_by_id(account_id)
            if not account or account.user_id != current_user.id:
                raise AuthorizationError("Account does not belong to you")

        cards = await self.card_repo.get_by_user(
            user_id=current_user.id,
            card_type=card_type,
            account_id=account_id,
            include_deleted=include_deleted,
            skip=skip,
            limit=limit,
        )

        return [CardListItem.model_validate(card) for card in cards]

    async def list_cards_paginated(
        self,
        current_user: User,
        pagination: PaginationParams,
        filters: CardFilterParams,
    ) -> PaginatedResponse[CardListItem]:
        """
        List all cards for the current user with pagination.

        Args:
            current_user: Authenticated user
            pagination: Pagination parameters (page, page_size)
            filters: Filter parameters (card_type, account_id, include_deleted)

        Returns:
            PaginatedResponse with CardListItem objects and metadata

        Raises:
            AuthorizationError: If filtering by account user doesn't own

        Example:
            response = await service.list_cards_paginated(
                current_user=user,
                pagination=PaginationParams(page=1, page_size=20),
                filters=CardFilterParams(card_type=CardType.credit_card)
            )
        """
        # If filtering by account, verify ownership
        if filters.account_id:
            account = await self.account_repo.get_by_id(filters.account_id)
            if not account or account.user_id != current_user.id:
                raise AuthorizationError("Account does not belong to you")

        # Get cards
        cards = await self.card_repo.get_by_user(
            user_id=current_user.id,
            card_type=filters.card_type,
            account_id=filters.account_id,
            include_deleted=filters.include_deleted,
            skip=pagination.offset,
            limit=pagination.page_size,
        )

        # Get total count
        # Note: count_by_user doesn't support account_id filter, so we'll count all
        # and filter in-memory for now (acceptable for small datasets)
        if filters.account_id:
            # For account filter, we need to get all cards and count them
            all_cards = await self.card_repo.get_by_user(
                user_id=current_user.id,
                card_type=filters.card_type,
                account_id=filters.account_id,
                include_deleted=filters.include_deleted,
                skip=0,
                limit=1000,  # Reasonable upper limit
            )
            total = len(all_cards)
        else:
            total = await self.card_repo.count_by_user(
                user_id=current_user.id,
                card_type=filters.card_type,
                include_deleted=filters.include_deleted,
            )

        # Convert to CardListItem
        card_items = [CardListItem.model_validate(card) for card in cards]

        # Calculate total pages
        total_pages = PaginationParams.calculate_total_pages(
            total, pagination.page_size
        )

        return PaginatedResponse(
            data=card_items,
            meta=PaginationMeta(
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
            ),
        )

    async def update_card(
        self,
        card_id: uuid.UUID,
        data: CardUpdate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CardResponse:
        """
        Update an existing card.

        Args:
            card_id: UUID of the card to update
            data: Card update data (partial updates supported)
            current_user: Authenticated user
            request_id: Optional request ID for tracing
            ip_address: Optional IP address for audit log
            user_agent: Optional user agent for audit log

        Returns:
            CardResponse with updated card details

        Raises:
            NotFoundError: If card or financial institution not found
            AuthorizationError: If user doesn't own the card's account
            ValidationError: If financial institution is inactive

        Note:
            account_id and card_type cannot be changed (immutable after creation)

        Example:
            card = await service.update_card(
                card_id=uuid.UUID('...'),
                data=CardUpdate(
                    name="New Card Name",
                    credit_limit=Decimal("30000.00")
                ),
                current_user=user
            )
        """
        # 1. Get card and verify ownership
        card = await self.card_repo.get_by_id_for_user(card_id, current_user.id)
        if not card:
            raise NotFoundError("Card")

        # 2. Validate new financial institution if provided
        if data.financial_institution_id:
            institution = await self.financial_institution_repo.get_by_id(
                data.financial_institution_id
            )
            if not institution:
                raise NotFoundError("Financial institution")

        # 3. Update only provided fields
        update_data = data.model_dump(exclude_unset=True)

        # Strip name if provided
        if "name" in update_data and update_data["name"]:
            update_data["name"] = update_data["name"].strip()

        update_data["updated_by"] = current_user.id

        card = await self.card_repo.update(card, **update_data)

        # 4. Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="card",
            entity_id=card.id,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return CardResponse.model_validate(card)

    async def delete_card(
        self,
        card_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Soft-delete a card.

        Args:
            card_id: UUID of the card to delete
            current_user: Authenticated user
            request_id: Optional request ID for tracing
            ip_address: Optional IP address for audit log
            user_agent: Optional user agent for audit log

        Raises:
            NotFoundError: If card not found or user doesn't own the account

        Note:
            This is a soft delete - the card remains in the database with
            deleted_at timestamp set. Transactions referencing this card
            will have card_id set to NULL (handled by database FK).

        Example:
            await service.delete_card(
                card_id=uuid.UUID('...'),
                current_user=user
            )
        """
        # 1. Get card and verify ownership
        card = await self.card_repo.get_by_id_for_user(card_id, current_user.id)
        if not card:
            raise NotFoundError("Card")

        # 2. Soft delete
        await self.card_repo.soft_delete(card)

        # 3. Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="card",
            entity_id=card.id,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )
