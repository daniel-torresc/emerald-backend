"""
Mapper between Role domain entity and RoleModel database model.

This mapper handles bidirectional conversion:
- to_entity(): Convert SQLAlchemy model → Domain entity
- to_model(): Convert Domain entity → SQLAlchemy model

The mapper lives in the Infrastructure layer and knows about both:
- Domain entities (app.domain.entities.role.Role)
- Database models (app.infrastructure...models.user_model.RoleModel)

Permissions are stored as:
- JSONB array of strings in database
- List of Permission enum values in domain
"""

from typing import Optional

from app.domain.entities.role import Role
from app.domain.value_objects.permission import Permission
from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import (
    RoleModel,
)


class RoleMapper:
    """
    Mapper between Role entity and RoleModel.

    Handles conversion between:
    - Pure domain entity (Role) with Permission enum
    - SQLAlchemy ORM model (RoleModel) with JSONB array of strings
    """

    @staticmethod
    def to_entity(model: RoleModel) -> Role:
        """
        Convert SQLAlchemy model to domain entity.

        Args:
            model: RoleModel from database

        Returns:
            Role domain entity

        Example:
            role_model = session.get(RoleModel, role_id)
            role_entity = RoleMapper.to_entity(role_model)
        """
        # Convert string permissions to Permission enum
        permissions = [Permission.from_string(p) for p in model.permissions]

        # Determine if this is a system role (admin, user, readonly are system roles)
        is_system_role = model.name.lower() in ("admin", "user", "readonly")

        return Role(
            id=model.id,
            name=model.name,
            description=model.description or "",  # Domain expects non-empty string
            permissions=permissions,
            is_system_role=is_system_role,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Role, existing_model: Optional[RoleModel] = None) -> RoleModel:
        """
        Convert domain entity to SQLAlchemy model.

        Args:
            entity: Role domain entity
            existing_model: Optional existing model to update (for updates)

        Returns:
            RoleModel for database persistence

        Example:
            # Create new model
            role_entity = Role(...)
            role_model = RoleMapper.to_model(role_entity)
            session.add(role_model)

            # Update existing model
            role_entity.description = "New description"
            updated_model = RoleMapper.to_model(role_entity, existing_model)
            session.flush()
        """
        # Convert Permission enum to string list
        permissions_str = [p.value for p in entity.permissions]

        if existing_model:
            # Update existing model (for UPDATE operations)
            existing_model.name = entity.name
            existing_model.description = entity.description
            existing_model.permissions = permissions_str
            existing_model.updated_at = entity.updated_at if entity.updated_at else existing_model.updated_at
            return existing_model
        else:
            # Create new model (for INSERT operations)
            return RoleModel(
                id=entity.id,
                name=entity.name,
                description=entity.description,
                permissions=permissions_str,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
