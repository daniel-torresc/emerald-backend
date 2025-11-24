"""
Metadata API response schemas.

This module provides Pydantic schemas for metadata endpoints that serve
as the authoritative source for business data (account types, currencies,
transaction types).
"""

from pydantic import BaseModel, Field

from src.services.currency_service import Currency


class AccountTypeItem(BaseModel):
    """Single account type metadata item."""

    key: str = Field(description="Account type key", examples=["checking", "savings"])
    label: str = Field(description="Display label", examples=["Checking", "Savings"])


class AccountTypesResponse(BaseModel):
    """Response schema for GET /api/metadata/account-types"""

    account_types: list[AccountTypeItem] = Field(
        description="List of available account types"
    )


class CurrenciesResponse(BaseModel):
    """Response schema for GET /api/metadata/currencies"""

    currencies: list[Currency] = Field(description="List of supported currencies")


class TransactionTypeItem(BaseModel):
    """Single transaction type metadata item."""

    key: str = Field(description="Transaction type key", examples=["income", "expense"])
    label: str = Field(description="Display label", examples=["Income", "Expense"])


class TransactionTypesResponse(BaseModel):
    """Response schema for GET /api/metadata/transaction-types"""

    transaction_types: list[TransactionTypeItem] = Field(
        description="List of transaction types"
    )
