"""
Integration tests for Account API routes.

Tests:
- POST /api/v1/accounts - Create account
- GET /api/v1/accounts - List accounts
- GET /api/v1/accounts/{id} - Get account by ID
- PUT /api/v1/accounts/{id} - Update account
- DELETE /api/v1/accounts/{id} - Delete account
- Authentication and authorization
- Error handling and validation
"""

import pytest
from httpx import AsyncClient

from src.models.user import User


@pytest.mark.asyncio
class TestAccountRoutes:
    """Integration tests for account API endpoints."""

    # ========================================================================
    # POST /api/v1/accounts - Create Account
    # ========================================================================

    async def test_create_account_success(
        self, async_client: AsyncClient, test_user: User, user_token: dict
    ):
        """Test successful account creation."""
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "My Checking Account",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1500.50",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["account_name"] == "My Checking Account"
        assert data["account_type"] == "savings"
        assert data["currency"] == "USD"
        assert data["opening_balance"] == "1500.50"
        assert data["current_balance"] == "1500.50"
        assert data["is_active"] is True
        assert data["user_id"] == str(test_user.id)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_account_negative_balance(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test creating account with negative balance (credit card/loan)."""
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Credit Card",
                "account_type": "credit_card",
                "currency": "USD",
                "opening_balance": "-500.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["opening_balance"] == "-500.00"
        assert data["current_balance"] == "-500.00"

    async def test_create_account_duplicate_name(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test that duplicate account name fails."""
        # Create first account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Savings",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Try to create duplicate (case-insensitive)
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "savings",  # Different case
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "2000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_create_account_invalid_currency(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test that invalid currency format fails validation."""
        invalid_currencies = ["US", "USDD", "usd", "123"]

        for currency in invalid_currencies:
            response = await async_client.post(
                "/api/v1/accounts",
                json={
                    "account_name": f"Account {currency}",
                    "account_type": "savings",
                    "currency": currency,
                    "opening_balance": "1000.00",
                },
                headers={"Authorization": f"Bearer {user_token['access_token']}"},
            )

            assert response.status_code == 422  # Validation error

    async def test_create_account_unauthenticated(self, async_client: AsyncClient):
        """Test that unauthenticated request fails."""
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
        )

        assert response.status_code == 401

    # ========================================================================
    # GET /api/v1/accounts - List Accounts
    # ========================================================================

    async def test_list_accounts_empty(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test listing accounts when user has none."""
        response = await async_client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_accounts_multiple(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test listing multiple accounts."""
        # Create 3 accounts
        for i in range(3):
            await async_client.post(
                "/api/v1/accounts",
                json={
                    "account_name": f"Account {i}",
                    "account_type": "savings",
                    "currency": "USD",
                    "opening_balance": "1000.00",
                },
                headers={"Authorization": f"Bearer {user_token['access_token']}"},
            )

        # List all
        response = await async_client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_list_accounts_filter_by_type(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test filtering accounts by type."""
        # Create savings account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Savings",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Create credit card account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Credit Card",
                "account_type": "credit_card",
                "currency": "USD",
                "opening_balance": "-500.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Filter by savings
        response = await async_client.get(
            "/api/v1/accounts?account_type=savings",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["account_type"] == "savings"

    async def test_list_accounts_filter_by_active(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test filtering accounts by active status."""
        # Create active account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Active",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )
        account_id = create_response.json()["id"]

        # Deactivate it
        await async_client.put(
            f"/api/v1/accounts/{account_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Create another active account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Still Active",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "2000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Filter by is_active=true
        response = await async_client.get(
            "/api/v1/accounts?is_active=true",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_active"] is True

    async def test_list_accounts_pagination(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test pagination for list accounts."""
        # Create 5 accounts
        for i in range(5):
            await async_client.post(
                "/api/v1/accounts",
                json={
                    "account_name": f"Account {i}",
                    "account_type": "savings",
                    "currency": "USD",
                    "opening_balance": "100.00",
                },
                headers={"Authorization": f"Bearer {user_token['access_token']}"},
            )

        # Get first 2
        response = await async_client.get(
            "/api/v1/accounts?skip=0&limit=2",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Get next 2
        response = await async_client.get(
            "/api/v1/accounts?skip=2&limit=2",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    # ========================================================================
    # GET /api/v1/accounts/{id} - Get Account by ID
    # ========================================================================

    async def test_get_account_success(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test getting account by ID."""
        # Create account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test Account",
                "account_type": "savings",
                "currency": "EUR",
                "opening_balance": "2000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account_id = create_response.json()["id"]

        # Get account
        response = await async_client.get(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == account_id
        assert data["account_name"] == "Test Account"
        assert data["currency"] == "EUR"

    async def test_get_account_not_found(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test getting non-existent account."""
        import uuid

        fake_id = uuid.uuid4()

        response = await async_client.get(
            f"/api/v1/accounts/{fake_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_get_account_not_owner(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_user: User,
        user_token: dict,
        admin_token: dict,
    ):
        """Test that non-owner cannot access account."""
        # Create account as test_user
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Private",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account_id = create_response.json()["id"]

        # Try to access as admin_user
        response = await async_client.get(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 404  # Should not reveal account exists

    # ========================================================================
    # PUT /api/v1/accounts/{id} - Update Account
    # ========================================================================

    async def test_update_account_name(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test updating account name."""
        # Create account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Old Name",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account_id = create_response.json()["id"]

        # Update name
        response = await async_client.put(
            f"/api/v1/accounts/{account_id}",
            json={"account_name": "New Name"},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["account_name"] == "New Name"

    async def test_update_account_is_active(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test updating account active status."""
        # Create account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account_id = create_response.json()["id"]

        # Deactivate
        response = await async_client.put(
            f"/api/v1/accounts/{account_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_update_account_duplicate_name(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test that updating to duplicate name fails."""
        # Create two accounts
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Account One",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        create_response2 = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Account Two",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "2000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account2_id = create_response2.json()["id"]

        # Try to rename account2 to "Account One"
        response = await async_client.put(
            f"/api/v1/accounts/{account2_id}",
            json={"account_name": "Account One"},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 400

    # ========================================================================
    # DELETE /api/v1/accounts/{id} - Delete Account
    # ========================================================================

    async def test_delete_account_success(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test deleting account (soft delete)."""
        # Create account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "To Delete",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account_id = create_response.json()["id"]

        # Delete account
        response = await async_client.delete(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 204

        # Verify account is gone
        get_response = await async_client.get(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )
        assert get_response.status_code == 404

    async def test_delete_account_not_owner(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test that non-owner cannot delete account."""
        # Create account as test_user
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account_id = create_response.json()["id"]

        # Try to delete as admin
        response = await async_client.delete(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_delete_account_not_found(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test deleting non-existent account."""
        import uuid

        fake_id = uuid.uuid4()

        response = await async_client.delete(
            f"/api/v1/accounts/{fake_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404
