"""Account DTOs (Data Transfer Objects)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateAccountInput(BaseModel):
    """Input DTO for creating a new account."""

    name: str = Field(..., min_length=1, max_length=100, description="Account name")
    description: Optional[str] = Field(
        None, max_length=500, description="Account description"
    )

    model_config = {"frozen": True}


class UpdateAccountInput(BaseModel):
    """Input DTO for updating an account."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Account name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Account description"
    )
    is_active: Optional[bool] = Field(None, description="Whether account is active")

    model_config = {"frozen": True}


class AccountOutput(BaseModel):
    """Output DTO for account information."""

    id: UUID = Field(..., description="Account's unique identifier")
    user_id: UUID = Field(..., description="Owner's user ID")
    name: str = Field(..., description="Account name")
    description: Optional[str] = Field(None, description="Account description")
    balance: Decimal = Field(..., description="Current account balance")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    is_active: bool = Field(..., description="Whether account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = {"frozen": True, "from_attributes": True}

    @classmethod
    def from_entity(cls, account: "Account") -> "AccountOutput":
        """
        Create DTO from Account entity.

        Args:
            account: Account domain entity

        Returns:
            AccountOutput DTO
        """
        return cls(
            id=account.id,
            user_id=account.user_id,
            name=account.name,
            description=account.description,
            balance=account.balance.amount,
            currency=account.balance.currency.value,
            is_active=account.is_active,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )


class AccountListOutput(BaseModel):
    """Output DTO for paginated account list."""

    accounts: list[AccountOutput] = Field(..., description="List of accounts")
    total: int = Field(..., description="Total number of accounts")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of accounts per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = {"frozen": True}


class ShareAccountInput(BaseModel):
    """Input DTO for sharing an account."""

    account_id: UUID = Field(..., description="Account's unique identifier")
    shared_with_user_id: UUID = Field(
        ..., description="User ID to share the account with"
    )
    permission: str = Field(
        ..., description="Permission level (e.g., 'read', 'write')"
    )
    expires_at: Optional[datetime] = Field(
        None, description="When the share expires (None for no expiration)"
    )

    model_config = {"frozen": True}


class AccountShareOutput(BaseModel):
    """Output DTO for account share information."""

    id: UUID = Field(..., description="Share's unique identifier")
    account_id: UUID = Field(..., description="Account's unique identifier")
    shared_with_user_id: UUID = Field(..., description="User ID account is shared with")
    permission: str = Field(..., description="Permission level")
    created_at: datetime = Field(..., description="Share creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Share expiration timestamp")
    is_active: bool = Field(..., description="Whether share is currently active")

    model_config = {"frozen": True, "from_attributes": True}

    @classmethod
    def from_entity(cls, account_share: "AccountShare") -> "AccountShareOutput":
        """
        Create DTO from AccountShare entity.

        Args:
            account_share: AccountShare domain entity

        Returns:
            AccountShareOutput DTO
        """
        return cls(
            id=account_share.id,
            account_id=account_share.account_id,
            shared_with_user_id=account_share.shared_with_user_id,
            permission=account_share.permission.value,
            created_at=account_share.created_at,
            expires_at=account_share.expires_at,
            is_active=account_share.is_active(),
        )


class RevokeShareInput(BaseModel):
    """Input DTO for revoking an account share."""

    account_id: UUID = Field(..., description="Account's unique identifier")
    shared_with_user_id: UUID = Field(
        ..., description="User ID to revoke share from"
    )

    model_config = {"frozen": True}


# Import for type hints
from app.domain.entities.account import Account  # noqa: E402
from app.domain.entities.account_share import AccountShare  # noqa: E402

AccountOutput.model_rebuild()
AccountShareOutput.model_rebuild()
