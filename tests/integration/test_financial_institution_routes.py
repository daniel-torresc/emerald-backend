"""
Integration tests for Financial Institution API routes.

Tests:
- POST /api/v1/financial-institutions - Create institution (admin only)
- GET /api/v1/financial-institutions - List institutions
- GET /api/v1/financial-institutions/{id} - Get institution by ID
- GET /api/v1/financial-institutions/swift/{code} - Get by SWIFT code
- GET /api/v1/financial-institutions/routing/{number} - Get by routing number
- PATCH /api/v1/financial-institutions/{id} - Update institution (admin only)
- POST /api/v1/financial-institutions/{id}/deactivate - Deactivate institution (admin only)
- Authentication and authorization
- Error handling and validation
"""

import pytest
from httpx import AsyncClient

from src.models.user import User


@pytest.mark.asyncio
class TestFinancialInstitutionRoutes:
    """Integration tests for financial institution API endpoints."""

    # ========================================================================
    # POST /api/v1/financial-institutions - Create Institution (Admin Only)
    # ========================================================================

    async def test_create_institution_success(
        self, async_client: AsyncClient, admin_user: User, admin_token: dict
    ):
        """Test successful institution creation by admin."""
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Bank of America, N.A.",
                "short_name": "Bank of America",
                "swift_code": "BOFAUS3N",
                "routing_number": "026009593",
                "country_code": "US",
                "institution_type": "bank",
                "logo_url": "https://logo.clearbit.com/bankofamerica.com",
                "website_url": "https://www.bankofamerica.com",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Bank of America, N.A."
        assert data["short_name"] == "Bank of America"
        assert data["swift_code"] == "BOFAUS3N"
        assert data["routing_number"] == "026009593"
        assert data["country_code"] == "US"
        assert data["institution_type"] == "bank"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_institution_minimal_data(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test institution creation with minimal required fields."""
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Test Fintech Ltd.",
                "short_name": "Test Fintech",
                "country_code": "GB",
                "institution_type": "fintech",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["swift_code"] is None
        assert data["routing_number"] is None
        assert data["logo_url"] is None
        assert data["website_url"] is None

    async def test_create_institution_duplicate_swift_code(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test that duplicate SWIFT code fails."""
        # Create first institution (using valid SWIFT code)
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "First Bank",
                "short_name": "First",
                "swift_code": "BARCGB22",  # Valid Barclays GB SWIFT
                "country_code": "GB",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Try to create duplicate
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Second Bank",
                "short_name": "Second",
                "swift_code": "BARCGB22",  # Same SWIFT code
                "country_code": "GB",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "SWIFT code" in data["error"]["message"]

    async def test_create_institution_duplicate_routing_number(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test that duplicate routing number fails."""
        # Create first institution (using valid routing number)
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "First US Bank",
                "short_name": "First US",
                "routing_number": "121000248",  # Valid routing number (Wells Fargo)
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Try to create duplicate
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Second US Bank",
                "short_name": "Second US",
                "routing_number": "121000248",  # Same routing number
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "routing number" in data["error"]["message"]

    async def test_create_institution_invalid_swift_code(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test validation of SWIFT code format."""
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Invalid Bank",
                "short_name": "Invalid",
                "swift_code": "INVALID",  # Too short
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 422
        data = response.json()
        # Check that validation error is about swift_code field
        assert any(
            "swift_code" in str(detail.get("field", ""))
            for detail in data["error"]["details"]
        )

    async def test_create_institution_invalid_routing_number(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test validation of routing number format."""
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Invalid Bank",
                "short_name": "Invalid",
                "routing_number": "12345",  # Not 9 digits
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 422

    async def test_create_institution_non_admin_forbidden(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test that regular users cannot create institutions."""
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Unauthorized Bank",
                "short_name": "Unauthorized",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 403

    async def test_create_institution_unauthenticated(self, async_client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Unauthorized Bank",
                "short_name": "Unauthorized",
                "country_code": "US",
                "institution_type": "bank",
            },
        )

        assert response.status_code == 401

    # ========================================================================
    # GET /api/v1/financial-institutions - List Institutions
    # ========================================================================

    async def test_list_institutions_success(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test listing institutions (authenticated users)."""
        # Create some institutions as admin
        for i in range(3):
            await async_client.post(
                "/api/v1/financial-institutions",
                json={
                    "name": f"Test Bank {i}",
                    "short_name": f"Bank{i}",
                    "country_code": "US",
                    "institution_type": "bank",
                },
                headers={"Authorization": f"Bearer {admin_token['access_token']}"},
            )

        # List as regular user
        response = await async_client.get(
            "/api/v1/financial-institutions",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data
        assert len(data["data"]) >= 3  # At least the 3 we created
        assert data["meta"]["page"] == 1

    async def test_list_institutions_filter_by_country(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test filtering institutions by country."""
        # Create Spanish and US banks
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Spanish Bank",
                "short_name": "Spanish",
                "country_code": "ES",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "US Bank",
                "short_name": "US",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Filter by Spain
        response = await async_client.get(
            "/api/v1/financial-institutions?country_code=ES",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        # All results should be Spanish
        for institution in data["data"]:
            assert institution["country_code"] == "ES"

    async def test_list_institutions_filter_by_type(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test filtering institutions by type."""
        # Create bank and fintech
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Traditional Bank",
                "short_name": "Trad",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Digital Fintech",
                "short_name": "Digital",
                "country_code": "US",
                "institution_type": "fintech",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Filter by fintech
        response = await async_client.get(
            "/api/v1/financial-institutions?institution_type=fintech",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        # All results should be fintech
        for institution in data["data"]:
            assert institution["institution_type"] == "fintech"

    async def test_list_institutions_search(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test searching institutions by name."""
        # Create institution with unique name
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "UniqueSearchBank Corporation",
                "short_name": "UniqueSearch",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Search for it
        response = await async_client.get(
            "/api/v1/financial-institutions?search=UniqueSearch",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) >= 1
        assert any("UniqueSearch" in inst["short_name"] for inst in data["data"])

    async def test_list_institutions_pagination(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test pagination of institution list."""
        # Create multiple institutions
        for i in range(25):
            await async_client.post(
                "/api/v1/financial-institutions",
                json={
                    "name": f"Pagination Test Bank {i}",
                    "short_name": f"PagTest{i}",
                    "country_code": "US",
                    "institution_type": "bank",
                },
                headers={"Authorization": f"Bearer {admin_token['access_token']}"},
            )

        # Get first page
        response = await async_client.get(
            "/api/v1/financial-institutions?page=1&page_size=10",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) <= 10
        assert data["meta"]["page"] == 1
        assert data["meta"]["page_size"] == 10

    async def test_list_institutions_unauthenticated(self, async_client: AsyncClient):
        """Test that unauthenticated users cannot list institutions."""
        response = await async_client.get("/api/v1/financial-institutions")

        assert response.status_code == 401

    # ========================================================================
    # GET /api/v1/financial-institutions/{id} - Get Institution by ID
    # ========================================================================

    async def test_get_institution_by_id_success(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test getting institution by ID."""
        # Create institution
        create_response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Get Test Bank",
                "short_name": "GetTest",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        institution_id = create_response.json()["id"]

        # Get as regular user
        response = await async_client.get(
            f"/api/v1/financial-institutions/{institution_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == institution_id
        assert data["short_name"] == "GetTest"

    async def test_get_institution_by_id_not_found(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test getting non-existent institution."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.get(
            f"/api/v1/financial-institutions/{fake_id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_get_institution_by_id_unauthenticated(
        self, async_client: AsyncClient
    ):
        """Test that unauthenticated users cannot get institution details."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.get(f"/api/v1/financial-institutions/{fake_id}")

        assert response.status_code == 401

    # ========================================================================
    # GET /api/v1/financial-institutions/swift/{code} - Get by SWIFT
    # ========================================================================

    async def test_get_institution_by_swift_code_success(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test getting institution by SWIFT code."""
        # Create institution
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "SWIFT Test Bank",
                "short_name": "SwiftTest",
                "swift_code": "HSBCGB2L",
                "country_code": "GB",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Get by SWIFT code
        response = await async_client.get(
            "/api/v1/financial-institutions/swift/HSBCGB2L",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["swift_code"] == "HSBCGB2L"
        assert data["short_name"] == "SwiftTest"

    async def test_get_institution_by_swift_code_not_found(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test getting institution with non-existent SWIFT code."""
        response = await async_client.get(
            "/api/v1/financial-institutions/swift/NOTFOUND",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    # ========================================================================
    # GET /api/v1/financial-institutions/routing/{number} - Get by Routing
    # ========================================================================

    async def test_get_institution_by_routing_number_success(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test getting institution by routing number."""
        # Create institution (using different routing number to avoid conflicts)
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Routing Test Bank",
                "short_name": "RoutingTest",
                "routing_number": "011000015",  # Different routing number (Federal Reserve)
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        # Get by routing number
        response = await async_client.get(
            "/api/v1/financial-institutions/routing/011000015",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["routing_number"] == "011000015"
        assert data["short_name"] == "RoutingTest"

    async def test_get_institution_by_routing_number_not_found(
        self, async_client: AsyncClient, user_token: dict
    ):
        """Test getting institution with non-existent routing number."""
        response = await async_client.get(
            "/api/v1/financial-institutions/routing/999999999",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    # ========================================================================
    # PATCH /api/v1/financial-institutions/{id} - Update Institution (Admin)
    # ========================================================================

    async def test_update_institution_success(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test updating institution as admin."""
        # Create institution
        create_response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Update Test Bank",
                "short_name": "UpdateTest",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        institution_id = create_response.json()["id"]

        # Update it
        response = await async_client.patch(
            f"/api/v1/financial-institutions/{institution_id}",
            json={
                "short_name": "Updated Name",
                "logo_url": "https://example.com/logo.png",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["short_name"] == "Updated Name"
        assert data["logo_url"] == "https://example.com/logo.png"
        assert data["name"] == "Update Test Bank"  # Unchanged

    async def test_update_institution_swift_code_conflict(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test updating institution with duplicate SWIFT code fails."""
        # Create two institutions
        await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "First Bank",
                "short_name": "First",
                "swift_code": "BOFAUS3N",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        create_response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Second Bank",
                "short_name": "Second",
                "swift_code": "CHASUS33",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        institution_id = create_response.json()["id"]

        # Try to update second to use first's SWIFT code
        response = await async_client.patch(
            f"/api/v1/financial-institutions/{institution_id}",
            json={"swift_code": "BOFAUS3N"},
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 409

    async def test_update_institution_non_admin_forbidden(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test that regular users cannot update institutions."""
        # Create institution as admin
        create_response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "No Update Bank",
                "short_name": "NoUpdate",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        institution_id = create_response.json()["id"]

        # Try to update as regular user
        response = await async_client.patch(
            f"/api/v1/financial-institutions/{institution_id}",
            json={"short_name": "Hacked Name"},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 403

    # ========================================================================
    # POST /api/v1/financial-institutions/{id}/deactivate - Deactivate (Admin)
    # ========================================================================

    async def test_deactivate_institution_success(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test deactivating institution as admin."""
        # Create institution
        create_response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "Deactivate Test Bank",
                "short_name": "DeactivateTest",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        institution_id = create_response.json()["id"]

        # Deactivate it
        response = await async_client.post(
            f"/api/v1/financial-institutions/{institution_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 200
        response.json()

    async def test_deactivate_institution_non_admin_forbidden(
        self, async_client: AsyncClient, user_token: dict, admin_token: dict
    ):
        """Test that regular users cannot deactivate institutions."""
        # Create institution as admin
        create_response = await async_client.post(
            "/api/v1/financial-institutions",
            json={
                "name": "No Deactivate Bank",
                "short_name": "NoDeactivate",
                "country_code": "US",
                "institution_type": "bank",
            },
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        institution_id = create_response.json()["id"]

        # Try to deactivate as regular user
        response = await async_client.post(
            f"/api/v1/financial-institutions/{institution_id}/deactivate",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 403

    async def test_deactivate_institution_not_found(
        self, async_client: AsyncClient, admin_token: dict
    ):
        """Test deactivating non-existent institution."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.post(
            f"/api/v1/financial-institutions/{fake_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        )

        assert response.status_code == 404
