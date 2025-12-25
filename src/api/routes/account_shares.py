"""
Account sharing API routes.

This module provides endpoints for:
- POST /api/v1/accounts/{account_id}/shares - Share account with user
- GET /api/v1/accounts/{account_id}/shares - List account shares
- PUT /api/v1/accounts/{account_id}/shares/{share_id} - Update share permission
- DELETE /api/v1/accounts/{account_id}/shares/{share_id} - Revoke account access
"""

import uuid

from fastapi import APIRouter, Request, status

from api.dependencies import AccountServiceDep, CurrentUser
from schemas.account_share import (
    AccountShareCreate,
    AccountShareResponse,
    AccountShareUpdate,
)

router = APIRouter(prefix="/accounts", tags=["Account Shares"])


@router.post(
    "/{account_id}/shares",
    response_model=AccountShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Share account with user",
    description="""
    Share an account with another user, granting them specific permissions.

    **Permission Required:** OWNER

    **Permission Levels:**
    - `owner`: Full access (cannot be granted, only one owner per account)
    - `editor`: Read/write access (can view and update account)
    - `viewer`: Read-only access (can only view account)

    **Validation:**
    - Cannot share with yourself
    - Cannot share with non-existent users
    - Cannot grant owner permission
    - Cannot share if already shared with user

    **Audit:** Creates audit log entry
    """,
)
async def create_share(
    account_id: uuid.UUID,
    share_data: AccountShareCreate,
    request: Request,
    current_user: CurrentUser,
    account_service: AccountServiceDep,
) -> AccountShareResponse:
    """
    Share account with another user.

    Args:
        account_id: UUID of the account to share
        share_data: Share creation data (user_id and permission_level)
        request: HTTP request object (for audit logging)
        current_user: Authenticated user (must be owner)
        account_service: Account service dependency

    Returns:
        Created AccountShare with user details

    Raises:
        404: Account or target user not found
        403: User is not the account owner
        400: Invalid share data (self-share, owner permission, duplicate)
        422: Validation error
    """
    share = await account_service.share_account(
        current_user=current_user,
        account_id=account_id,
        data=share_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.state.request_id
        if hasattr(request.state, "request_id")
        else None,
    )

    return AccountShareResponse.model_validate(share)


@router.get(
    "/{account_id}/shares",
    response_model=list[AccountShareResponse],
    summary="List account shares",
    description="""
    List all shares for an account.

    **Permission Required:** VIEWER or higher

    **Filtering:**
    - Owner sees all shares for the account
    - Non-owners see only their own share entry

    This allows users to see their permission level without exposing
    who else has access to the account.
    """,
)
async def list_shares(
    account_id: uuid.UUID,
    current_user: CurrentUser,
    account_service: AccountServiceDep,
) -> list[AccountShareResponse]:
    """
    List all shares for an account.

    Owners see all shares, non-owners see only their own.

    Args:
        account_id: UUID of the account
        current_user: Authenticated user
        account_service: Account service dependency

    Returns:
        List of AccountShare objects with user details

    Raises:
        404: Account not found or user has no access
        403: User does not have permission to view account
    """
    shares = await account_service.list_shares(
        account_id=account_id,
        current_user=current_user,
    )

    return [AccountShareResponse.model_validate(share) for share in shares]


@router.put(
    "/{account_id}/shares/{share_id}",
    response_model=AccountShareResponse,
    summary="Update share permission",
    description="""
    Update the permission level for an account share.

    **Permission Required:** OWNER

    **Allowed Changes:**
    - Upgrade viewer to editor
    - Downgrade editor to viewer

    **Restrictions:**
    - Cannot grant owner permission
    - Cannot change your own owner permission

    **Audit:** Creates audit log entry with old and new permission levels
    """,
)
async def update_share(
    account_id: uuid.UUID,
    share_id: uuid.UUID,
    share_data: AccountShareUpdate,
    request: Request,
    current_user: CurrentUser,
    account_service: AccountServiceDep,
) -> AccountShareResponse:
    """
    Update permission level for an account share.

    Args:
        account_id: UUID of the account
        share_id: UUID of the share to update
        share_data: New permission level
        request: HTTP request object (for audit logging)
        current_user: Authenticated user (must be owner)
        account_service: Account service dependency

    Returns:
        Updated AccountShare with user details

    Raises:
        404: Account or share not found
        403: User is not the account owner
        400: Invalid permission change (owner grant, self-modification)
        422: Validation error
    """
    updated_share = await account_service.update_share(
        account_id=account_id,
        share_id=share_id,
        permission_level=share_data.permission_level,
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.state.request_id
        if hasattr(request.state, "request_id")
        else None,
    )

    return AccountShareResponse.model_validate(updated_share)


@router.delete(
    "/{account_id}/shares/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke account access",
    description="""
    Revoke a user's access to an account.

    **Permission Required:** OWNER

    **Behavior:**
    - Soft deletes the share (preserves audit trail)
    - User immediately loses access
    - Share history preserved in database

    **Restrictions:**
    - Cannot revoke your own owner permission

    **Audit:** Creates audit log entry
    """,
)
async def revoke_share(
    account_id: uuid.UUID,
    share_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    account_service: AccountServiceDep,
) -> None:
    """
    Revoke account access from a user.

    Args:
        account_id: UUID of the account
        share_id: UUID of the share to revoke
        request: HTTP request object (for audit logging)
        current_user: Authenticated user (must be owner)
        account_service: Account service dependency

    Returns:
        None (204 No Content)

    Raises:
        404: Account or share not found
        403: User is not the account owner
        400: Trying to revoke own owner permission
    """
    await account_service.revoke_share(
        account_id=account_id,
        share_id=share_id,
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.state.request_id
        if hasattr(request.state, "request_id")
        else None,
    )
