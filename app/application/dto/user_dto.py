"""User DTOs (Data Transfer Objects)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserProfileOutput(BaseModel):
    """Output DTO for user profile information."""

    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    username: str = Field(..., description="Username")
    full_name: str = Field(..., description="Full name")
    is_active: bool = Field(..., description="Whether user account is active")
    is_admin: bool = Field(..., description="Whether user has admin privileges")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = {"frozen": True, "from_attributes": True}

    @classmethod
    def from_entity(cls, user: "User") -> "UserProfileOutput":
        """
        Create DTO from User entity.

        Args:
            user: User domain entity

        Returns:
            UserProfileOutput DTO
        """
        return cls(
            id=user.id,
            email=user.email.value,
            username=user.username.value,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UpdateUserProfileInput(BaseModel):
    """Input DTO for updating user profile."""

    full_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Full name"
    )
    email: Optional[EmailStr] = Field(None, description="Email address")
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, description="Username"
    )

    model_config = {"frozen": True}


class UserListOutput(BaseModel):
    """Output DTO for paginated user list."""

    users: list[UserProfileOutput] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of users per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = {"frozen": True}


class DeleteUserInput(BaseModel):
    """Input DTO for user deletion."""

    user_id: UUID = Field(..., description="User's unique identifier")
    soft_delete: bool = Field(
        default=True, description="Whether to soft delete (True) or hard delete (False)"
    )

    model_config = {"frozen": True}


class UserDetailOutput(BaseModel):
    """Output DTO for detailed user information (admin only)."""

    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    username: str = Field(..., description="Username")
    full_name: str = Field(..., description="Full name")
    is_active: bool = Field(..., description="Whether user account is active")
    is_admin: bool = Field(..., description="Whether user has admin privileges")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    roles: list[str] = Field(default_factory=list, description="List of role names")

    model_config = {"frozen": True, "from_attributes": True}

    @classmethod
    def from_entity(cls, user: "User") -> "UserDetailOutput":
        """
        Create DTO from User entity.

        Args:
            user: User domain entity

        Returns:
            UserDetailOutput DTO
        """
        return cls(
            id=user.id,
            email=user.email.value,
            username=user.username.value,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
            roles=[role.name for role in user.roles],
        )


# Import for type hints
from app.domain.entities.user import User  # noqa: E402

UserProfileOutput.model_rebuild()
UserDetailOutput.model_rebuild()
