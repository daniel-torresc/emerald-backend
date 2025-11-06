"""
Mapper between AccountShare domain entity and AccountShareModel database model.

This mapper handles bidirectional conversion:
- to_entity(): Convert SQLAlchemy model → Domain entity
- to_model(): Convert Domain entity → SQLAlchemy model

The mapper lives in the Infrastructure layer and knows about both:
- Domain entities (app.domain.entities.account_share.AccountShare)
- Database models (app.infrastructure...models.account_model.AccountShareModel)
"""

from typing import Optional

from app.domain.entities.account_share import AccountShare
from app.domain.value_objects.permission import Permission
from app.infrastructure.adapters.outbound.persistence.postgresql.models.account_model import (
    AccountShareModel,
)
from app.infrastructure.adapters.outbound.persistence.postgresql.models.enums import (
    PermissionLevel,
)


class AccountShareMapper:
    """
    Mapper between AccountShare entity and AccountShareModel.

    Handles conversion between:
    - Pure domain entity (AccountShare) with Permission list and boolean flags
    - SQLAlchemy ORM model (AccountShareModel) with PermissionLevel enum

    Note: The domain and database models have different permission representations:
    - Domain: Uses list of Permission enums + boolean flags (can_view, can_edit, can_delete)
    - Database: Uses PermissionLevel enum (OWNER, EDITOR, VIEWER)

    This mapper translates between these two representations.
    """

    @staticmethod
    def _permission_level_to_flags(level: PermissionLevel) -> tuple[bool, bool, bool]:
        """
        Convert PermissionLevel enum to boolean flags.

        Args:
            level: PermissionLevel from database

        Returns:
            Tuple of (can_view, can_edit, can_delete)
        """
        if level == PermissionLevel.OWNER:
            return (True, True, True)
        elif level == PermissionLevel.EDITOR:
            return (True, True, False)
        else:  # VIEWER
            return (True, False, False)

    @staticmethod
    def _flags_to_permission_level(can_view: bool, can_edit: bool, can_delete: bool) -> PermissionLevel:
        """
        Convert boolean flags to PermissionLevel enum.

        Args:
            can_view: Whether user can view
            can_edit: Whether user can edit
            can_delete: Whether user can delete

        Returns:
            Corresponding PermissionLevel
        """
        if can_delete:
            return PermissionLevel.OWNER
        elif can_edit:
            return PermissionLevel.EDITOR
        else:
            return PermissionLevel.VIEWER

    @staticmethod
    def to_entity(model: AccountShareModel) -> AccountShare:
        """
        Convert SQLAlchemy model to domain entity.

        Args:
            model: AccountShareModel from database

        Returns:
            AccountShare domain entity

        Example:
            share_model = session.get(AccountShareModel, share_id)
            share_entity = AccountShareMapper.to_entity(share_model)
        """
        # Convert PermissionLevel to boolean flags
        can_view, can_edit, can_delete = AccountShareMapper._permission_level_to_flags(
            model.permission_level
        )

        # For now, use empty permissions list (can be populated based on permission_level if needed)
        permissions: list[Permission] = []
        if can_view:
            permissions.append(Permission.ACCOUNT_READ)
        if can_edit:
            permissions.append(Permission.ACCOUNT_WRITE)
        if can_delete:
            permissions.append(Permission.ACCOUNT_DELETE)

        return AccountShare(
            id=model.id,
            account_id=model.account_id,
            shared_by_user_id=model.account.user_id,  # Get owner from account
            shared_with_user_id=model.user_id,
            permissions=permissions,
            can_view=can_view,
            can_edit=can_edit,
            can_delete=can_delete,
            expires_at=None,  # Not in database model
            created_at=model.created_at,
            revoked_at=model.deleted_at,  # Map deleted_at to revoked_at
        )

    @staticmethod
    def to_model(
        entity: AccountShare, existing_model: Optional[AccountShareModel] = None
    ) -> AccountShareModel:
        """
        Convert domain entity to SQLAlchemy model.

        Args:
            entity: AccountShare domain entity
            existing_model: Optional existing model to update (for updates)

        Returns:
            AccountShareModel for database persistence

        Example:
            # Create new model
            share_entity = AccountShare(...)
            share_model = AccountShareMapper.to_model(share_entity)
            session.add(share_model)

            # Update existing model
            share_entity.can_edit = False
            updated_model = AccountShareMapper.to_model(share_entity, existing_model)
            session.flush()
        """
        # Convert boolean flags to PermissionLevel
        permission_level = AccountShareMapper._flags_to_permission_level(
            entity.can_view, entity.can_edit, entity.can_delete
        )

        if existing_model:
            # Update existing model (for UPDATE operations)
            existing_model.permission_level = permission_level
            existing_model.updated_at = (
                entity.created_at if entity.created_at else existing_model.updated_at
            )
            existing_model.deleted_at = entity.revoked_at  # Map revoked_at to deleted_at
            return existing_model
        else:
            # Create new model (for INSERT operations)
            return AccountShareModel(
                id=entity.id,
                account_id=entity.account_id,
                user_id=entity.shared_with_user_id,
                permission_level=permission_level,
                created_at=entity.created_at,
                updated_at=entity.created_at,
                deleted_at=entity.revoked_at,  # Map revoked_at to deleted_at
            )
