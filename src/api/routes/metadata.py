"""
Metadata API endpoints.

This module provides:
- Account types metadata (for dropdowns)
- Currency metadata (for dropdowns)
- Transaction types metadata (for dropdowns)

These endpoints serve as the authoritative source for business data,
ensuring frontend and backend stay in sync.
"""

import logging

from fastapi import APIRouter

from src.models.enums import AccountType, TransactionType
from src.schemas.metadata import (
    AccountTypeItem,
    AccountTypesResponse,
    CurrenciesResponse,
    TransactionTypeItem,
    TransactionTypesResponse,
)
from src.services.currency_service import get_currency_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.get(
    "/account-types",
    response_model=AccountTypesResponse,
    summary="Get available account types",
    description="Returns list of supported account types for dropdowns and filters.",
)
async def get_account_types() -> AccountTypesResponse:
    """
    Get all available account types.

    Returns:
        AccountTypesResponse with list of account type objects

    Example Response:
        {
            "account_types": [
                {"key": "checking", "label": "Checking"},
                {"key": "savings", "label": "Savings"},
                {"key": "investment", "label": "Investment"},
                {"key": "other", "label": "Other"}
            ]
        }
    """
    logger.debug("Fetching account types metadata")
    account_types = [AccountTypeItem(**item) for item in AccountType.to_dict_list()]
    return AccountTypesResponse(account_types=account_types)


@router.get(
    "/currencies",
    response_model=CurrenciesResponse,
    summary="Get supported currencies",
    description="Returns list of supported currencies with ISO 4217 codes and symbols.",
)
async def get_currencies() -> CurrenciesResponse:
    """
    Get all supported currencies.

    Returns:
        CurrenciesResponse with list of currency objects (code, symbol, name)

    Example Response:
        {
            "currencies": [
                {"code": "USD", "symbol": "$", "name": "US Dollar"},
                {"code": "EUR", "symbol": "€", "name": "Euro"},
                ...
            ]
        }
    """
    logger.debug("Fetching currencies metadata")
    currency_service = get_currency_service()
    currencies = currency_service.get_all()
    return CurrenciesResponse(currencies=currencies)


@router.get(
    "/transaction-types",
    response_model=TransactionTypesResponse,
    summary="Get available transaction types",
    description="Returns list of supported transaction types for filtering and creation.",
)
async def get_transaction_types() -> TransactionTypesResponse:
    """
    Get all available transaction types.

    Returns:
        TransactionTypesResponse with list of transaction type objects

    Example Response:
        {
            "transaction_types": [
                {"key": "income", "label": "Income"},
                {"key": "expense", "label": "Expense"},
                {"key": "transfer", "label": "Transfer"}
            ]
        }
    """
    logger.debug("Fetching transaction types metadata")
    transaction_types = [
        TransactionTypeItem(**item) for item in TransactionType.to_dict_list()
    ]
    return TransactionTypesResponse(transaction_types=transaction_types)
