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
        self,
        async_client: AsyncClient,
        test_user: User,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test successful account creation."""
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "My Checking Account",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1500.50",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["account_name"] == "My Checking Account"
        assert data["account_type_id"] == str(savings_account_type.id)
        assert data["account_type"]["key"] == "savings"
        assert data["account_type"]["name"] == "Savings"
        assert data["currency"] == "USD"
        assert data["opening_balance"] == "1500.50"
        assert data["current_balance"] == "1500.50"
        assert data["user_id"] == str(test_user.id)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_account_negative_balance(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        other_account_type,
    ):
        """Test creating account with negative balance (credit card/loan)."""
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Credit Card",
                "account_type_id": str(other_account_type.id),
                "currency": "USD",
                "opening_balance": "-500.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["opening_balance"] == "-500.00"
        assert data["current_balance"] == "-500.00"

    async def test_create_account_duplicate_name(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that duplicate account name fails."""
        # Create first account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Savings",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Try to create duplicate (case-insensitive)
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "savings",  # Different case
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "2000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 409  # 409 Conflict is correct for duplicates
        response_data = response.json()
        # Check the error message in the standardized error response format
        assert "error" in response_data
        error_message = response_data["error"]["message"].lower()
        assert "already exists" in error_message

    async def test_create_account_invalid_currency(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that invalid currency format fails validation."""
        invalid_currencies = ["US", "USDD", "usd", "123"]

        for currency in invalid_currencies:
            response = await async_client.post(
                "/api/v1/accounts",
                json={
                    "account_name": f"Account {currency}",
                    "account_type_id": str(savings_account_type.id),
                    "currency": currency,
                    "opening_balance": "1000.00",
                    "financial_institution_id": str(test_financial_institution.id),
                },
                headers={"Authorization": f"Bearer {user_token['access_token']}"},
            )

            assert response.status_code == 422  # Validation error

    async def test_create_account_unsupported_currency(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that unsupported currency codes fail validation."""
        # Valid format (3 uppercase letters) but not in supported list
        unsupported_currencies = ["ZZZ", "ABC", "XYZ", "QQQ"]

        for currency in unsupported_currencies:
            response = await async_client.post(
                "/api/v1/accounts",
                json={
                    "account_name": f"Account {currency}",
                    "account_type_id": str(savings_account_type.id),
                    "currency": currency,
                    "opening_balance": "1000.00",
                    "financial_institution_id": str(test_financial_institution.id),
                },
                headers={"Authorization": f"Bearer {user_token['access_token']}"},
            )

            assert response.status_code == 422  # Validation error
            error_data = response.json()
            assert "error" in error_data
            # Error message should mention unsupported currency
            error_message = str(error_data["error"]["message"]).lower()
            assert "unsupported" in error_message and "currency" in error_message

    async def test_create_account_unauthenticated(
        self,
        async_client: AsyncClient,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that unauthenticated request fails."""
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
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
        # Verify paginated response structure
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0

    async def test_list_accounts_multiple(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test listing multiple accounts."""
        # Create 3 accounts
        for i in range(3):
            await async_client.post(
                "/api/v1/accounts",
                json={
                    "account_name": f"Account {i}",
                    "account_type_id": str(savings_account_type.id),
                    "currency": "USD",
                    "opening_balance": "1000.00",
                    "financial_institution_id": str(test_financial_institution.id),
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
        # Verify paginated response
        assert "data" in data
        assert len(data["data"]) == 3

    async def test_list_accounts_filter_by_type(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
        other_account_type,
    ):
        """Test filtering accounts by type."""
        # Create savings account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Savings",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Create credit card account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Credit Card",
                "account_type_id": str(other_account_type.id),
                "currency": "USD",
                "opening_balance": "-500.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Filter by savings account type
        response = await async_client.get(
            f"/api/v1/accounts?account_type_id={str(savings_account_type.id)}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Verify paginated response with filter
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["account_type"]["key"] == "savings"

    async def test_list_accounts_filter_by_active(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that deleted accounts are not returned in list."""
        # Create first account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "To Be Deleted",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )
        account_id = create_response.json()["id"]

        # Delete it (soft delete)
        await async_client.delete(
            f"/api/v1/accounts/{account_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Create another account
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Still Active",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "2000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # List accounts - should only return non-deleted accounts
        response = await async_client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should only have the "Still Active" account, not the deleted one
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["account_name"] == "Still Active"

    async def test_list_accounts_pagination(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test pagination for list accounts."""
        # Create 5 accounts
        for i in range(5):
            await async_client.post(
                "/api/v1/accounts",
                json={
                    "account_name": f"Account {i}",
                    "account_type_id": str(savings_account_type.id),
                    "currency": "USD",
                    "opening_balance": "100.00",
                    "financial_institution_id": str(test_financial_institution.id),
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
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test getting account by ID."""
        # Create account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test Account",
                "account_type_id": str(savings_account_type.id),
                "currency": "EUR",
                "opening_balance": "2000.00",
                "financial_institution_id": str(test_financial_institution.id),
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
        test_financial_institution,
        savings_account_type,
    ):
        """Test that non-owner cannot access account."""
        # Create account as test_user
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Private",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
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
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test updating account name."""
        # Create account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Old Name",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
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

    async def test_update_account_duplicate_name(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that updating to duplicate name fails."""
        # Create two accounts
        await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Account One",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        create_response2 = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Account Two",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "2000.00",
                "financial_institution_id": str(test_financial_institution.id),
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

        assert response.status_code == 409  # 409 Conflict is correct for duplicates

    # ========================================================================
    # DELETE /api/v1/accounts/{id} - Delete Account
    # ========================================================================

    async def test_delete_account_success(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test deleting account (soft delete)."""
        # Create account
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "To Delete",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
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
        self,
        async_client: AsyncClient,
        user_token: dict,
        admin_token: dict,
        test_financial_institution,
        savings_account_type,
    ):
        """Test that non-owner cannot delete account."""
        # Create account as test_user
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
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

    # ========================================================================
    # Account Type Validation Tests (NEW)
    # ========================================================================

    async def test_create_account_invalid_account_type_id(
        self, async_client: AsyncClient, user_token: dict, test_financial_institution
    ):
        """Test creating account with non-existent account type ID."""
        import uuid

        fake_account_type_id = uuid.uuid4()

        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test Account",
                "account_type_id": str(fake_account_type_id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404
        response_data = response.json()
        assert "error" in response_data
        assert "not found" in response_data["error"]["message"].lower()

    async def test_create_account_nil_uuid_account_type(
        self, async_client: AsyncClient, user_token: dict, test_financial_institution
    ):
        """Test creating account with nil UUID for account type."""
        nil_uuid = "00000000-0000-0000-0000-000000000000"

        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test Account",
                "account_type_id": nil_uuid,
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        # Nil UUID validation only happens at account type creation, not when referencing
        # So the API tries to look it up and returns 404 (not found)
        assert response.status_code == 404
        response_data = response.json()
        assert "error" in response_data

    async def test_create_account_system_account_type_success(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        checking_account_type,
    ):
        """Test that any user can use system account types."""
        response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "System Type Account",
                "account_type_id": str(checking_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["account_type"]["key"] == "checking"

    async def test_update_account_change_account_type(
        self,
        async_client: AsyncClient,
        user_token: dict,
        test_financial_institution,
        savings_account_type,
        checking_account_type,
    ):
        """Test updating account to change account type."""
        # Create account with savings type
        create_response = await async_client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test Account",
                "account_type_id": str(savings_account_type.id),
                "currency": "USD",
                "opening_balance": "1000.00",
                "financial_institution_id": str(test_financial_institution.id),
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        account_id = create_response.json()["id"]

        # Update to checking type
        response = await async_client.put(
            f"/api/v1/accounts/{account_id}",
            json={"account_type_id": str(checking_account_type.id)},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["account_type"]["key"] == "checking"
        assert data["account_type_id"] == str(checking_account_type.id)
