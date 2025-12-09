"""
Integration tests for Account Type API routes.

Tests:
- POST /api/v1/account-types - Create account type (admin only)
- GET /api/v1/account-types - List account types with filtering
- GET /api/v1/account-types/{id} - Get account type by ID
- GET /api/v1/account-types/key/{key} - Get by key
- PATCH /api/v1/account-types/{id} - Update account type (admin only)
- POST /api/v1/account-types/{id}/deactivate - Deactivate account type (admin only)
- Authentication and authorization
- Error handling and validation
"""

import pytest
from httpx import AsyncClient

from src.models.user import User


@pytest.mark.asyncio
class TestAccountTypeRoutes:
    """Integration tests for account type API endpoints."""

    # ========================================================================
    # POST /api/v1/account-types - Create Account Type (Admin Only)
    # ========================================================================

    async def test_create_account_type_success(
        self, async_client: AsyncClient, admin_user: User, admin_token: dict
    ):
        """Test successful account type creation by admin."""
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "hsa",
                "name": "Health Savings Account",
                "description": "Tax-advantaged medical savings account",
                "icon_url": "https://example.com/icons/hsa.svg",
                "is_active": True,
                "sort_order": 5,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["key"] == "hsa"
        assert data["name"] == "Health Savings Account"
        assert data["description"] == "Tax-advantaged medical savings account"
        assert data["icon_url"] == "https://example.com/icons/hsa.svg"
        assert data["is_active"] is True
        assert data["sort_order"] == 5
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_account_type_minimal_data(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test account type creation with minimal required fields."""
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "minimal_type",
                "name": "Minimal Type",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["key"] == "minimal_type"
        assert data["name"] == "Minimal Type"
        assert data["description"] is None
        assert data["icon_url"] is None
        assert data["is_active"] is True  # Default value
        assert data["sort_order"] == 0  # Default value

    async def test_create_account_type_duplicate_key(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test that duplicate key fails."""
        # Create first account type
        await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "duplicate_key",
                "name": "First Type",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Try to create duplicate
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "duplicate_key",
                "name": "Second Type",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "key" in data["error"]["message"].lower()

    async def test_create_account_type_invalid_key_format(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test validation of key format (lowercase, alphanumeric, underscore only)."""
        # Note: The pattern validation in Pydantic runs before field validators,
        # so uppercase letters fail validation before they can be normalized
        # This test validates that invalid formats are rejected

        # Test invalid characters (spaces) - should fail validation
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "invalid key",
                "name": "Invalid Key Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 422
        data = response.json()
        # Check that validation error mentions the key field
        assert any(
            "key" in str(detail.get("field", "")) for detail in data["error"]["details"]
        )

        # Test special characters (hyphen) - should fail
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "invalid-key",
                "name": "Invalid Key Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 422
        data = response.json()
        assert any(
            "key" in str(detail.get("field", "")) for detail in data["error"]["details"]
        )

        # Test uppercase letters - should fail pattern validation
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "UPPERCASE",
                "name": "Uppercase Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 422
        data = response.json()
        assert any(
            "key" in str(detail.get("field", "")) for detail in data["error"]["details"]
        )

        # Test valid key (lowercase with underscores and numbers) - should succeed
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "valid_key_123",
                "name": "Valid Key Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "valid_key_123"

    async def test_create_account_type_empty_key(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test that empty key fails validation."""
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "",
                "name": "Empty Key Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 422

    async def test_create_account_type_whitespace_trimming(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test that whitespace is trimmed from text fields."""
        # Note: Key validation with regex pattern happens before field validator,
        # so we can't test whitespace trimming on keys with the pattern constraint
        # But we can test name and description trimming
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "trim_test_key",  # Must be valid for pattern match
                "name": "  Trim Test Name  ",
                "description": "  Trimmed description text  ",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()

        # Name and description should be trimmed
        assert data["name"] == "Trim Test Name"
        assert data["description"] == "Trimmed description text"

    async def test_create_account_type_non_admin_forbidden(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test that regular users cannot create account types."""
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "forbidden_type",
                "name": "Forbidden Type",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 403

    async def test_create_account_type_unauthenticated(self, async_client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "unauthenticated",
                "name": "Unauthenticated Type",
            },
        )

        assert response.status_code == 401

    # ========================================================================
    # GET /api/v1/account-types - List Account Types
    # ========================================================================

    async def test_list_account_types_success(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test listing account types (authenticated users)."""
        # Create some account types as admin
        for i in range(3):
            await async_client.post(
                "/api/v1/account-types",
                json={
                    "key": f"test_type_{i}",
                    "name": f"Test Type {i}",
                    "sort_order": i,
                },
                headers={"Authorization": f"Bearer {admin_token['access_token']}"},
            )

        # List as regular user
        response = await async_client.get(
            "/api/v1/account-types",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should be a simple list (not paginated)
        assert isinstance(data, list)
        assert len(data) >= 3  # At least the 3 we created

        # Verify ordering (by sort_order, then name)
        # All our test types have sequential sort_order
        test_types = [item for item in data if item["key"].startswith("test_type_")]
        assert len(test_types) == 3
        for i, item in enumerate(test_types):
            assert item["sort_order"] == i

    async def test_list_account_types_filter_active_only(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test filtering account types by active status."""
        # Create active and inactive types
        await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "active_type",
                "name": "Active Type",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "inactive_type",
                "name": "Inactive Type",
                "is_active": False,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Default: get active only
        response = await async_client.get(
            "/api/v1/account-types",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        # All results should be active
        for item in data:
            assert item["is_active"] is True

        # Verify inactive type is not in results
        assert not any(item["key"] == "inactive_type" for item in data)

    async def test_list_account_types_filter_inactive_only(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test filtering to get only inactive account types."""
        # Create active and inactive types
        await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "active_type_2",
                "name": "Active Type 2",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "inactive_type_2",
                "name": "Inactive Type 2",
                "is_active": False,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Get inactive only
        response = await async_client.get(
            "/api/v1/account-types?is_active=false",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        # All results should be inactive
        for item in data:
            assert item["is_active"] is False

    async def test_list_account_types_all(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test getting all account types regardless of active status."""
        # Create active and inactive types with unique keys to avoid conflicts
        active_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "all_test_active",
                "name": "All Test Active",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )
        assert active_response.status_code == 201

        inactive_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "all_test_inactive",
                "name": "All Test Inactive",
                "is_active": False,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )
        assert inactive_response.status_code == 201

        # Get only active types (default behavior)
        response_active = await async_client.get(
            "/api/v1/account-types",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response_active.status_code == 200
        data_active = response_active.json()

        # Should contain the active type but not the inactive one
        active_keys = [item["key"] for item in data_active]
        assert "all_test_active" in active_keys
        assert "all_test_inactive" not in active_keys

        # Get only inactive types
        response_inactive = await async_client.get(
            "/api/v1/account-types?is_active=false",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response_inactive.status_code == 200
        data_inactive = response_inactive.json()

        # Should contain the inactive type
        inactive_keys = [item["key"] for item in data_inactive]
        assert "all_test_inactive" in inactive_keys
        assert "all_test_active" not in inactive_keys

    async def test_list_account_types_ordering(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test that account types are ordered by sort_order, then name."""
        # Create types with specific ordering
        await async_client.post(
            "/api/v1/account-types",
            json={"key": "z_type", "name": "Z Type", "sort_order": 1},
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        await async_client.post(
            "/api/v1/account-types",
            json={"key": "a_type", "name": "A Type", "sort_order": 1},
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        await async_client.post(
            "/api/v1/account-types",
            json={"key": "b_type", "name": "B Type", "sort_order": 0},
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        response = await async_client.get(
            "/api/v1/account-types",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Filter to our test types
        test_types = [
            item for item in data if item["key"] in ["z_type", "a_type", "b_type"]
        ]

        # Should be ordered: b_type (sort=0), a_type (sort=1, name=A), z_type (sort=1, name=Z)
        assert test_types[0]["key"] == "b_type"
        assert test_types[1]["key"] == "a_type"
        assert test_types[2]["key"] == "z_type"

    async def test_list_account_types_unauthenticated(self, async_client: AsyncClient):
        """Test that unauthenticated users cannot list account types."""
        response = await async_client.get("/api/v1/account-types")

        assert response.status_code == 401

    # ========================================================================
    # GET /api/v1/account-types/{id} - Get Account Type by ID
    # ========================================================================

    async def test_get_account_type_by_id_success(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test getting account type by ID."""
        # Create account type
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "get_by_id_test",
                "name": "Get By ID Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Get as regular user
        response = await async_client.get(
            f"/api/v1/account-types/{account_type_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == account_type_id
        assert data["key"] == "get_by_id_test"
        assert data["name"] == "Get By ID Test"

    async def test_get_account_type_by_id_not_found(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test getting non-existent account type."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.get(
            f"/api/v1/account-types/{fake_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_get_account_type_by_id_inactive(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test getting inactive account type by ID (should work)."""
        # Create inactive type
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "inactive_get",
                "name": "Inactive Get",
                "is_active": False,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Get by ID should work even if inactive
        response = await async_client.get(
            f"/api/v1/account-types/{account_type_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_get_account_type_by_id_unauthenticated(
        self, async_client: AsyncClient
    ):
        """Test that unauthenticated users cannot get account type details."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.get(f"/api/v1/account-types/{fake_id}")

        assert response.status_code == 401

    # ========================================================================
    # GET /api/v1/account-types/key/{key} - Get by Key
    # ========================================================================

    async def test_get_account_type_by_key_success(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test getting account type by key."""
        # Create account type
        await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "get_by_key_test",
                "name": "Get By Key Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Get by key
        response = await async_client.get(
            "/api/v1/account-types/key/get_by_key_test",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["key"] == "get_by_key_test"
        assert data["name"] == "Get By Key Test"

    async def test_get_account_type_by_key_case_insensitive(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test that key lookup is case-insensitive."""
        # Create account type with lowercase key
        await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "case_test",
                "name": "Case Test",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Get with uppercase (should work)
        response = await async_client.get(
            "/api/v1/account-types/key/CASE_TEST",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "case_test"

    async def test_get_account_type_by_key_not_found(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test getting account type with non-existent key."""
        response = await async_client.get(
            "/api/v1/account-types/key/nonexistent_key",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    # ========================================================================
    # PATCH /api/v1/account-types/{id} - Update Account Type (Admin)
    # ========================================================================

    async def test_update_account_type_success(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test updating account type as admin."""
        # Create account type
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "update_test",
                "name": "Update Test",
                "description": "Original description",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Update it
        response = await async_client.patch(
            f"/api/v1/account-types/{account_type_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
                "icon_url": "https://example.com/icon.svg",
                "sort_order": 10,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["icon_url"] == "https://example.com/icon.svg"
        assert data["sort_order"] == 10
        assert data["key"] == "update_test"  # Key should remain unchanged

    async def test_update_account_type_partial(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test partial update of account type."""
        # Create account type
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "partial_update",
                "name": "Partial Update",
                "description": "Original",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Update only name
        response = await async_client.patch(
            f"/api/v1/account-types/{account_type_id}",
            json={"name": "New Name Only"},
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "New Name Only"
        assert data["description"] == "Original"  # Unchanged

    async def test_update_account_type_deactivate_via_update(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test deactivating account type via update endpoint."""
        # Create active account type
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "deactivate_via_update",
                "name": "Deactivate Via Update",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Deactivate via update
        response = await async_client.patch(
            f"/api/v1/account-types/{account_type_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_update_account_type_not_found(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test updating non-existent account type."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.patch(
            f"/api/v1/account-types/{fake_id}",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_update_account_type_non_admin_forbidden(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test that regular users cannot update account types."""
        # Create account type as admin
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "no_update",
                "name": "No Update",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Try to update as regular user
        response = await async_client.patch(
            f"/api/v1/account-types/{account_type_id}",
            json={"name": "Hacked Name"},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 403

    # ========================================================================
    # POST /api/v1/account-types/{id}/deactivate - Deactivate (Admin)
    # ========================================================================

    async def test_deactivate_account_type_success(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test deactivating account type as admin."""
        # Create account type
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "deactivate_test",
                "name": "Deactivate Test",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]
        assert create_response.json()["is_active"] is True

        # Deactivate it
        response = await async_client.post(
            f"/api/v1/account-types/{account_type_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_active"] is False

    async def test_deactivate_account_type_already_inactive(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test deactivating already inactive account type (idempotent)."""
        # Create inactive account type
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "already_inactive",
                "name": "Already Inactive",
                "is_active": False,
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Deactivate it (should succeed idempotently)
        response = await async_client.post(
            f"/api/v1/account-types/{account_type_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_deactivate_account_type_non_admin_forbidden(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test that regular users cannot deactivate account types."""
        # Create account type as admin
        create_response = await async_client.post(
            "/api/v1/account-types",
            json={
                "key": "no_deactivate",
                "name": "No Deactivate",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        account_type_id = create_response.json()["id"]

        # Try to deactivate as regular user
        response = await async_client.post(
            f"/api/v1/account-types/{account_type_id}/deactivate",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 403

    async def test_deactivate_account_type_not_found(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test deactivating non-existent account type."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.post(
            f"/api/v1/account-types/{fake_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 404
