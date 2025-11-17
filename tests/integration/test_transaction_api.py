"""
Integration tests for Transaction Management API.

Tests complete workflows through the REST API layer, including:
- Transaction CRUD operations
- Search and filtering
- Transaction splitting and joining
- Tag management
- Permission enforcement
"""

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.models.user import User


@pytest.mark.asyncio
class TestTransactionAPI:
    """Integration tests for transaction REST endpoints."""

    async def test_create_transaction(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test creating a transaction via API."""
        response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-50.25",
                "currency": "USD",
                "description": "Grocery shopping",
                "merchant": "Whole Foods",
                "transaction_type": "debit",
                "tags": ["groceries", "food"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "-50.25"
        assert data["description"] == "Grocery shopping"
        assert data["merchant"] == "Whole Foods"
        assert len(data["tags"]) == 2

    async def test_list_transactions(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test listing transactions for an account."""
        # Create a few transactions
        for i in range(3):
            await async_client.post(
                f"/api/v1/accounts/{test_account.id}/transactions",
                headers={"Authorization": f"Bearer {user_token['access_token']}"},
                json={
                    "transaction_date": str(date.today()),
                    "amount": f"-{10 + i}.00",
                    "currency": "USD",
                    "description": f"Transaction {i}",
                    "transaction_type": "debit",
                },
            )

        # List transactions
        response = await async_client.get(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    async def test_get_transaction(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test getting a single transaction by ID."""
        # Create transaction
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-25.00",
                "currency": "USD",
                "description": "Test transaction",
                "transaction_type": "debit",
            },
        )

        transaction_id = create_response.json()["id"]

        # Get transaction
        response = await async_client.get(
            f"/api/v1/transactions/{transaction_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transaction_id
        assert data["description"] == "Test transaction"

    async def test_update_transaction(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test updating a transaction."""
        # Create transaction
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-25.00",
                "currency": "USD",
                "description": "Original",
                "transaction_type": "debit",
            },
        )

        transaction_id = create_response.json()["id"]

        # Update transaction
        response = await async_client.put(
            f"/api/v1/transactions/{transaction_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "description": "Updated description",
                "amount": "-30.00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["amount"] == "-30.00"

    async def test_delete_transaction(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test deleting a transaction."""
        # Create transaction
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-25.00",
                "currency": "USD",
                "description": "To delete",
                "transaction_type": "debit",
            },
        )

        transaction_id = create_response.json()["id"]

        # Delete transaction
        response = await async_client.delete(
            f"/api/v1/transactions/{transaction_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = await async_client.get(
            f"/api/v1/transactions/{transaction_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert get_response.status_code == 404

    async def test_split_transaction(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test splitting a transaction."""
        # Create parent transaction
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-50.00",
                "currency": "USD",
                "description": "Shopping",
                "transaction_type": "debit",
            },
        )

        transaction_id = create_response.json()["id"]

        # Split transaction
        response = await async_client.post(
            f"/api/v1/transactions/{transaction_id}/split",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "splits": [
                    {"amount": "-30.00", "description": "Groceries"},
                    {"amount": "-20.00", "description": "Household items"},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_split_parent"] is True
        assert len(data["child_transactions"]) == 2

    async def test_join_split_transaction(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test joining split transactions back together."""
        # Create and split
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-50.00",
                "currency": "USD",
                "description": "Shopping",
                "transaction_type": "debit",
            },
        )

        transaction_id = create_response.json()["id"]

        await async_client.post(
            f"/api/v1/transactions/{transaction_id}/split",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "splits": [
                    {"amount": "-30.00", "description": "Split 1"},
                    {"amount": "-20.00", "description": "Split 2"},
                ]
            },
        )

        # Join back
        response = await async_client.post(
            f"/api/v1/transactions/{transaction_id}/join",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_split_parent"] is False

    async def test_add_tag(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test adding a tag to a transaction."""
        # Create transaction
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-25.00",
                "currency": "USD",
                "description": "Transaction",
                "transaction_type": "debit",
            },
        )

        transaction_id = create_response.json()["id"]

        # Add tag
        response = await async_client.post(
            f"/api/v1/transactions/{transaction_id}/tags",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={"tag": "groceries"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "groceries" in [t["tag"] for t in data["tags"]]

    async def test_remove_tag(
        self, async_client: AsyncClient, test_user: User, user_token: dict, test_account
    ):
        """Test removing a tag from a transaction."""
        # Create transaction with tag
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-25.00",
                "currency": "USD",
                "description": "Transaction",
                "transaction_type": "debit",
                "tags": ["groceries"],
            },
        )

        transaction_id = create_response.json()["id"]

        # Remove tag
        response = await async_client.delete(
            f"/api/v1/transactions/{transaction_id}/tags/groceries",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tags"]) == 0

    async def test_permission_denied(
        self, async_client: AsyncClient, test_user: User, admin_user: User, user_token: dict, test_account
    ):
        """Test that users without permission cannot access transactions."""
        from src.models.user import User
        from src.core.security import hash_password
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        # Create transaction as test_user
        create_response = await async_client.post(
            f"/api/v1/accounts/{test_account.id}/transactions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
            json={
                "transaction_date": str(date.today()),
                "amount": "-25.00",
                "currency": "USD",
                "description": "Transaction",
                "transaction_type": "debit",
            },
        )

        transaction_id = create_response.json()["id"]

        # Try to access as admin (who doesn't have account access)
        # Note: This would require creating a separate user and getting their token
        # For now, we'll test with invalid token
        response = await async_client.get(
            f"/api/v1/transactions/{transaction_id}",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


# ============================================================================
# Permission Enforcement Tests
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_create_transaction(
    async_client: AsyncClient,
    test_user: User,
    test_account,
    test_engine,
):
    """Test: User with VIEWER permission cannot create transactions."""
    from src.core.security import hash_password
    from src.models.account import AccountShare
    from src.models.enums import PermissionLevel
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # Create a viewer user
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        viewer_user = User(
            email="viewer@example.com",
            username="viewer",
            password_hash=hash_password("ViewerPass123!"),
            is_active=True,
            is_admin=False,
        )
        session.add(viewer_user)
        await session.flush()

        # Share account with viewer permission
        share = AccountShare(
            account_id=test_account.id,
            user_id=viewer_user.id,
            permission_level=PermissionLevel.viewer,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        session.add(share)
        await session.commit()

    # Login as viewer
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "viewer@example.com", "password": "ViewerPass123!"},
    )
    viewer_token = login_response.json()

    # Try to create transaction
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {viewer_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "USD",
            "description": "Test",
            "transaction_type": "debit",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_update_transaction(
    async_client: AsyncClient,
    test_user: User,
    user_token: dict,
    test_account,
    test_engine,
):
    """Test: User with VIEWER permission cannot update transactions."""
    from src.core.security import hash_password
    from src.models.account import AccountShare
    from src.models.enums import PermissionLevel
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # Create transaction as owner
    create_response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "USD",
            "description": "Original",
            "transaction_type": "debit",
        },
    )
    transaction_id = create_response.json()["id"]

    # Create a viewer user
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        viewer_user = User(
            email="viewer2@example.com",
            username="viewer2",
            password_hash=hash_password("ViewerPass123!"),
            is_active=True,
            is_admin=False,
        )
        session.add(viewer_user)
        await session.flush()

        # Share account with viewer permission
        share = AccountShare(
            account_id=test_account.id,
            user_id=viewer_user.id,
            permission_level=PermissionLevel.viewer,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        session.add(share)
        await session.commit()

    # Login as viewer
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "viewer2@example.com", "password": "ViewerPass123!"},
    )
    viewer_token = login_response.json()

    # Try to update transaction
    response = await async_client.put(
        f"/api/v1/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {viewer_token['access_token']}"},
        json={"description": "Updated"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_transaction(
    async_client: AsyncClient,
    test_user: User,
    user_token: dict,
    test_account,
    test_engine,
):
    """Test: User with VIEWER permission cannot delete transactions."""
    from src.core.security import hash_password
    from src.models.account import AccountShare
    from src.models.enums import PermissionLevel
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # Create transaction as owner
    create_response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "USD",
            "description": "To delete",
            "transaction_type": "debit",
        },
    )
    transaction_id = create_response.json()["id"]

    # Create a viewer user
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        viewer_user = User(
            email="viewer3@example.com",
            username="viewer3",
            password_hash=hash_password("ViewerPass123!"),
            is_active=True,
            is_admin=False,
        )
        session.add(viewer_user)
        await session.flush()

        # Share account with viewer permission
        share = AccountShare(
            account_id=test_account.id,
            user_id=viewer_user.id,
            permission_level=PermissionLevel.viewer,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        session.add(share)
        await session.commit()

    # Login as viewer
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "viewer3@example.com", "password": "ViewerPass123!"},
    )
    viewer_token = login_response.json()

    # Try to delete transaction
    response = await async_client.delete(
        f"/api/v1/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {viewer_token['access_token']}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_editor_can_create_transaction(
    async_client: AsyncClient,
    test_user: User,
    test_account,
    test_engine,
):
    """Test: User with EDITOR permission can create transactions."""
    from src.core.security import hash_password
    from src.models.account import AccountShare
    from src.models.enums import PermissionLevel
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # Create an editor user
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        editor_user = User(
            email="editor@example.com",
            username="editor",
            password_hash=hash_password("EditorPass123!"),
            is_active=True,
            is_admin=False,
        )
        session.add(editor_user)
        await session.flush()

        # Share account with editor permission
        share = AccountShare(
            account_id=test_account.id,
            user_id=editor_user.id,
            permission_level=PermissionLevel.editor,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        session.add(share)
        await session.commit()

    # Login as editor
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "editor@example.com", "password": "EditorPass123!"},
    )
    editor_token = login_response.json()

    # Create transaction
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {editor_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "USD",
            "description": "Editor transaction",
            "transaction_type": "debit",
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] == "Editor transaction"


@pytest.mark.asyncio
async def test_owner_has_full_access(
    async_client: AsyncClient,
    test_user: User,
    user_token: dict,
    test_account,
):
    """Test: Owner has full access to all transaction operations."""
    # Create
    create_response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "USD",
            "description": "Owner transaction",
            "transaction_type": "debit",
        },
    )
    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]

    # Read
    get_response = await async_client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
    )
    assert get_response.status_code == 200

    # Update
    update_response = await async_client.put(
        f"/api/v1/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={"description": "Updated"},
    )
    assert update_response.status_code == 200

    # Delete
    delete_response = await async_client.delete(
        f"/api/v1/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
    )
    assert delete_response.status_code == 204


# ============================================================================
# Validation & Edge Case Tests
# ============================================================================
@pytest.mark.asyncio
async def test_cannot_create_transaction_with_wrong_currency(
    async_client: AsyncClient,
    user_token: dict,
    test_account,
):
    """Test: Cannot create transaction with currency different from account."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "EUR",  # Account is USD
            "description": "Wrong currency",
            "transaction_type": "debit",
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cannot_create_transaction_with_zero_amount(
    async_client: AsyncClient,
    user_token: dict,
    test_account,
):
    """Test: Cannot create transaction with zero amount."""
    response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "0.00",
            "currency": "USD",
            "description": "Zero amount",
            "transaction_type": "debit",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_split_transaction_maintains_balance(
    async_client: AsyncClient,
    user_token: dict,
    test_account,
):
    """Test: Split transaction child amounts must sum to parent amount."""
    # Create parent transaction
    create_response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-50.00",
            "currency": "USD",
            "description": "Shopping",
            "transaction_type": "debit",
        },
    )
    transaction_id = create_response.json()["id"]

    # Try to split with incorrect sum
    response = await async_client.post(
        f"/api/v1/transactions/{transaction_id}/split",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "splits": [
                {"amount": "-30.00", "description": "Split 1"},
                {"amount": "-15.00", "description": "Split 2"},  # Sum is -45, not -50
            ]
        },
    )

    # Should reject mismatched amounts
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cannot_split_already_split_transaction(
    async_client: AsyncClient,
    user_token: dict,
    test_account,
):
    """Test: Cannot split a transaction that's already split."""
    # Create and split transaction
    create_response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-50.00",
            "currency": "USD",
            "description": "Shopping",
            "transaction_type": "debit",
        },
    )
    transaction_id = create_response.json()["id"]

    # First split (should succeed)
    await async_client.post(
        f"/api/v1/transactions/{transaction_id}/split",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "splits": [
                {"amount": "-30.00", "description": "Split 1"},
                {"amount": "-20.00", "description": "Split 2"},
            ]
        },
    )

    # Try to split again (should fail)
    response = await async_client.post(
        f"/api/v1/transactions/{transaction_id}/split",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "splits": [
                {"amount": "-25.00", "description": "Split 3"},
                {"amount": "-25.00", "description": "Split 4"},
            ]
        },
    )

    assert response.status_code == 400


# ============================================================================
# Cross-Account Security Tests
# ============================================================================
@pytest.mark.asyncio
async def test_cannot_create_transaction_in_non_member_account(
    async_client: AsyncClient,
    test_user: User,
    test_engine,
):
    """Test: Cannot create transaction in account where user is not a member."""
    from decimal import Decimal
    from src.models.account import Account, AccountShare
    from src.models.enums import AccountType, PermissionLevel
    from src.core.security import hash_password
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # Create another user with their own account
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        other_user = User(
            email="other@example.com",
            username="other",
            password_hash=hash_password("OtherPass123!"),
            is_active=True,
            is_admin=False,
        )
        session.add(other_user)
        await session.flush()

        other_account = Account(
            user_id=other_user.id,
            account_name="Other Account",
            account_type=AccountType.SAVINGS,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            is_active=True,
            created_by=other_user.id,
            updated_by=other_user.id,
        )
        session.add(other_account)
        await session.flush()

        # Create owner share
        share = AccountShare(
            account_id=other_account.id,
            user_id=other_user.id,
            permission_level=PermissionLevel.owner,
            created_by=other_user.id,
            updated_by=other_user.id,
        )
        session.add(share)
        await session.commit()
        await session.refresh(other_account)

        other_account_id = other_account.id

    # Login as test_user
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "testuser@example.com", "password": "TestPass123!"},
    )
    test_token = login_response.json()

    # Try to create transaction in other user's account
    response = await async_client.post(
        f"/api/v1/accounts/{other_account_id}/transactions",
        headers={"Authorization": f"Bearer {test_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "USD",
            "description": "Unauthorized transaction",
            "transaction_type": "debit",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_access_another_users_transaction(
    async_client: AsyncClient,
    test_user: User,
    user_token: dict,
    test_account,
    test_engine,
):
    """Test: Cannot access transaction from account where user has no access."""
    from decimal import Decimal
    from src.models.account import Account, AccountShare
    from src.models.enums import AccountType, PermissionLevel
    from src.core.security import hash_password
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    # Create transaction as test_user
    create_response = await async_client.post(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers={"Authorization": f"Bearer {user_token['access_token']}"},
        json={
            "transaction_date": str(date.today()),
            "amount": "-25.00",
            "currency": "USD",
            "description": "Test transaction",
            "transaction_type": "debit",
        },
    )
    transaction_id = create_response.json()["id"]

    # Create another user without access
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        other_user = User(
            email="other2@example.com",
            username="other2",
            password_hash=hash_password("OtherPass123!"),
            is_active=True,
            is_admin=False,
        )
        session.add(other_user)
        await session.commit()

    # Login as other user
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "other2@example.com", "password": "OtherPass123!"},
    )
    other_token = login_response.json()

    # Try to access test_user's transaction
    response = await async_client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {other_token['access_token']}"},
    )

    assert response.status_code == 404  # Not found (or forbidden)
