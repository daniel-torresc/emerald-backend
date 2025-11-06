"""
RefreshToken SQLAlchemy model for JWT refresh token management.

This module implements refresh token storage for token rotation security:
- Tokens are stored as SHA-256 hashes (not plain tokens)
- Token families track rotation chains
- Reuse detection prevents token theft
- Expired tokens are automatically filtered
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.adapters.outbound.persistence.postgresql.models.base import Base


class RefreshTokenModel(Base):
    """
    RefreshToken SQLAlchemy model for managing JWT refresh tokens.

    This is the ORM model for database persistence. Pure SQLAlchemy with no business logic.
    Business logic lives in domain.entities.refresh_token.RefreshToken (if needed).

    This model implements the refresh token rotation pattern for security:

    1. When a refresh token is used, it's revoked and a new one is issued
    2. All tokens in a family share the same token_family_id
    3. If a revoked token is reused (detected theft), the entire family is revoked
    4. Tokens expire after settings.refresh_token_expire_days (default: 7 days)

    Security Features:
    - Tokens stored as SHA-256 hashes (database compromise doesn't leak tokens)
    - Token rotation on every use (limits token lifetime)
    - Reuse detection via token family (detects theft attempts)
    - Automatic expiration (limits attack window)

    Attributes:
        id: UUID primary key
        token_hash: SHA-256 hash of the JWT refresh token
        token_family_id: UUID linking rotated tokens in the same family
        user_id: Foreign key to User who owns the token
        expires_at: When the token expires
        is_revoked: Whether the token has been revoked (used or invalidated)
        revoked_at: When the token was revoked
        created_at: When the token was created
        user: Relationship to UserModel

    Token Lifecycle:
        1. Login: Create new token with new token_family_id
        2. Refresh: Revoke old token, create new token with same token_family_id
        3. Reuse detected: Revoke entire token family
        4. Logout: Revoke token
        5. Password change: Revoke all user's tokens

    Example:
        # Create new token family on login
        token = RefreshTokenModel(
            token_hash=hash_refresh_token(jwt_token),
            token_family_id=uuid.uuid4(),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        # Rotate token on refresh
        old_token.is_revoked = True
        new_token = RefreshTokenModel(
            token_hash=hash_refresh_token(new_jwt_token),
            token_family_id=old_token.token_family_id,  # Same family!
            user_id=old_token.user_id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        # Detect reuse and revoke family
        if old_token.is_revoked:
            # Token already used - possible theft!
            session.execute(
                update(RefreshTokenModel)
                .where(RefreshTokenModel.token_family_id == old_token.token_family_id)
                .values(is_revoked=True, revoked_at=datetime.now(UTC))
            )
    """

    __tablename__ = "refresh_tokens"

    # Token storage
    token_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 produces 64-character hex string
        nullable=False,
        unique=True,
        index=True,
    )

    # Token family for rotation tracking
    token_family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # User ownership
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token validity
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Revocation status
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationship to User
    user: Mapped["UserModel"] = relationship(  # type: ignore
        "UserModel",
        lazy="selectin",
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Index for finding valid tokens by user
        Index("ix_refresh_tokens_user_valid", "user_id", "is_revoked", "expires_at"),
        # Index for finding tokens by family
        Index("ix_refresh_tokens_family", "token_family_id", "is_revoked"),
        # Index for cleanup of expired tokens
        Index("ix_refresh_tokens_cleanup", "expires_at", "is_revoked"),
    )

    def __repr__(self) -> str:
        """String representation of RefreshTokenModel."""
        return (
            f"RefreshTokenModel(id={self.id}, user_id={self.user_id}, "
            f"family_id={self.token_family_id}, revoked={self.is_revoked})"
        )

    @property
    def is_expired(self) -> bool:
        """
        Check if token has expired.

        Returns:
            True if token has expired, False otherwise
        """
        return datetime.now(UTC) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """
        Check if token is valid (not revoked and not expired).

        Returns:
            True if token is valid, False otherwise
        """
        return not self.is_revoked and not self.is_expired
