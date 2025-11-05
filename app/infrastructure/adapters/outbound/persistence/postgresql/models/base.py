"""
Base model class for all database models.

This module provides the declarative base and common model configuration.
All SQLAlchemy models should inherit from Base.
"""

import uuid

from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention for constraints
# This ensures consistent naming across all database objects
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Base class for all database models.

    Provides:
    - UUID primary key (id column)
    - Naming convention for constraints
    - Common configuration

    Usage:
        class User(Base):
            __tablename__ = "users"
            username: Mapped[str] = mapped_column(String(50))
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Default primary key column (UUID)
    # All models will have this unless overridden
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Type annotation for repr
    __name__: str

    def __repr__(self) -> str:
        """
        String representation of model instance.

        Returns:
            String in format: ModelName(id=uuid)
        """
        return f"{self.__class__.__name__}(id={self.id})"
