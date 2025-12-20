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

from api.dependencies import CurrencyServiceDep
from schemas import CurrenciesResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.get(
    "/currencies",
    response_model=CurrenciesResponse,
    summary="Get supported currencies",
    description="Returns list of supported currencies with ISO 4217 codes and symbols.",
)
async def get_currencies(
    currency_service: CurrencyServiceDep,
) -> CurrenciesResponse:
    """
    Get all supported currencies.

    Args:
        currency_service: Injected CurrencyService instance

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
    currencies = currency_service.get_all()
    return CurrenciesResponse(currencies=currencies)
