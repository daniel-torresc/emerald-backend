"""
Mapper between User domain entity and UserModel database model.

This mapper handles bidirectional conversion:
- to_entity(): Convert SQLAlchemy model → Domain entity
- to_model(): Convert Domain entity → SQLAlchemy model

The mapper lives in the Infrastructure layer and knows about both:
- Domain entities (app.domain.entities.user.User)
- Database models (app.infrastructure...models.user_model.UserModel)

This is the only place where entity ↔ model conversion happens.
"""

from typing import Optional

from app.domain.entities.role import Role
from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.password_hash import PasswordHash
from app.domain.value_objects.username import Username
from app.infrastructure.adapters.outbound.persistence.postgresql.models.user_model import (
    RoleModel,
    UserModel,
)


class UserMapper:
    """
    Mapper between User entity and UserModel.

    Handles conversion between:
    - Pure domain entity (User) with value objects
    - SQLAlchemy ORM model (UserModel) with primitives
    """

    @staticmethod
    def to_entity(model: UserModel) -> User:
        """
        Convert SQLAlchemy model to domain entity.

        Args:
            model: UserModel from database

        Returns:
            User domain entity

        Example:
            user_model = session.get(UserModel, user_id)
            user_entity = UserMapper.to_entity(user_model)
        """
        # Convert role models to role entities
        from app.infrastructure.adapters.outbound.persistence.postgresql.mappers.role_mapper import (
            RoleMapper,
        )

        roles = [RoleMapper.to_entity(role_model) for role_model in model.roles]

        return User(
            id=model.id,
            email=Email(model.email),
            username=Username(model.username),
            password_hash=PasswordHash(model.password_hash),
            full_name=model.full_name or "",  # Domain requires non-empty string
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            last_login_at=model.last_login_at,
            is_active=model.is_active,
            is_admin=model.is_admin,
            roles=roles,
        )

    @staticmethod
    def to_model(entity: User, existing_model: Optional[UserModel] = None) -> UserModel:
        """
        Convert domain entity to SQLAlchemy model.

        Args:
            entity: User domain entity
            existing_model: Optional existing model to update (for updates)

        Returns:
            UserModel for database persistence

        Example:
            # Create new model
            user_entity = User(...)
            user_model = UserMapper.to_model(user_entity)
            session.add(user_model)

            # Update existing model
            user_entity.full_name = "New Name"
            updated_model = UserMapper.to_model(user_entity, existing_model)
            session.flush()
        """
        if existing_model:
            # Update existing model (for UPDATE operations)
            existing_model.email = entity.email.value
            existing_model.username = entity.username.value
            existing_model.password_hash = entity.password_hash.value
            existing_model.full_name = entity.full_name
            existing_model.is_active = entity.is_active
            existing_model.is_admin = entity.is_admin
            existing_model.last_login_at = entity.last_login_at
            existing_model.updated_at = entity.updated_at
            existing_model.deleted_at = entity.deleted_at
            return existing_model
        else:
            # Create new model (for INSERT operations)
            return UserModel(
                id=entity.id,
                email=entity.email.value,
                username=entity.username.value,
                password_hash=entity.password_hash.value,
                full_name=entity.full_name,
                is_active=entity.is_active,
                is_admin=entity.is_admin,
                last_login_at=entity.last_login_at,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                deleted_at=entity.deleted_at,
                # Note: roles relationship will be managed separately
                # through the user_roles junction table
            )
