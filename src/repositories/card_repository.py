"""
Card repository for database operations.

This module provides the CardRepository class for managing card data access.
All queries are scoped to user ownership via account relationships.
"""

import uuid

from sqlalchemy import UnaryExpression, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Account, Card
from schemas import CardFilterParams, CardSortParams, PaginationParams, SortOrder
from .base import BaseRepository


class CardRepository(BaseRepository[Card]):
    """
    Repository for card database operations.

    Handles all database operations for cards with user-scoped access.
    Cards are accessed through account ownership - if a user owns the account,
    they own all cards linked to that account.

    Inherits from BaseRepository for standard CRUD operations with soft delete support.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize card repository.

        Args:
            session: Async database session for executing queries
        """
        super().__init__(Card, session)

    # ========================================================================
    # USER PARAMS METHODS
    # ========================================================================

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        filter_params: CardFilterParams,
        sort_params: CardSortParams,
        pagination_params: PaginationParams,
    ) -> tuple[list[Card], int]:
        """
        Get all cards for a user (via account ownership).

        Args:
            user_id: UUID of the user who owns the accounts
            filter_params:
            sort_params:
            pagination_params:

        Returns:
            List of Card objects ordered by created_at descending

        Example:
            # Get all active credit cards for user
            cards = await repo.get_by_user(
                user_id=user.id,
                card_type=CardType.credit_card
            )

            # Get cards for specific account with pagination
            cards = await repo.get_by_user(
                user_id=user.id,
                account_id=account.id,
                skip=0,
                limit=20
            )
        """
        filters = [Card.account.has(Account.user_id == user_id)]

        # Card type filter
        if filter_params.card_type is not None:
            filters.append(Card.card_type == filter_params.card_type)

        # Account filter
        if filter_params.account_id is not None:
            filters.append(Card.account_id == filter_params.account_id)

        order_by: list[UnaryExpression] = []

        # Get the model column from enum value
        sort_column = getattr(Card, sort_params.sort_by.value)

        # Apply sort direction
        if sort_params.sort_order == SortOrder.ASC:
            order_by.append(asc(sort_column))
        else:
            order_by.append(desc(sort_column))

        # Add secondary sort by id for deterministic pagination
        order_by.append(desc(Card.id))

        load_relationships = [
            selectinload(Card.account),
            selectinload(Card.financial_institution),
        ]

        return await self._list_and_count(
            filters=filters,
            order_by=order_by,
            load_relationships=load_relationships,
            offset=pagination_params.offset,
            limit=pagination_params.page_size,
        )

    async def get_by_id_for_user(
        self,
        card_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Card | None:
        """
        Get a card by ID if user owns the associated account.

        Args:
            card_id: UUID of the card to retrieve
            user_id: UUID of the user (must own the card's account)

        Returns:
            Card object if found and user owns it, None otherwise

        Example:
            card = await repo.get_by_id_for_user(
                card_id=uuid.UUID('...'),
                user_id=current_user.id
            )
            if not card:
                raise NotFoundError("Card not found")
        """
        query = (
            select(Card)
            .join(Account, Card.account_id == Account.id)
            .where(Card.id == card_id, Account.user_id == user_id)
            .options(
                selectinload(Card.account),
                selectinload(Card.financial_institution),
            )
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_account(
        self,
        account_id: uuid.UUID,
    ) -> list[Card]:
        """
        Get all cards for a specific account.

        Args:
            account_id: UUID of the account

        Returns:
            List of Card objects ordered by created_at descending

        Note:
            This method does NOT verify account ownership. The caller must ensure
            the user has access to the specified account before calling this method.

        Example:
            # After verifying user owns the account
            cards = await repo.get_by_account(account_id=account.id)
        """
        query = (
            select(Card)
            .where(Card.account_id == account_id)
            .options(
                selectinload(Card.financial_institution),
            )
        )
        query = self._apply_soft_delete_filter(query)

        # Order by creation date descending
        query = query.order_by(Card.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())
