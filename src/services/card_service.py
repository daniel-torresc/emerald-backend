"""
Card service for business logic and validation.

This module provides the CardService class for managing card operations
with proper authorization, validation, and audit logging.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthorizationError, NotFoundError
from models import AuditAction, AuditStatus, Card
from models.user import User
from repositories.account_repository import AccountRepository
from repositories.card_repository import CardRepository
from repositories.financial_institution_repository import (
    FinancialInstitutionRepository,
)
from schemas.card import (
    CardCreate,
    CardFilterParams,
    CardListItem,
    CardResponse,
    CardUpdate,
)
from schemas.common import PaginatedResponse, PaginationMeta, PaginationParams
from services.audit_service import AuditService


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
        card = Card(
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
        card = await self.card_repo.add(card)
        await self.session.commit()

        # 4. Audit log
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.CREATE,
            entity_type="card",
            entity_id=card.id,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
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
        pagination: PaginationParams,
        filters: CardFilterParams,
    ) -> PaginatedResponse[CardListItem]:
        """
        List all cards for the current user with pagination.

        Args:
            current_user: Authenticated user
            pagination: Pagination parameters (page, page_size)
            filters: Filter parameters (card_type, account_id)

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
        cards = await self.card_repo.search_by_user(
            user_id=current_user.id,
            card_type=filters.card_type,
            account_id=filters.account_id,
            offset=pagination.offset,
            limit=pagination.page_size,
        )

        total_count = await self.card_repo.search_count_by_user(
            user_id=current_user.id,
            card_type=filters.card_type,
            account_id=filters.account_id,
        )

        # Convert to CardListItem
        items = [CardListItem.model_validate(card) for card in cards]

        # Calculate total pages
        total_pages = PaginationParams.calculate_total_pages(
            total_count, pagination.page_size
        )

        metadata = PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total_count,
            total_pages=total_pages,
        )

        return PaginatedResponse(data=items, meta=metadata)

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

        # 3. Get only provided fields
        update_dict = data.model_dump(exclude_unset=True)

        if not update_dict:
            return CardResponse.model_validate(card)  # Nothing to update

        # 4. Capture old values for audit (handle enum safely)
        old_card_network = card.card_network
        old_values = {
            "name": card.name,
            "last_four_digits": card.last_four_digits,
            "card_network": old_card_network.value
            if hasattr(old_card_network, "value")
            else old_card_network,
            "expiry_month": card.expiry_month,
            "expiry_year": card.expiry_year,
            "credit_limit": str(card.credit_limit) if card.credit_limit else None,
            "financial_institution_id": str(card.financial_institution_id)
            if card.financial_institution_id
            else None,
            "notes": card.notes,
        }

        # 5. Apply changes to model instance
        for key, value in update_dict.items():
            setattr(card, key, value)
        card.updated_by = current_user.id

        # 6. Persist
        card = await self.card_repo.update(card)

        # 7. Capture new values for audit (handle enum safely)
        new_card_network = card.card_network
        new_values = {
            "name": card.name,
            "last_four_digits": card.last_four_digits,
            "card_network": new_card_network.value
            if hasattr(new_card_network, "value")
            else new_card_network,
            "expiry_month": card.expiry_month,
            "expiry_year": card.expiry_year,
            "credit_limit": str(card.credit_limit) if card.credit_limit else None,
            "financial_institution_id": str(card.financial_institution_id)
            if card.financial_institution_id
            else None,
            "notes": card.notes,
        }

        # 8. Audit log with old/new values
        await self.audit_service.log_event(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="card",
            entity_id=card.id,
            old_values=old_values,
            new_values=new_values,
            extra_metadata={"changed_fields": list(update_dict.keys())},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        # 9. Commit transaction
        await self.session.commit()

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
            request_id=request_id,
        )
