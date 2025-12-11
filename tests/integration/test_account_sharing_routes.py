"""
Integration tests for Account Sharing API routes.

Tests cover:
- POST /api/v1/accounts/{account_id}/shares - Create share
- GET /api/v1/accounts/{account_id}/shares - List shares
- PUT /api/v1/accounts/{account_id}/shares/{share_id} - Update share permission
- DELETE /api/v1/accounts/{account_id}/shares/{share_id} - Revoke share

Test scenarios:
- Happy paths (successful operations)
- Permission enforcement (owner vs editor vs viewer)
- Error cases (invalid data, unauthorized access)
- Edge cases (self-share, duplicate shares, etc.)
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.account import Account, AccountShare
from src.models.enums import PermissionLevel
from src.models.user import User


# ============================================================================
# Fixtures
# ============================================================================
@pytest_asyncio.fixture
async def second_user(test_engine) -> User:
    """Create a second test user for sharing tests."""
    from src.core.security import hash_password

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        user = User(
            email="user2@example.com",
            username="user2",
            password_hash=hash_password("User2Pass123!"),
            is_admin=False,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user


@pytest_asyncio.fixture
async def third_user(test_engine) -> User:
    """Create a third test user for multi-user sharing tests."""
    from src.core.security import hash_password

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        user = User(
            email="user3@example.com",
            username="user3",
            password_hash=hash_password("User3Pass123!"),
            is_admin=False,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user


@pytest_asyncio.fixture
async def second_user_token(async_client: AsyncClient, second_user: User) -> dict:
    """Get authentication tokens for second user."""
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "user2@example.com",
            "password": "User2Pass123!",
        },
    )

    assert response.status_code == 200
    return response.json()


@pytest_asyncio.fixture
async def third_user_token(async_client: AsyncClient, third_user: User) -> dict:
    """Get authentication tokens for third user."""
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "user3@example.com",
            "password": "User3Pass123!",
        },
    )

    assert response.status_code == 200
    return response.json()


@pytest_asyncio.fixture
def second_user_headers(second_user_token: dict) -> dict:
    """Get authorization headers for second user."""
    return {"Authorization": f"Bearer {second_user_token['access_token']}"}


@pytest_asyncio.fixture
def third_user_headers(third_user_token: dict) -> dict:
    """Get authorization headers for third user."""
    return {"Authorization": f"Bearer {third_user_token['access_token']}"}


@pytest_asyncio.fixture
async def shared_account_viewer(
    test_engine, test_user: User, second_user: User, test_account: Account
) -> AccountShare:
    """Create a share with VIEWER permission for testing."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        share = AccountShare(
            account_id=test_account.id,
            user_id=second_user.id,
            permission_level=PermissionLevel.viewer,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        session.add(share)
        await session.commit()
        await session.refresh(share)

        return share


@pytest_asyncio.fixture
async def shared_account_editor(
    test_engine, test_user: User, second_user: User, test_account: Account
) -> AccountShare:
    """Create a share with EDITOR permission for testing."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        share = AccountShare(
            account_id=test_account.id,
            user_id=second_user.id,
            permission_level=PermissionLevel.editor,
            created_by=test_user.id,
            updated_by=test_user.id,
        )

        session.add(share)
        await session.commit()
        await session.refresh(share)

        return share


# ============================================================================
# Create Share Tests (POST /accounts/{account_id}/shares)
# ============================================================================
@pytest.mark.asyncio
async def test_create_share_viewer_success(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Owner successfully shares account with VIEWER permission."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={
            "user_id": str(second_user.id),
            "permission_level": "viewer",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["account_id"] == str(test_account.id)
    assert data["user_id"] == str(second_user.id)
    assert data["permission_level"] == "viewer"
    assert data["user"]["email"] == "user2@example.com"
    assert data["user"]["username"] == "user2"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_share_editor_success(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Owner successfully shares account with EDITOR permission."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={
            "user_id": str(second_user.id),
            "permission_level": "editor",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["account_id"] == str(test_account.id)
    assert data["user_id"] == str(second_user.id)
    assert data["permission_level"] == "editor"
    assert data["user"]["email"] == "user2@example.com"


@pytest.mark.asyncio
async def test_create_share_cannot_grant_owner_permission(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Cannot grant OWNER permission through share endpoint."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={
            "user_id": str(second_user.id),
            "permission_level": "owner",
        },
        headers=auth_headers,
    )

    # Should fail with validation error or business logic error
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_share_non_owner_cannot_share(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    third_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    second_user_headers: dict,
):
    """Test: Non-owner (editor) cannot share account."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={
            "user_id": str(third_user.id),
            "permission_level": "viewer",
        },
        headers=second_user_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_share_cannot_share_with_self(
    async_client: AsyncClient,
    test_user: User,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Cannot share account with yourself."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={
            "user_id": str(test_user.id),
            "permission_level": "viewer",
        },
        headers=auth_headers,
    )

    assert response.status_code in [400, 422]  # Business validation error


@pytest.mark.asyncio
async def test_create_share_nonexistent_account(
    async_client: AsyncClient,
    second_user: User,
    auth_headers: dict,
):
    """Test: Cannot share non-existent account."""
    fake_account_id = uuid.uuid4()

    response = await async_client.post(
        f"/api/v1/accounts/{fake_account_id}/shares",
        json={
            "user_id": str(second_user.id),
            "permission_level": "viewer",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_share_nonexistent_user(
    async_client: AsyncClient,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Cannot share with non-existent user."""
    fake_user_id = uuid.uuid4()

    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={
            "user_id": str(fake_user_id),
            "permission_level": "viewer",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_share_duplicate_share(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_viewer: AccountShare,
    auth_headers: dict,
):
    """Test: Cannot create duplicate share for same user."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={
            "user_id": str(second_user.id),
            "permission_level": "viewer",
        },
        headers=auth_headers,
    )

    assert response.status_code in [400, 409]  # Conflict or bad request


# ============================================================================
# List Shares Tests (GET /accounts/{account_id}/shares)
# ============================================================================
@pytest.mark.asyncio
async def test_list_shares_owner_sees_all(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    third_user: User,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Owner sees all explicit shares for the account."""
    # Create two shares
    await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={"user_id": str(second_user.id), "permission_level": "viewer"},
        headers=auth_headers,
    )
    await async_client.post(
        f"/api/v1/accounts/{test_account.id}/shares",
        json={"user_id": str(third_user.id), "permission_level": "editor"},
        headers=auth_headers,
    )

    # Owner lists shares
    response = await async_client.get(
        f"/api/v1/accounts/{test_account.id}/shares",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should see 2 explicit shares (ownership is implicit, not in share list)
    assert len(data) == 2

    user_ids = [share["user_id"] for share in data]
    assert str(second_user.id) in user_ids
    assert str(third_user.id) in user_ids


@pytest.mark.asyncio
async def test_list_shares_editor_can_view(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    second_user_headers: dict,
):
    """Test: Editor can view shares."""
    response = await async_client.get(
        f"/api/v1/accounts/{test_account.id}/shares",
        headers=second_user_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Editor should see at least their own share
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_shares_viewer_can_view(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_viewer: AccountShare,
    second_user_headers: dict,
):
    """Test: Viewer can view shares."""
    response = await async_client.get(
        f"/api/v1/accounts/{test_account.id}/shares",
        headers=second_user_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Viewer should see at least their own share
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_shares_non_member_cannot_view(
    async_client: AsyncClient,
    test_account: Account,
    second_user_headers: dict,
):
    """Test: Non-member cannot list shares."""
    response = await async_client.get(
        f"/api/v1/accounts/{test_account.id}/shares",
        headers=second_user_headers,
    )

    assert response.status_code in [403, 404]  # Forbidden or not found


@pytest.mark.asyncio
async def test_list_shares_empty_for_unshared_account(
    async_client: AsyncClient,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Returns empty list when account not shared with others."""
    response = await async_client.get(
        f"/api/v1/accounts/{test_account.id}/shares",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should see empty list (ownership is implicit, not in AccountShare table)
    assert len(data) == 0


# ============================================================================
# Update Share Tests (PUT /accounts/{account_id}/shares/{share_id})
# ============================================================================
@pytest.mark.asyncio
async def test_update_share_upgrade_viewer_to_editor(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_viewer: AccountShare,
    auth_headers: dict,
):
    """Test: Owner upgrades VIEWER to EDITOR."""
    response = await async_client.put(
        f"/api/v1/accounts/{test_account.id}/shares/{shared_account_viewer.id}",
        json={"permission_level": "editor"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(shared_account_viewer.id)
    assert data["permission_level"] == "editor"


@pytest.mark.asyncio
async def test_update_share_downgrade_editor_to_viewer(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    auth_headers: dict,
):
    """Test: Owner downgrades EDITOR to VIEWER."""
    response = await async_client.put(
        f"/api/v1/accounts/{test_account.id}/shares/{shared_account_editor.id}",
        json={"permission_level": "viewer"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(shared_account_editor.id)
    assert data["permission_level"] == "viewer"


@pytest.mark.asyncio
async def test_update_share_cannot_grant_owner_permission(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    auth_headers: dict,
):
    """Test: Cannot upgrade user to OWNER via update."""
    response = await async_client.put(
        f"/api/v1/accounts/{test_account.id}/shares/{shared_account_editor.id}",
        json={"permission_level": "owner"},
        headers=auth_headers,
    )

    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_update_share_non_owner_cannot_update(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    third_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    second_user_headers: dict,
    test_engine,
):
    """Test: Non-owner (editor) cannot update permissions."""
    # Create a third user share to try to modify
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        third_share = AccountShare(
            account_id=test_account.id,
            user_id=third_user.id,
            permission_level=PermissionLevel.viewer,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        session.add(third_share)
        await session.commit()
        await session.refresh(third_share)

        share_id = third_share.id

    # Second user (editor) tries to update third user's permission
    response = await async_client.put(
        f"/api/v1/accounts/{test_account.id}/shares/{share_id}",
        json={"permission_level": "editor"},
        headers=second_user_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_share_nonexistent_share(
    async_client: AsyncClient,
    test_account: Account,
    auth_headers: dict,
):
    """Test: Cannot update non-existent share."""
    fake_share_id = uuid.uuid4()

    response = await async_client.put(
        f"/api/v1/accounts/{test_account.id}/shares/{fake_share_id}",
        json={"permission_level": "editor"},
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_share_cannot_modify_owner_share(
    async_client: AsyncClient,
    test_user: User,
    test_account: Account,
    auth_headers: dict,
    test_engine,
):
    """Test: Cannot modify non-existent implicit owner share."""
    # Ownership is implicit - there is no AccountShare entry for the owner
    # Try to update a non-existent share (should fail with 404)
    fake_share_id = uuid.uuid4()

    response = await async_client.put(
        f"/api/v1/accounts/{test_account.id}/shares/{fake_share_id}",
        json={"permission_level": "viewer"},
        headers=auth_headers,
    )

    assert response.status_code == 404  # Share not found


# ============================================================================
# Delete/Revoke Share Tests (DELETE /accounts/{account_id}/shares/{share_id})
# ============================================================================
@pytest.mark.asyncio
async def test_revoke_share_viewer_success(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_viewer: AccountShare,
    auth_headers: dict,
):
    """Test: Owner successfully revokes viewer access."""
    response = await async_client.delete(
        f"/api/v1/accounts/{test_account.id}/shares/{shared_account_viewer.id}",
        headers=auth_headers,
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_revoke_share_editor_success(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    auth_headers: dict,
):
    """Test: Owner successfully revokes editor access."""
    response = await async_client.delete(
        f"/api/v1/accounts/{test_account.id}/shares/{shared_account_editor.id}",
        headers=auth_headers,
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_revoke_share_non_owner_cannot_revoke(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    third_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    second_user_headers: dict,
    test_engine,
):
    """Test: Non-owner (editor) cannot revoke access."""
    # Create a third user share to try to revoke
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        third_share = AccountShare(
            account_id=test_account.id,
            user_id=third_user.id,
            permission_level=PermissionLevel.viewer,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        session.add(third_share)
        await session.commit()
        await session.refresh(third_share)

        share_id = third_share.id

    # Second user (editor) tries to revoke third user's access
    response = await async_client.delete(
        f"/api/v1/accounts/{test_account.id}/shares/{share_id}",
        headers=second_user_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_revoke_share_cannot_revoke_owner_share(
    async_client: AsyncClient,
    test_user: User,
    test_account: Account,
    auth_headers: dict,
    test_engine,
):
    """Test: Cannot revoke non-existent implicit owner share."""
    # Ownership is implicit - there is no AccountShare entry to revoke
    # Try to delete a non-existent share (should fail with 404)
    fake_share_id = uuid.uuid4()

    response = await async_client.delete(
        f"/api/v1/accounts/{test_account.id}/shares/{fake_share_id}",
        headers=auth_headers,
    )

    assert response.status_code in [404, 400, 422]  # Not found or validation error


@pytest.mark.asyncio
async def test_revoke_share_user_loses_access_immediately(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_viewer: AccountShare,
    auth_headers: dict,
    second_user_headers: dict,
):
    """Test: Revoked user loses access immediately."""
    # Revoke access
    response = await async_client.delete(
        f"/api/v1/accounts/{test_account.id}/shares/{shared_account_viewer.id}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Second user tries to access account
    response = await async_client.get(
        f"/api/v1/accounts/{test_account.id}",
        headers=second_user_headers,
    )

    # Should be forbidden now
    assert response.status_code in [403, 404]


# ============================================================================
# Permission Enforcement Tests
# ============================================================================
@pytest.mark.asyncio
async def test_shared_viewer_cannot_create_transaction(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_viewer: AccountShare,
    second_user_headers: dict,
):
    """Test: Shared viewer cannot create transactions."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        json={
            "amount": "100.00",
            "transaction_type": "expense",
            "description": "Test transaction",
            "currency": "USD",
            "transaction_date": "2025-11-10",
        },
        headers=second_user_headers,
    )

    assert response.status_code in [403, 422]  # Forbidden or validation error


@pytest.mark.asyncio
async def test_shared_editor_cannot_delete_account(
    async_client: AsyncClient,
    test_user: User,
    second_user: User,
    test_account: Account,
    shared_account_editor: AccountShare,
    second_user_headers: dict,
):
    """Test: Shared editor cannot delete account."""
    response = await async_client.delete(
        f"/api/v1/accounts/{test_account.id}",
        headers=second_user_headers,
    )

    assert response.status_code in [403, 404]
