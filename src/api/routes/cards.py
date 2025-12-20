"""
Card API routes.

This module provides RESTful API endpoints for card management:
- GET /api/v1/cards - List user's cards
- GET /api/v1/cards/{id} - Get card by ID
- POST /api/v1/cards - Create new card
- PATCH /api/v1/cards/{id} - Update card
- DELETE /api/v1/cards/{id} - Delete card
"""

import uuid

from fastapi import APIRouter, Depends, Request, status

from api.dependencies import CardServiceDep, CurrentUser
from schemas.card import (
    CardCreate,
    CardFilterParams,
    CardListItem,
    CardResponse,
    CardUpdate,
)
from schemas.common import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/cards", tags=["Cards"])


@router.get("", response_model=PaginatedResponse[CardListItem])
async def list_cards(
    current_user: CurrentUser,
    service: CardServiceDep,
    filters: CardFilterParams = Depends(),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[CardListItem]:
    """
    List all cards for the authenticated user.

    Returns cards linked to accounts owned by the current user.
    Supports filtering by card type and account, plus pagination.

    **Authorization**: Requires active user authentication.

    **Query Parameters**:
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20, max: 100)
    - `card_type`: Filter by credit_card or debit_card
    - `account_id`: Filter cards for specific account

    **Returns**: Paginated response with cards and metadata.

    **Example**:
    ```
    GET /api/v1/cards?page=1&page_size=20&card_type=credit_card
    ```
    """
    return await service.list_cards(
        current_user=current_user,
        pagination=pagination,
        filters=filters,
    )


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: uuid.UUID,
    current_user: CurrentUser,
    service: CardServiceDep,
) -> CardResponse:
    """
    Get a specific card by ID.

    **Authorization**: Requires active user authentication.
    User must own the account linked to the card.

    **Returns**: Complete card details including relationships.

    **Errors**:
    - `404 Not Found`: Card doesn't exist or doesn't belong to user

    **Example**:
    ```
    GET /api/v1/cards/550e8400-e29b-41d4-a716-446655440100
    ```
    """
    return await service.get_card(
        card_id=card_id,
        current_user=current_user,
    )


@router.post("", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    request: Request,
    data: CardCreate,
    current_user: CurrentUser,
    service: CardServiceDep,
) -> CardResponse:
    """
    Create a new card linked to an account.

    **Authorization**: Requires active user authentication.
    User must own the specified account.

    **Required Fields**:
    - `account_id`: UUID of account to link card to
    - `card_type`: Type of card (credit_card or debit_card)
    - `name`: Display name for the card

    **Optional Fields**:
    - `financial_institution_id`: Issuing institution
    - `last_four_digits`: Last 4 digits (exactly 4 numeric digits)
    - `card_network`: Payment network (Visa, Mastercard, etc.)
    - `expiry_month`: Expiration month (1-12)
    - `expiry_year`: Expiration year (2000-2100)
    - `credit_limit`: Credit limit (must be positive)
    - `notes`: Personal notes (max 500 chars)

    **Validation Rules**:
    - Account must belong to current user
    - Financial institution must exist and be active (if provided)
    - Both expiry_month and expiry_year must be provided together
    - Last four digits must be exactly 4 numeric digits
    - Credit limit must be positive

    **Returns**: Created card with generated ID and timestamps.

    **Errors**:
    - `400 Bad Request`: Validation error
    - `403 Forbidden`: Account doesn't belong to user
    - `404 Not Found`: Account or financial institution not found

    **Example**:
    ```json
    POST /api/v1/cards
    {
      "account_id": "550e8400-e29b-41d4-a716-446655440010",
      "card_type": "credit_card",
      "name": "Chase Sapphire Reserve",
      "last_four_digits": "4242",
      "card_network": "Visa",
      "expiry_month": 12,
      "expiry_year": 2027,
      "credit_limit": 25000.00,
      "financial_institution_id": "550e8400-e29b-41d4-a716-446655440001"
    }
    ```
    """
    return await service.create_card(
        data=data,
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: uuid.UUID,
    data: CardUpdate,
    request: Request,
    current_user: CurrentUser,
    service: CardServiceDep,
) -> CardResponse:
    """
    Update an existing card.

    **Authorization**: Requires active user authentication.
    User must own the account linked to the card.

    **Supported Updates**:
    All fields are optional (partial updates supported):
    - `name`: Display name
    - `last_four_digits`: Last 4 digits
    - `card_network`: Payment network
    - `expiry_month`: Expiration month (1-12)
    - `expiry_year`: Expiration year (2000-2100)
    - `credit_limit`: Credit limit (must be positive)
    - `financial_institution_id`: Issuing institution
    - `notes`: Personal notes

    **Immutable Fields**:
    - `account_id`: Cannot change card's account
    - `card_type`: Cannot change card type

    **Validation Rules**:
    - Financial institution must exist and be active (if provided)
    - Last four digits must be exactly 4 numeric digits
    - Credit limit must be positive
    - Expiry year must be 2000-2100

    **Returns**: Updated card with new updated_at timestamp.

    **Errors**:
    - `400 Bad Request`: Validation error
    - `403 Forbidden`: Card doesn't belong to user's account
    - `404 Not Found`: Card or financial institution not found

    **Example**:
    ```json
    PATCH /api/v1/cards/550e8400-e29b-41d4-a716-446655440100
    {
      "name": "Updated Card Name",
      "credit_limit": 30000.00,
      "notes": "Increased limit on 2025-12-09"
    }
    ```
    """
    return await service.update_card(
        card_id=card_id,
        data=data,
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    service: CardServiceDep,
) -> None:
    """
    Soft-delete a card.

    **Authorization**: Requires active user authentication.
    User must own the account linked to the card.

    **Behavior**:
    - Performs soft delete (sets deleted_at timestamp)
    - Card remains in database for audit/history
    - Transactions referencing this card will have card_id set to NULL
    - Deleted cards excluded from normal queries

    **Returns**: 204 No Content on success.

    **Errors**:
    - `403 Forbidden`: Card doesn't belong to user's account
    - `404 Not Found`: Card not found

    **Example**:
    ```
    DELETE /api/v1/cards/550e8400-e29b-41d4-a716-446655440100
    ```
    """
    await service.delete_card(
        card_id=card_id,
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
