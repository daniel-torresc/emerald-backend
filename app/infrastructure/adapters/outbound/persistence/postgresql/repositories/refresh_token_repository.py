"""
PostgreSQL implementation of RefreshTokenRepositoryPort.

This repository handles all database operations for RefreshToken entities using PostgreSQL.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.outbound.refresh_token_repository_port import (
    RefreshTokenRepositoryPort,
)
from app.domain.entities.refresh_token import RefreshToken
from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.refresh_token_mapper import (
    RefreshTokenMapper,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.refresh_token_model import (
    RefreshTokenModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.repositories.base_repository import (
    BaseRepository,
)


class PostgresRefreshTokenRepository(
    BaseRepository[RefreshTokenModel, RefreshToken], RefreshTokenRepositoryPort
):
    """
    PostgreSQL implementation of RefreshTokenRepositoryPort.

    Inherits common CRUD operations from BaseRepository and implements
    RefreshToken-specific operations defined in RefreshTokenRepositoryPort.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize PostgreSQL refresh token repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, RefreshTokenModel, RefreshTokenMapper)

    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Retrieve refresh token by token hash.

        Args:
            token_hash: SHA-256 hash of the token

        Returns:
            RefreshToken entity if found, None otherwise
        """
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self.mapper.to_entity(model)

    async def list_by_user_id(
        self,
        user_id: UUID,
        include_revoked: bool = False,
    ) -> list[RefreshToken]:
        """
        List refresh tokens for a user.

        Args:
            user_id: User's unique identifier
            include_revoked: Whether to include revoked tokens

        Returns:
            List of refresh token entities
        """
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)

        if not include_revoked:
            stmt = stmt.where(RefreshTokenModel.is_revoked.is_(False))

        stmt = stmt.order_by(RefreshTokenModel.created_at.desc())

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self.mapper.to_entity(model) for model in models]

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """
        Revoke all refresh tokens for a user.

        Used when user changes password or logs out from all devices.

        Args:
            user_id: User's unique identifier
        """
        from datetime import UTC, datetime

        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.is_revoked.is_(False),
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        for model in models:
            model.is_revoked = True
            model.revoked_at = datetime.now(UTC)

        await self.session.flush()

    async def revoke_by_family_id(self, token_family_id: UUID) -> None:
        """
        Revoke all tokens in a token family.

        Used when token reuse is detected (security breach).

        Args:
            token_family_id: Token family identifier
        """
        from datetime import UTC, datetime

        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token_family_id == token_family_id,
            RefreshTokenModel.is_revoked.is_(False),
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        for model in models:
            model.is_revoked = True
            model.revoked_at = datetime.now(UTC)

        await self.session.flush()

    async def cleanup_expired(self) -> int:
        """
        Delete expired tokens from the database.

        This is typically run as a scheduled job to keep the database clean.

        Returns:
            Number of tokens deleted
        """
        from datetime import UTC, datetime

        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.expires_at < datetime.now(UTC)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        count = len(models)
        for model in models:
            await self.session.delete(model)

        await self.session.flush()
        return count
