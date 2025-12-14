"""
Transaction management API routes.

This module provides:
- POST /api/v1/accounts/{account_id}/transactions - Create transaction
- GET /api/v1/accounts/{account_id}/transactions - List/search transactions
- GET /api/v1/transactions/{transaction_id} - Get transaction by ID
- PUT /api/v1/transactions/{transaction_id} - Update transaction
- DELETE /api/v1/transactions/{transaction_id} - Delete transaction
- POST /api/v1/transactions/{transaction_id}/split - Split transaction
- POST /api/v1/transactions/{transaction_id}/join - Join split
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Path, Request, status

from src.api.dependencies import CurrentUser, TransactionServiceDep
from src.schemas.common import PaginatedResponse, PaginationParams
from src.schemas.transaction import (
    TransactionCreate,
    TransactionFilterParams,
    TransactionResponse,
    TransactionSplitRequest,
    TransactionUpdate,
)
from src.services.transaction_service import UNSET

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Transactions"])


@router.post(
    "/accounts/{account_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transaction",
    description="""
    Create a new transaction for an account.

    Requires EDITOR or OWNER permission on the account.
    Currency must match the account currency.
    Automatically updates account balance.

    **Permission:** EDITOR or OWNER
    **Audit:** Creates audit log entry with transaction details
    """,
    responses={
        201: {"description": "Transaction created successfully"},
        400: {"description": "Currency mismatch or validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Account not found"},
        422: {"description": "Validation error"},
    },
)
async def create_transaction(
    request: Request,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    account_id: uuid.UUID = Path(description="Account UUID"),
    transaction_data: TransactionCreate = ...,
) -> TransactionResponse:
    """
    Create new transaction for an account.

    Request body:
        - transaction_date: Date when transaction occurred
        - amount: Transaction amount (positive or negative, non-zero)
        - currency: ISO 4217 code (must match account currency)
        - description: Transaction description (1-500 chars)
        - transaction_type: Type (debit, credit, transfer, fee, interest, other)
        - merchant: Optional merchant name (1-100 chars)
        - value_date: Optional value date
        - user_notes: Optional notes (max 1000 chars)

    Returns:
        TransactionResponse with created transaction details

    Requires:
        - Valid access token
        - EDITOR or OWNER permission on account
    """
    transaction = await transaction_service.create_transaction(
        account_id=account_id,
        transaction_date=transaction_data.transaction_date,
        amount=transaction_data.amount,
        currency=transaction_data.currency,
        description=transaction_data.description,
        transaction_type=transaction_data.transaction_type,
        merchant=transaction_data.merchant,
        card_id=transaction_data.card_id,
        value_date=transaction_data.value_date,
        user_notes=transaction_data.user_notes,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return TransactionResponse.model_validate(transaction)


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List and search transactions",
    description="""
    List transactions for an account with advanced search and filtering.

    Supports:
    - Date range filtering
    - Amount range filtering
    - Fuzzy text search (handles typos)
    - Transaction type filtering
    - Multiple sort options
    - Pagination

    **Permission:** VIEWER or higher
    """,
    responses={
        200: {"description": "List of transactions"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Account not found"},
    },
)
async def list_transactions(
    request: Request,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    account_id: uuid.UUID = Path(description="Account UUID"),
    pagination: PaginationParams = Depends(),
    filters: TransactionFilterParams = Depends(),
) -> PaginatedResponse[TransactionResponse]:
    """
    List and search transactions for an account.

    Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - date_from: Filter from this date (inclusive)
        - date_to: Filter to this date (inclusive)
        - amount_min: Minimum amount (inclusive)
        - amount_max: Maximum amount (inclusive)
        - description: Fuzzy search on description (handles typos)
        - merchant: Fuzzy search on merchant (handles typos)
        - transaction_type: Filter by type
        - card_id: Filter by card UUID
        - card_type: Filter by card type (credit_card or debit_card)
        - sort_by: Sort field (transaction_date, amount, description, created_at)
        - sort_order: Sort order (asc or desc)

    Returns:
        PaginatedResponse with transactions and pagination metadata

    Requires:
        - Valid access token
        - VIEWER or higher permission on account
    """
    return await transaction_service.search_transactions_paginated(
        account_id=account_id,
        current_user=current_user,
        pagination=pagination,
        filters=filters,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction by ID",
    description="""
    Get transaction details by ID.

    Requires VIEWER or higher permission on the account.

    **Permission:** VIEWER or higher
    """,
    responses={
        200: {"description": "Transaction details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Transaction not found"},
    },
)
async def get_transaction(
    request: Request,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
) -> TransactionResponse:
    """
    Get transaction details by ID.

    Returns:
        TransactionResponse with all transaction details

    Requires:
        - Valid access token
        - VIEWER or higher permission on account
    """
    transaction = await transaction_service.get_transaction(
        transaction_id=transaction_id,
        current_user=current_user,
    )

    return TransactionResponse.model_validate(transaction)


@router.put(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update transaction",
    description="""
    Update transaction fields.

    Only the creator, account owner, or admin can update a transaction.
    All fields are optional (partial update).
    Currency and account_id cannot be changed.

    **Permission:** Creator, OWNER, or Admin
    **Audit:** Logs old and new values
    """,
    responses={
        200: {"description": "Transaction updated successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Transaction not found"},
        422: {"description": "Validation error"},
    },
)
async def update_transaction(
    request: Request,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
    transaction_data: TransactionUpdate = ...,
) -> TransactionResponse:
    """
    Update transaction fields.

    Request body (all fields optional):
        - transaction_date: New date
        - amount: New amount (non-zero)
        - description: New description
        - merchant: New merchant
        - card_id: New card (or null to clear)
        - transaction_type: New type
        - user_notes: New notes
        - value_date: New value date

    Returns:
        TransactionResponse with updated transaction

    Requires:
        - Valid access token
        - Creator, OWNER permission, or Admin role
    """
    # Check if card_id was in the request body to distinguish
    # "not provided" (UNSET) from "explicitly null" (None)
    request_body = await request.json()
    card_id_param = transaction_data.card_id if "card_id" in request_body else UNSET

    transaction = await transaction_service.update_transaction(
        transaction_id=transaction_id,
        current_user=current_user,
        transaction_date=transaction_data.transaction_date,
        amount=transaction_data.amount,
        description=transaction_data.description,
        merchant=transaction_data.merchant,
        card_id=card_id_param,
        transaction_type=transaction_data.transaction_type,
        user_notes=transaction_data.user_notes,
        value_date=transaction_data.value_date,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return TransactionResponse.model_validate(transaction)


@router.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete transaction",
    description="""
    Soft delete a transaction.

    Only the account OWNER can delete transactions.
    Deleting a parent transaction also deletes all children.
    Balance is automatically updated.

    **Permission:** OWNER
    **Audit:** Logs deletion with old values
    """,
    responses={
        204: {"description": "Transaction deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions (OWNER required)"},
        404: {"description": "Transaction not found"},
    },
)
async def delete_transaction(
    request: Request,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
) -> None:
    """
    Delete transaction (soft delete).

    Requires:
        - Valid access token
        - OWNER permission on account
    """
    await transaction_service.delete_transaction(
        transaction_id=transaction_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/transactions/{transaction_id}/split",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Split transaction",
    description="""
    Split a transaction into multiple child transactions.

    Validation:
    - Sum of split amounts must equal parent amount exactly
    - At least 2 splits required
    - Parent cannot already be a child

    **Permission:** EDITOR or higher
    **Audit:** Logs split with details
    """,
    responses={
        200: {"description": "Transaction split successfully"},
        400: {"description": "Validation error (amounts don't sum, etc.)"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Transaction not found"},
        422: {"description": "Validation error"},
    },
)
async def split_transaction(
    request: Request,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    transaction_id: uuid.UUID = Path(description="Transaction UUID to split"),
    split_data: TransactionSplitRequest = ...,
) -> dict:
    """
    Split transaction into multiple parts.

    Request body:
        - splits: List of split items (min 2)
            - amount: Split amount (must sum to parent)
            - description: Split description
            - merchant: Optional merchant for this split
            - user_notes: Optional notes for this split

    Returns:
        Dictionary with parent and children details

    Requires:
        - Valid access token
        - EDITOR or higher permission on account
    """
    parent, children = await transaction_service.split_transaction(
        transaction_id=transaction_id,
        splits=[item.model_dump() for item in split_data.splits],
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "parent": TransactionResponse.model_validate(parent).model_dump(),
        "children": [
            TransactionResponse.model_validate(child).model_dump() for child in children
        ],
    }


@router.post(
    "/transactions/{transaction_id}/join",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Join split transaction",
    description="""
    Reverse a split by deleting all child transactions.

    The parent transaction remains as a single transaction.

    **Permission:** EDITOR or higher
    **Audit:** Logs join with child details
    """,
    responses={
        200: {"description": "Split joined successfully"},
        400: {"description": "Transaction has no splits to join"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Transaction not found"},
    },
)
async def join_split_transaction(
    request: Request,
    current_user: CurrentUser,
    transaction_service: TransactionServiceDep,
    transaction_id: uuid.UUID = Path(description="Parent transaction UUID"),
) -> TransactionResponse:
    """
    Join split transactions back to parent.

    Returns:
        TransactionResponse with parent transaction

    Requires:
        - Valid access token
        - EDITOR or higher permission on account
    """
    parent = await transaction_service.join_split_transaction(
        transaction_id=transaction_id,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return TransactionResponse.model_validate(parent)
