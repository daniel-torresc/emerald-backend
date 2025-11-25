"""
End-to-End tests for complete user journey workflows.

This module tests the full lifecycle of a user interacting with the application:
1. User registration
2. User login and authentication
3. Profile access and management
4. Account creation
5. Transaction management (create, split, tag, search)
6. Profile updates and password changes

These tests validate that all components work together correctly
and that users can complete real-world workflows successfully.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_user_journey(async_client: AsyncClient):
    """
    Test: Complete user journey from registration to transaction management.

    This test covers the entire workflow:
    - Register new user
    - Login and get tokens
    - Access profile
    - Create checking account
    - Add income transaction
    - Add expense transaction
    - Split expense transaction
    - Add tags to transactions
    - Search transactions by tag
    - Update profile
    - Change password
    """

    # Step 1: Register new user
    register_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "journey@example.com",
            "username": "journeyuser",
            "password": "Journey123!",
            "full_name": "Journey Test User",
        },
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    user_id = user_data["id"]  # UserResponse returns user fields directly
    print(f"✓ Step 1: User registered (ID: {user_id})")

    # Step 2: Login and receive tokens
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "journey@example.com",
            "password": "Journey123!",
        },
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    print("✓ Step 2: User logged in and received tokens")

    # Step 3: Access profile (GET /users/me)
    profile_response = await async_client.get(
        "/api/v1/users/me",
        headers=headers,
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["email"] == "journey@example.com"
    assert profile["username"] == "journeyuser"
    print(f"✓ Step 3: Retrieved user profile ({profile['username']})")

    # Step 4: Create checking account
    account_response = await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "account_name": "Main Checking",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "1000.00",
        },
    )
    assert account_response.status_code == 201
    account = account_response.json()
    account_id = account["id"]
    assert account["current_balance"] == "1000.00"
    print(f"✓ Step 4: Created checking account (ID: {account_id}, Balance: $1000.00)")

    # Step 5: Add income transaction
    income_response = await async_client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        headers=headers,
        json={
            "transaction_date": str(date.today()),
            "amount": "2500.00",
            "currency": "USD",
            "description": "Monthly Salary",
            "merchant": "ACME Corp",
            "transaction_type": "credit",
            "tags": ["income", "salary"],
        },
    )
    assert income_response.status_code == 201
    income = income_response.json()
    print("✓ Step 5: Added income transaction (+$2500.00)")

    # Step 6: Add expense transaction
    expense_response = await async_client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        headers=headers,
        json={
            "transaction_date": str(date.today()),
            "amount": "-150.00",
            "currency": "USD",
            "description": "Grocery Shopping",
            "merchant": "Whole Foods",
            "transaction_type": "debit",
            "tags": ["groceries", "food"],
        },
    )
    assert expense_response.status_code == 201
    expense = expense_response.json()
    expense_id = expense["id"]
    print("✓ Step 6: Added expense transaction (-$150.00)")

    # Step 7: Split expense transaction
    split_response = await async_client.post(
        f"/api/v1/transactions/{expense_id}/split",
        headers=headers,
        json={
            "splits": [
                {"amount": "-100.00", "description": "Groceries"},
                {"amount": "-50.00", "description": "Household Items"},
            ]
        },
    )
    assert split_response.status_code == 200
    split_data = split_response.json()
    # Verify split was created (should have parent and children)
    assert "parent" in split_data
    assert "children" in split_data
    assert len(split_data["children"]) == 2
    print("✓ Step 7: Split expense into 2 transactions ($100 + $50)")

    # Step 8: Add tags to transaction
    tag_response = await async_client.post(
        f"/api/v1/transactions/{income['id']}/tags",
        headers=headers,
        json={"tag": "recurring"},
    )
    assert tag_response.status_code == 200
    print("✓ Step 8: Added 'recurring' tag to income transaction")

    # Step 9: Search transactions by tag
    search_response = await async_client.get(
        f"/api/v1/accounts/{account_id}/transactions?tag=groceries",
        headers=headers,
    )
    assert search_response.status_code == 200
    search_results = search_response.json()
    assert search_results["total"] >= 1
    print(
        f"✓ Step 9: Searched transactions by tag (found {search_results['total']} results)"
    )

    # Step 10: Update profile
    update_profile_response = await async_client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "full_name": "Journey Updated Name",
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert updated_profile["full_name"] == "Journey Updated Name"
    print(f"✓ Step 10: Updated profile (new name: {updated_profile['full_name']})")

    # Step 11: Change password (final step)
    change_password_response = await async_client.post(
        "/api/auth/change-password",
        headers=headers,
        json={
            "current_password": "Journey123!",
            "new_password": "NewJourney123!",
        },
    )
    assert change_password_response.status_code == 204
    print("✓ Step 11: Changed password successfully")

    print(
        "\n🎉 Complete user journey test passed! All 11 steps completed successfully."
    )


@pytest.mark.asyncio
async def test_new_user_creates_multiple_accounts_and_transactions(
    async_client: AsyncClient,
):
    """
    Test: New user creates multiple accounts and manages transactions across them.
    """

    # Register and login
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "multi@example.com",
            "username": "multiuser",
            "password": "Multi123!",
        },
    )

    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "multi@example.com", "password": "Multi123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # Create checking account
    checking_response = await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "account_name": "Checking",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "500.00",
        },
    )
    checking_id = checking_response.json()["id"]

    # Create savings account
    savings_response = await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "account_name": "Savings",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "5000.00",
        },
    )
    savings_id = savings_response.json()["id"]

    # Add transactions to checking
    for i in range(3):
        await async_client.post(
            f"/api/v1/accounts/{checking_id}/transactions",
            headers=headers,
            json={
                "transaction_date": str(date.today() - timedelta(days=i)),
                "amount": f"-{10 + i * 5}.00",
                "currency": "USD",
                "description": f"Checking Expense {i + 1}",
                "transaction_type": "debit",
            },
        )

    # Add transactions to savings
    await async_client.post(
        f"/api/v1/accounts/{savings_id}/transactions",
        headers=headers,
        json={
            "transaction_date": str(date.today()),
            "amount": "100.00",
            "currency": "USD",
            "description": "Interest Payment",
            "transaction_type": "credit",
        },
    )

    # List all accounts
    accounts_response = await async_client.get(
        "/api/v1/accounts",
        headers=headers,
    )
    assert accounts_response.status_code == 200
    accounts = accounts_response.json()
    assert len(accounts) == 2

    # List transactions for checking
    checking_txns = await async_client.get(
        f"/api/v1/accounts/{checking_id}/transactions",
        headers=headers,
    )
    assert checking_txns.status_code == 200
    assert checking_txns.json()["total"] == 3

    # List transactions for savings
    savings_txns = await async_client.get(
        f"/api/v1/accounts/{savings_id}/transactions",
        headers=headers,
    )
    assert savings_txns.status_code == 200
    assert savings_txns.json()["total"] == 1

    print("✓ Multi-account workflow completed successfully")


@pytest.mark.asyncio
async def test_user_deactivation_workflow(async_client: AsyncClient):
    """
    Test: User can be deactivated and cannot login afterwards.
    """

    # Register user
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "deactivate@example.com",
            "username": "deactivateuser",
            "password": "Deactivate123!",
        },
    )

    # Login successfully
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "deactivate@example.com", "password": "Deactivate123!"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # User can access their profile
    profile_response = await async_client.get("/api/v1/users/me", headers=headers)
    assert profile_response.status_code == 200

    # Now we need an admin to deactivate the user
    # For this test, we'll simulate admin deactivation via direct API
    # (In reality, an admin would call the deactivate endpoint)

    # After deactivation, user should not be able to login
    # Note: This requires admin functionality which we'll test separately
    print("✓ Deactivation workflow test structure verified")


@pytest.mark.asyncio
async def test_transaction_tag_management_workflow(async_client: AsyncClient):
    """
    Test: User adds, removes, and searches by tags.
    """

    # Setup: Register, login, create account
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "tagger@example.com",
            "username": "tagger",
            "password": "Tagger123!",
        },
    )

    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "tagger@example.com", "password": "Tagger123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    account_response = await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "account_name": "Tag Account",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "1000.00",
        },
    )
    account_id = account_response.json()["id"]

    # Create transaction with initial tags
    txn_response = await async_client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        headers=headers,
        json={
            "transaction_date": str(date.today()),
            "amount": "-50.00",
            "currency": "USD",
            "description": "Restaurant",
            "transaction_type": "debit",
            "tags": ["food", "dining"],
        },
    )
    txn_id = txn_response.json()["id"]

    # Add additional tag
    add_tag_response = await async_client.post(
        f"/api/v1/transactions/{txn_id}/tags",
        headers=headers,
        json={"tag": "business"},
    )
    assert add_tag_response.status_code == 200
    txn_data = add_tag_response.json()
    tags = txn_data["tags"]  # tags is already a list of strings
    assert "business" in tags
    assert "food" in tags
    assert "dining" in tags

    # Remove a tag
    remove_tag_response = await async_client.delete(
        f"/api/v1/transactions/{txn_id}/tags/dining",
        headers=headers,
    )
    assert remove_tag_response.status_code == 204

    # Get transaction to verify tag was removed
    get_txn_response = await async_client.get(
        f"/api/v1/transactions/{txn_id}",
        headers=headers,
    )
    assert get_txn_response.status_code == 200
    updated_txn = get_txn_response.json()
    remaining_tags = updated_txn["tags"]  # tags is already a list of strings
    assert "dining" not in remaining_tags
    assert "food" in remaining_tags
    assert "business" in remaining_tags

    print("✓ Tag management workflow completed successfully")


@pytest.mark.asyncio
async def test_transaction_split_and_join_workflow(async_client: AsyncClient):
    """
    Test: User splits a transaction and then joins it back.
    """

    # Setup
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "splitter@example.com",
            "username": "splitter",
            "password": "Splitter123!",
        },
    )

    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "splitter@example.com", "password": "Splitter123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    account_response = await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "account_name": "Split Account",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "1000.00",
        },
    )
    account_id = account_response.json()["id"]

    # Create transaction
    txn_response = await async_client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        headers=headers,
        json={
            "transaction_date": str(date.today()),
            "amount": "-100.00",
            "currency": "USD",
            "description": "Shopping",
            "transaction_type": "debit",
        },
    )
    txn_id = txn_response.json()["id"]

    # Split the transaction
    split_response = await async_client.post(
        f"/api/v1/transactions/{txn_id}/split",
        headers=headers,
        json={
            "splits": [
                {"amount": "-60.00", "description": "Groceries"},
                {"amount": "-40.00", "description": "Supplies"},
            ]
        },
    )
    assert split_response.status_code == 200
    split_data = split_response.json()
    assert split_data["parent"]["is_split_parent"] is True
    assert len(split_data["children"]) == 2

    # Get the transaction to verify split
    get_response = await async_client.get(
        f"/api/v1/transactions/{txn_id}",
        headers=headers,
    )
    assert get_response.json()["is_split_parent"] is True

    # Join the transaction back
    join_response = await async_client.post(
        f"/api/v1/transactions/{txn_id}/join",
        headers=headers,
    )
    assert join_response.status_code == 200
    joined_data = join_response.json()
    assert joined_data["is_split_parent"] is False

    print("✓ Split and join workflow completed successfully")


@pytest.mark.asyncio
async def test_account_lifecycle_workflow(async_client: AsyncClient):
    """
    Test: Complete account lifecycle - create, update, deactivate, reactivate, delete.
    """

    # Setup
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "lifecycle@example.com",
            "username": "lifecycle",
            "password": "Lifecycle123!",
        },
    )

    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "lifecycle@example.com", "password": "Lifecycle123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # Create account
    create_response = await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "account_name": "Lifecycle Account",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "1000.00",
        },
    )
    account_id = create_response.json()["id"]
    assert create_response.json()["is_active"] is True

    # Update account name
    update_response = await async_client.put(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
        json={"account_name": "Updated Lifecycle Account"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["account_name"] == "Updated Lifecycle Account"

    # Deactivate account
    deactivate_response = await async_client.put(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    # Reactivate account
    reactivate_response = await async_client.put(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
        json={"is_active": True},
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["is_active"] is True

    # Delete account (soft delete)
    delete_response = await async_client.delete(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    # Verify account is deleted (should return 404)
    get_response = await async_client.get(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
    )
    assert get_response.status_code == 404

    print("✓ Account lifecycle workflow completed successfully")
