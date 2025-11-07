"""
PostgreSQL implementation of AccountShareRepositoryPort.

This repository handles all database operations for AccountShare entities using PostgreSQL.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.outbound.account_share_repository_port import (
    AccountShareRepositoryPort,
)
from app.domain.entities.account_share import AccountShare
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.account_share_mapper import (
    AccountShareMapper,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.account_model import (
    AccountShareModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.base_repository import (
    BaseRepository,
)


class PostgresAccountShareRepository(
    BaseRepository[AccountShareModel, AccountShare], AccountShareRepositoryPort
):
    """
    PostgreSQL implementation of AccountShareRepositoryPort.

    Inherits common CRUD operations from BaseRepository and implements
    AccountShare-specific operations defined in AccountShareRepositoryPort.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize PostgreSQL account share repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, AccountShareModel, AccountShareMapper)

    async def list_by_account_id(self, account_id: UUID) -> list[AccountShare]:
        """
        List all shares for an account.

        Args:
            account_id: Account's unique identifier

        Returns:
            List of account share entities
        """
        stmt = select(AccountShareModel).where(
            AccountShareModel.account_id == account_id,
            AccountShareModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def list_by_user_id(self, user_id: UUID) -> list[AccountShare]:
        """
        List all account shares for a user.

        Args:
            user_id: User's unique identifier

        Returns:
            List of account share entities
        """
        stmt = select(AccountShareModel).where(
            AccountShareModel.user_id == user_id,
            AccountShareModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def find_by_account_and_user(
        self, account_id: UUID, user_id: UUID
    ) -> Optional[AccountShare]:
        """
        Find share by account and user.

        Args:
            account_id: Account's unique identifier
            user_id: User's unique identifier

        Returns:
            AccountShare entity if found, None otherwise
        """
        stmt = select(AccountShareModel).where(
            AccountShareModel.account_id == account_id,
            AccountShareModel.user_id == user_id,
            AccountShareModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)
