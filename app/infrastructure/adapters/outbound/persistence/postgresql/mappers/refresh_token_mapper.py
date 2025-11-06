"""
Mapper between RefreshToken domain entity and RefreshTokenModel database model.

This mapper handles bidirectional conversion:
- to_entity(): Convert SQLAlchemy model → Domain entity
- to_model(): Convert Domain entity → SQLAlchemy model

The mapper lives in the Infrastructure layer and knows about both:
- Domain entities (app.domain.entities.refresh_token.RefreshToken)
- Database models (app.infrastructure...models.refresh_token_model.RefreshTokenModel)
"""

from typing import Optional

from app.domain.entities.refresh_token import RefreshToken
from app.infrastructure.adapters.outbound.persistence.postgresql.models.refresh_token_model import (
    RefreshTokenModel,
)


class RefreshTokenMapper:
    """
    Mapper between RefreshToken entity and RefreshTokenModel.

    Handles conversion between:
    - Pure domain entity (RefreshToken) with plain token
    - SQLAlchemy ORM model (RefreshTokenModel) with token hash and family tracking

    Note: The database stores token_hash (SHA-256), not plain token.
    The domain entity expects plain token string.
    """

    @staticmethod
    def to_entity(model: RefreshTokenModel) -> RefreshToken:
        """
        Convert SQLAlchemy model to domain entity.

        Args:
            model: RefreshTokenModel from database

        Returns:
            RefreshToken domain entity

        Note: The plain token cannot be recovered from the hash.
        This method should only be called when the plain token is not needed,
        or the token_hash will be used as the token placeholder.

        Example:
            token_model = session.get(RefreshTokenModel, token_id)
            token_entity = RefreshTokenMapper.to_entity(token_model)
        """
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token=model.token_hash,  # Note: This is the hash, not the plain token
            expires_at=model.expires_at,
            created_at=model.created_at,
            revoked_at=model.revoked_at,
        )

    @staticmethod
    def to_model(
        entity: RefreshToken,
        token_hash: str,
        token_family_id,
        existing_model: Optional[RefreshTokenModel] = None,
    ) -> RefreshTokenModel:
        """
        Convert domain entity to SQLAlchemy model.

        Args:
            entity: RefreshToken domain entity
            token_hash: SHA-256 hash of the token (computed externally)
            token_family_id: UUID for token family tracking
            existing_model: Optional existing model to update (for updates)

        Returns:
            RefreshTokenModel for database persistence

        Example:
            # Create new model
            token_entity = RefreshToken(...)
            token_hash = hashlib.sha256(token_entity.token.encode()).hexdigest()
            token_model = RefreshTokenMapper.to_model(token_entity, token_hash, family_id)
            session.add(token_model)

            # Update existing model (revoke)
            token_entity.revoke()
            updated_model = RefreshTokenMapper.to_model(
                token_entity, token_hash, family_id, existing_model
            )
            session.flush()
        """
        if existing_model:
            # Update existing model (for UPDATE operations, typically revocation)
            existing_model.is_revoked = entity.is_revoked()
            existing_model.revoked_at = entity.revoked_at
            return existing_model
        else:
            # Create new model (for INSERT operations)
            return RefreshTokenModel(
                id=entity.id,
                token_hash=token_hash,
                token_family_id=token_family_id,
                user_id=entity.user_id,
                expires_at=entity.expires_at,
                is_revoked=entity.is_revoked(),
                revoked_at=entity.revoked_at,
                created_at=entity.created_at,
            )
