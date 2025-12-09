"""
Card repository for database operations.

This module provides the CardRepository class for managing card data access.
All queries are scoped to user ownership via account relationships.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.account import Account
from src.models.card import Card
from src.models.enums import CardType
from src.repositories.base import BaseRepository


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

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        card_type: CardType | None = None,
        account_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Card]:
        """
        Get all cards for a user (via account ownership).

        Args:
            user_id: UUID of the user who owns the accounts
            card_type: Optional filter by card type (credit_card or debit_card)
            account_id: Optional filter by specific account
            include_deleted: Whether to include soft-deleted cards (default: False)
            skip: Number of records to skip for pagination (default: 0)
            limit: Maximum number of records to return (default: 100)

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
        query = (
            select(Card)
            .join(Account, Card.account_id == Account.id)
            .where(Account.user_id == user_id)
            .options(
                selectinload(Card.account),
                selectinload(Card.financial_institution),
            )
        )

        # Apply soft delete filter
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        # Apply optional filters
        if card_type is not None:
            query = query.where(Card.card_type == card_type)

        if account_id is not None:
            query = query.where(Card.account_id == account_id)

        # Apply pagination and ordering
        query = query.offset(skip).limit(limit).order_by(Card.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id_for_user(
        self,
        card_id: uuid.UUID,
        user_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Card | None:
        """
        Get a card by ID if user owns the associated account.

        Args:
            card_id: UUID of the card to retrieve
            user_id: UUID of the user (must own the card's account)
            include_deleted: Whether to return soft-deleted cards (default: False)

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

        # Apply soft delete filter
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_account(
        self,
        account_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> list[Card]:
        """
        Get all cards for a specific account.

        Args:
            account_id: UUID of the account
            include_deleted: Whether to include soft-deleted cards (default: False)

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

        # Apply soft delete filter
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        # Order by creation date descending
        query = query.order_by(Card.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        card_type: CardType | None = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Count cards for a user (via account ownership).

        Args:
            user_id: UUID of the user who owns the accounts
            card_type: Optional filter by card type
            include_deleted: Whether to include soft-deleted cards (default: False)

        Returns:
            Total number of cards matching criteria

        Example:
            total_credit_cards = await repo.count_by_user(
                user_id=user.id,
                card_type=CardType.credit_card
            )
        """
        query = (
            select(Card)
            .join(Account, Card.account_id == Account.id)
            .where(Account.user_id == user_id)
        )

        # Apply soft delete filter
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        # Apply optional card type filter
        if card_type is not None:
            query = query.where(Card.card_type == card_type)

        result = await self.session.execute(query)
        return len(result.scalars().all())
