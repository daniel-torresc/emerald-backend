"""
RefreshToken repository for token management operations.

This module provides database operations for the RefreshToken model,
including token validation, rotation, and revocation.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.refresh_token import RefreshToken
from src.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """
    Repository for RefreshToken model operations.

    Extends BaseRepository with token-specific operations:
    - Token hash lookups
    - Token validation (expiry, revocation)
    - Token rotation
    - Token family revocation (for reuse detection)
    - Expired token cleanup
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize RefreshTokenRepository.

        Args:
            session: Async database session
        """
        super().__init__(RefreshToken, session)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Get refresh token by its hash.

        Used during token refresh to validate the token.

        Args:
            token_hash: SHA-256 hash of the refresh token

        Returns:
            RefreshToken instance or None if not found

        Example:
            token_hash = hash_refresh_token(jwt_token)
            db_token = await token_repo.get_by_token_hash(token_hash)
            if db_token is None:
                raise InvalidTokenError()
        """
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def revoke_token(self, token_id: uuid.UUID) -> None:
        """
        Revoke a specific refresh token.

        Sets is_revoked=True and records revocation timestamp.
        Used during logout and token rotation.

        Args:
            token_id: UUID of the token to revoke

        Example:
            # During logout
            await token_repo.revoke_token(refresh_token.id)
        """
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )
        await self.session.flush()

    async def revoke_user_tokens(self, user_id: uuid.UUID) -> int:
        """
        Revoke all refresh tokens for a user.

        Used during:
        - Password change (force re-authentication)
        - Account lockout
        - Security incident response

        Args:
            user_id: UUID of the user

        Returns:
            Number of tokens revoked

        Example:
            # After password change
            count = await token_repo.revoke_user_tokens(user.id)
            logger.info(f"Revoked {count} tokens for user {user.id}")
        """
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )
        await self.session.flush()
        return result.rowcount

    async def revoke_token_family(self, token_family_id: uuid.UUID) -> int:
        """
        Revoke all tokens in a token family.

        This is used for reuse detection - when a revoked token is reused
        (indicating potential theft), the entire family is revoked.

        Args:
            token_family_id: UUID of the token family

        Returns:
            Number of tokens revoked

        Example:
            # Reuse detected!
            if db_token.is_revoked:
                count = await token_repo.revoke_token_family(db_token.token_family_id)
                logger.warning(
                    f"Token reuse detected! Revoked {count} tokens in family "
                    f"{db_token.token_family_id}"
                )
                raise InvalidTokenError("Token has been compromised")
        """
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_family_id == token_family_id,
                RefreshToken.is_revoked == False,
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )
        await self.session.flush()
        return result.rowcount

    async def delete_expired_tokens(self, before_date: datetime | None = None) -> int:
        """
        Delete expired refresh tokens from the database.

        This is a cleanup operation that should be run periodically
        (e.g., daily via cron job) to prevent token table bloat.

        Args:
            before_date: Delete tokens expired before this date.
                        If None, uses current time (delete all expired).

        Returns:
            Number of tokens deleted

        Example:
            # Delete all expired tokens (cleanup job)
            count = await token_repo.delete_expired_tokens()
            logger.info(f"Cleaned up {count} expired tokens")

            # Delete tokens expired more than 30 days ago
            cutoff = datetime.now(UTC) - timedelta(days=30)
            count = await token_repo.delete_expired_tokens(cutoff)
        """
        if before_date is None:
            before_date = datetime.now(UTC)

        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < before_date)
        )
        await self.session.flush()
        return result.rowcount

    async def get_user_active_tokens(self, user_id: uuid.UUID) -> list[RefreshToken]:
        """
        Get all active (non-revoked, non-expired) tokens for a user.

        Used for:
        - Debugging (how many sessions does user have?)
        - Security monitoring (unusual number of sessions?)
        - Admin tools (view user's active sessions)

        Args:
            user_id: UUID of the user

        Returns:
            List of active RefreshToken instances

        Example:
            active_tokens = await token_repo.get_user_active_tokens(user.id)
            print(f"User has {len(active_tokens)} active sessions")
        """
        query = (
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .order_by(RefreshToken.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_user_active_tokens(self, user_id: uuid.UUID) -> int:
        """
        Count active tokens for a user.

        Useful for rate limiting or security monitoring.

        Args:
            user_id: UUID of the user

        Returns:
            Number of active tokens

        Example:
            count = await token_repo.count_user_active_tokens(user.id)
            if count > 10:
                logger.warning(f"User {user.id} has {count} active sessions")
        """
        from sqlalchemy import func

        query = (
            select(func.count())
            .select_from(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one()
