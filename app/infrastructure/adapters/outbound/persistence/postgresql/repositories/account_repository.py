"""
PostgreSQL implementation of AccountRepositoryPort.

This repository handles all database operations for Account entities using PostgreSQL.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.ports.outbound.account_repository_port import AccountRepositoryPort
from app.domain.entities.account import Account
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.account_mapper import (
    AccountMapper,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.account_model import (
    AccountModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.base_repository import (
    BaseRepository,
)


class PostgresAccountRepository(BaseRepository[AccountModel, Account], AccountRepositoryPort):
    """
    PostgreSQL implementation of AccountRepositoryPort.

    Inherits common CRUD operations from BaseRepository and implements
    Account-specific operations defined in AccountRepositoryPort.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize PostgreSQL account repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, AccountModel, AccountMapper)

    async def list_by_user_id(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[Account]:
        """
        List accounts owned by a user.

        Args:
            user_id: User's unique identifier
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive accounts

        Returns:
            List of account entities
        """
        stmt = (
            select(AccountModel)
            .where(
                AccountModel.user_id == user_id,
                AccountModel.deleted_at.is_(None),
            )
            .options(selectinload(AccountModel.shares))  # Eager load shares
        )

        if not include_inactive:
            stmt = stmt.where(AccountModel.is_active.is_(True))

        stmt = stmt.offset(skip).limit(limit).order_by(AccountModel.created_at.desc())

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def find_by_user_and_name(self, user_id: UUID, name: str) -> Optional[Account]:
        """
        Find account by user ID and account name.

        Args:
            user_id: User's unique identifier
            name: Account name

        Returns:
            Account entity if found, None otherwise
        """
        stmt = (
            select(AccountModel)
            .where(
                AccountModel.user_id == user_id,
                AccountModel.account_name == name,
                AccountModel.deleted_at.is_(None),
            )
            .options(selectinload(AccountModel.shares))
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)

    # Override get_by_id to include eager loading of shares
    async def get_by_id(self, account_id: UUID, include_deleted: bool = False) -> Optional[Account]:
        """
        Retrieve account by ID with eager loaded shares.

        Args:
            account_id: Account's unique identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            Account entity if found, None otherwise
        """
        stmt = (
            select(AccountModel)
            .where(AccountModel.id == account_id)
            .options(selectinload(AccountModel.shares))
        )

        if not include_deleted:
            stmt = stmt.where(AccountModel.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)
