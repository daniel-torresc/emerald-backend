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
- POST /api/v1/transactions/{transaction_id}/tags - Add tag
- DELETE /api/v1/transactions/{transaction_id}/tags/{tag} - Remove tag
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Path, Query, Request, status

from src.api.dependencies import (
    get_transaction_service,
    require_active_user,
)
from src.models.user import User
from src.schemas.transaction import (
    SplitItem,
    TagRequest,
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionSearchParams,
    TransactionSplitRequest,
    TransactionUpdate,
)
from src.services.transaction_service import TransactionService

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
    account_id: uuid.UUID = Path(description="Account UUID"),
    transaction_data: TransactionCreate = ...,
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
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
        - tags: Optional list of tags

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
        value_date=transaction_data.value_date,
        user_notes=transaction_data.user_notes,
        tags=transaction_data.tags,
        current_user=current_user,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return TransactionResponse.model_validate(transaction)


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=TransactionListResponse,
    summary="List and search transactions",
    description="""
    List transactions for an account with advanced search and filtering.

    Supports:
    - Date range filtering
    - Amount range filtering
    - Fuzzy text search (handles typos)
    - Tag filtering
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
    account_id: uuid.UUID = Path(description="Account UUID"),
    search_params: TransactionSearchParams = Depends(),
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionListResponse:
    """
    List and search transactions for an account.

    Query parameters:
        - date_from: Filter from this date (inclusive)
        - date_to: Filter to this date (inclusive)
        - amount_min: Minimum amount (inclusive)
        - amount_max: Maximum amount (inclusive)
        - description: Fuzzy search on description (handles typos)
        - merchant: Fuzzy search on merchant (handles typos)
        - tags: Filter by tags (ANY match)
        - transaction_type: Filter by type
        - sort_by: Sort field (transaction_date, amount, description, created_at)
        - sort_order: Sort order (asc or desc)
        - skip: Number of records to skip (pagination)
        - limit: Maximum records to return (max 100)

    Returns:
        TransactionListResponse with items and total count

    Requires:
        - Valid access token
        - VIEWER or higher permission on account
    """
    transactions, total = await transaction_service.search_transactions(
        account_id=account_id,
        current_user=current_user,
        date_from=search_params.date_from,
        date_to=search_params.date_to,
        amount_min=search_params.amount_min,
        amount_max=search_params.amount_max,
        description=search_params.description,
        merchant=search_params.merchant,
        tags=search_params.tags,
        transaction_type=search_params.transaction_type,
        sort_by=search_params.sort_by,
        sort_order=search_params.sort_order,
        skip=search_params.skip,
        limit=search_params.limit,
    )

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        skip=search_params.skip,
        limit=search_params.limit,
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
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
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
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
    transaction_data: TransactionUpdate = ...,
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Update transaction fields.

    Request body (all fields optional):
        - transaction_date: New date
        - amount: New amount (non-zero)
        - description: New description
        - merchant: New merchant
        - transaction_type: New type
        - user_notes: New notes
        - value_date: New value date

    Returns:
        TransactionResponse with updated transaction

    Requires:
        - Valid access token
        - Creator, OWNER permission, or Admin role
    """
    transaction = await transaction_service.update_transaction(
        transaction_id=transaction_id,
        current_user=current_user,
        transaction_date=transaction_data.transaction_date,
        amount=transaction_data.amount,
        description=transaction_data.description,
        merchant=transaction_data.merchant,
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
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
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
    transaction_id: uuid.UUID = Path(description="Transaction UUID to split"),
    split_data: TransactionSplitRequest = ...,
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
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
    transaction_id: uuid.UUID = Path(description="Parent transaction UUID"),
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
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


@router.post(
    "/transactions/{transaction_id}/tags",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Add tag to transaction",
    description="""
    Add a tag to a transaction.

    Tags are normalized (lowercased and trimmed).
    Duplicate tags are prevented by unique constraint.

    **Permission:** EDITOR or higher
    """,
    responses={
        200: {"description": "Tag added successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Transaction not found"},
        409: {"description": "Tag already exists"},
    },
)
async def add_tag(
    request: Request,
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
    tag_data: TagRequest = ...,
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Add tag to transaction.

    Request body:
        - tag: Tag text (1-50 chars, will be normalized)

    Returns:
        TransactionResponse with updated tags

    Requires:
        - Valid access token
        - EDITOR or higher permission on account
    """
    transaction = await transaction_service.add_tag(
        transaction_id=transaction_id,
        tag=tag_data.tag,
        current_user=current_user,
    )

    return TransactionResponse.model_validate(transaction)


@router.delete(
    "/transactions/{transaction_id}/tags/{tag}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tag from transaction",
    description="""
    Remove a tag from a transaction.

    Tags are normalized before lookup (lowercased and trimmed).

    **Permission:** EDITOR or higher
    """,
    responses={
        204: {"description": "Tag removed successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Transaction or tag not found"},
    },
)
async def remove_tag(
    request: Request,
    transaction_id: uuid.UUID = Path(description="Transaction UUID"),
    tag: str = Path(description="Tag to remove"),
    current_user: User = Depends(require_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> None:
    """
    Remove tag from transaction.

    Requires:
        - Valid access token
        - EDITOR or higher permission on account
    """
    await transaction_service.remove_tag(
        transaction_id=transaction_id,
        tag=tag,
        current_user=current_user,
    )
