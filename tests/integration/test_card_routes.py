"""
Integration tests for card management API endpoints.

Tests cover:
- Card creation (POST /api/v1/cards)
- Card retrieval (GET /api/v1/cards/{id})
- Card listing (GET /api/v1/cards)
- Card update (PATCH /api/v1/cards/{id})
- Card deletion (DELETE /api/v1/cards/{id})
- Authorization checks
- Validation errors
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.account import Account
from models.card import Card
from models.enums import CardType
from models.financial_institution import FinancialInstitution


@pytest.mark.asyncio
class TestCreateCard:
    """Tests for POST /api/v1/cards."""

    async def test_create_card_success(
        self,
        async_client: AsyncClient,
        test_account: Account,
        user_token: dict,
        test_financial_institution: FinancialInstitution,
    ):
        """Test successful card creation."""
        response = await async_client.post(
            "/api/v1/cards",
            json={
                "account_id": str(test_account.id),
                "card_type": "credit_card",
                "name": "Chase Sapphire Reserve",
                "last_four_digits": "4242",
                "card_network": "Visa",
                "expiry_month": 12,
                "expiry_year": 2027,
                "credit_limit": 25000.00,
                "financial_institution_id": str(test_financial_institution.id),
                "notes": "Primary travel card",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Chase Sapphire Reserve"
        assert data["card_type"] == "credit_card"
        assert data["last_four_digits"] == "4242"

    async def test_create_card_minimal(
        self,
        async_client: AsyncClient,
        test_account: Account,
        user_token: dict,
    ):
        """Test card creation with minimal required fields."""
        response = await async_client.post(
            "/api/v1/cards",
            json={
                "account_id": str(test_account.id),
                "card_type": "debit_card",
                "name": "Checking Debit",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Checking Debit"
        assert data["card_type"] == "debit_card"

    async def test_create_card_unauthorized(
        self,
        async_client: AsyncClient,
        test_account: Account,
    ):
        """Test card creation without authentication."""
        response = await async_client.post(
            "/api/v1/cards",
            json={
                "account_id": str(test_account.id),
                "card_type": "credit_card",
                "name": "Test Card",
            },
        )

        assert response.status_code == 401

    async def test_create_card_account_not_found(
        self,
        async_client: AsyncClient,
        user_token: dict,
    ):
        """Test card creation with non-existent account."""
        response = await async_client.post(
            "/api/v1/cards",
            json={
                "account_id": str(uuid.uuid4()),
                "card_type": "credit_card",
                "name": "Test Card",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_create_card_invalid_expiry_month(
        self,
        async_client: AsyncClient,
        test_account: Account,
        user_token: dict,
    ):
        """Test card creation with invalid expiry month."""
        response = await async_client.post(
            "/api/v1/cards",
            json={
                "account_id": str(test_account.id),
                "card_type": "credit_card",
                "name": "Test Card",
                "expiry_month": 13,
                "expiry_year": 2027,
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestGetCard:
    """Tests for GET /api/v1/cards/{id}."""

    async def test_get_card_success(
        self,
        async_client: AsyncClient,
        test_card: Card,
        user_token: dict,
    ):
        """Test successful card retrieval."""
        response = await async_client.get(
            f"/api/v1/cards/{test_card.id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_card.id)
        assert data["name"] == test_card.name

    async def test_get_card_not_found(
        self,
        async_client: AsyncClient,
        user_token: dict,
    ):
        """Test getting non-existent card."""
        response = await async_client.get(
            f"/api/v1/cards/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_get_card_unauthorized(
        self,
        async_client: AsyncClient,
        test_card: Card,
    ):
        """Test getting card without authentication."""
        response = await async_client.get(f"/api/v1/cards/{test_card.id}")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestListCards:
    """Tests for GET /api/v1/cards."""

    async def test_list_cards_success(
        self,
        async_client: AsyncClient,
        test_card: Card,
        user_token: dict,
    ):
        """Test successful card listing."""
        response = await async_client.get(
            "/api/v1/cards",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Verify paginated response structure
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        # Verify pagination metadata
        assert data["meta"]["page"] == 1
        assert data["meta"]["total"] >= 1

    async def test_list_cards_filter_by_type(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_account: Account,
        test_user,
        user_token: dict,
    ):
        """Test listing cards filtered by card type."""
        from repositories.card_repository import CardRepository

        from models.card import Card

        repo = CardRepository(db_session)
        card = Card(
            account_id=test_account.id,
            card_type=CardType.credit_card,
            name="Credit Card",
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        await repo.add(card)

        response = await async_client.get(
            "/api/v1/cards?card_type=credit_card",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Verify paginated response with filter
        assert "data" in data
        assert all(card["card_type"] == "credit_card" for card in data["data"])

    async def test_list_cards_unauthorized(
        self,
        async_client: AsyncClient,
    ):
        """Test listing cards without authentication."""
        response = await async_client.get("/api/v1/cards")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateCard:
    """Tests for PATCH /api/v1/cards/{id}."""

    async def test_update_card_success(
        self,
        async_client: AsyncClient,
        test_card: Card,
        user_token: dict,
    ):
        """Test successful card update."""
        response = await async_client.patch(
            f"/api/v1/cards/{test_card.id}",
            json={
                "name": "Updated Card Name",
                "notes": "Updated notes",
            },
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Card Name"
        assert data["notes"] == "Updated notes"

    async def test_update_card_not_found(
        self,
        async_client: AsyncClient,
        user_token: dict,
    ):
        """Test updating non-existent card."""
        response = await async_client.patch(
            f"/api/v1/cards/{uuid.uuid4()}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_update_card_unauthorized(
        self,
        async_client: AsyncClient,
        test_card: Card,
    ):
        """Test updating card without authentication."""
        response = await async_client.patch(
            f"/api/v1/cards/{test_card.id}",
            json={"name": "Updated"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestDeleteCard:
    """Tests for DELETE /api/v1/cards/{id}."""

    async def test_delete_card_success(
        self,
        async_client: AsyncClient,
        test_card: Card,
        user_token: dict,
    ):
        """Test successful card deletion."""
        response = await async_client.delete(
            f"/api/v1/cards/{test_card.id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 204

        # Verify card is soft-deleted
        get_response = await async_client.get(
            f"/api/v1/cards/{test_card.id}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )
        assert get_response.status_code == 404

    async def test_delete_card_not_found(
        self,
        async_client: AsyncClient,
        user_token: dict,
    ):
        """Test deleting non-existent card."""
        response = await async_client.delete(
            f"/api/v1/cards/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {user_token['access_token']}"},
        )

        assert response.status_code == 404

    async def test_delete_card_unauthorized(
        self,
        async_client: AsyncClient,
        test_card: Card,
    ):
        """Test deleting card without authentication."""
        response = await async_client.delete(f"/api/v1/cards/{test_card.id}")

        assert response.status_code == 401
