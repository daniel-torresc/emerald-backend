"""
Unit tests for TransactionTagRepository.

Tests:
- Add tag to transaction
- Remove tag from transaction
- Get tags for transaction
- Get all tags for account
- Get tag usage counts
- Tag normalization
- Duplicate tag prevention
"""

from datetime import date
from decimal import Decimal

import pytest

from src.models.enums import TransactionType
from src.models.transaction import Transaction
from src.repositories.transaction_repository import TransactionRepository
from src.repositories.transaction_tag_repository import TransactionTagRepository


@pytest.mark.asyncio
class TestTransactionTagRepository:
    """Test suite for TransactionTagRepository."""

    async def test_add_tag(self, db_session, test_user, test_account):
        """Test adding a tag to a transaction."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Grocery shopping",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Add tag
        tag_repo = TransactionTagRepository(db_session)
        tag = await tag_repo.add_tag(created_trans.id, "groceries")

        assert tag.id is not None
        assert tag.transaction_id == created_trans.id
        assert tag.tag == "groceries"

    async def test_tag_normalization(self, db_session, test_user, test_account):
        """Test that tags are normalized (lowercased and trimmed)."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Transaction",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Add tag with uppercase and whitespace
        tag_repo = TransactionTagRepository(db_session)
        tag = await tag_repo.add_tag(created_trans.id, "  GROCERIES  ")

        assert tag.tag == "groceries"  # Normalized

    async def test_remove_tag(self, db_session, test_user, test_account):
        """Test removing a tag from a transaction."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Transaction",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Add and then remove tag
        tag_repo = TransactionTagRepository(db_session)
        await tag_repo.add_tag(created_trans.id, "groceries")
        removed = await tag_repo.remove_tag(created_trans.id, "groceries")

        assert removed is True

    async def test_remove_nonexistent_tag(self, db_session, test_user, test_account):
        """Test removing a tag that doesn't exist."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Transaction",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Try to remove non-existent tag
        tag_repo = TransactionTagRepository(db_session)
        removed = await tag_repo.remove_tag(created_trans.id, "nonexistent")

        assert removed is False

    async def test_get_tags(self, db_session, test_user, test_account):
        """Test getting all tags for a transaction."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Transaction",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Add multiple tags
        tag_repo = TransactionTagRepository(db_session)
        await tag_repo.add_tag(created_trans.id, "groceries")
        await tag_repo.add_tag(created_trans.id, "food")
        await tag_repo.add_tag(created_trans.id, "essentials")

        # Get all tags
        tags = await tag_repo.get_tags(created_trans.id)

        assert len(tags) == 3
        tag_names = [t.tag for t in tags]
        assert "groceries" in tag_names
        assert "food" in tag_names
        assert "essentials" in tag_names

    async def test_get_all_tags_for_account(self, db_session, test_user, test_account):
        """Test getting unique tags for an account."""
        trans_repo = TransactionRepository(db_session)
        tag_repo = TransactionTagRepository(db_session)

        # Create multiple transactions with tags
        tags_per_transaction = [
            ["groceries", "food"],
            ["gas", "transportation"],
            ["groceries", "essentials"],  # Duplicate "groceries"
        ]

        for tag_list in tags_per_transaction:
            # Create transaction
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.00"),
                currency="USD",
                description="Transaction",
                transaction_type=TransactionType.DEBIT,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            created_trans = await trans_repo.create(transaction)

            # Add tags
            for tag in tag_list:
                await tag_repo.add_tag(created_trans.id, tag)

        # Get unique tags for account
        unique_tags = await tag_repo.get_all_tags_for_account(test_account.id)

        # Should have 5 unique tags (groceries appears twice but counted once)
        assert len(unique_tags) == 5
        assert "groceries" in unique_tags
        assert "food" in unique_tags
        assert "gas" in unique_tags
        assert "transportation" in unique_tags
        assert "essentials" in unique_tags

    async def test_get_tag_usage_counts(self, db_session, test_user, test_account):
        """Test getting tag usage statistics."""
        trans_repo = TransactionRepository(db_session)
        tag_repo = TransactionTagRepository(db_session)

        # Create transactions and add tags
        # groceries: 3 times
        # food: 2 times
        # gas: 1 time
        transaction_tags = [
            ["groceries", "food"],
            ["groceries", "food"],
            ["groceries"],
            ["gas"],
        ]

        for tag_list in transaction_tags:
            transaction = Transaction(
                account_id=test_account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.00"),
                currency="USD",
                description="Transaction",
                transaction_type=TransactionType.DEBIT,
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            created_trans = await trans_repo.create(transaction)

            for tag in tag_list:
                await tag_repo.add_tag(created_trans.id, tag)

        # Get tag usage counts
        tag_counts = await tag_repo.get_tag_usage_counts(test_account.id)

        # Convert to dict for easier assertions
        tag_dict = {tag: count for tag, count in tag_counts}

        assert tag_dict["groceries"] == 3
        assert tag_dict["food"] == 2
        assert tag_dict["gas"] == 1

    async def test_exists(self, db_session, test_user, test_account):
        """Test checking if a tag exists on a transaction."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Transaction",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Add tag
        tag_repo = TransactionTagRepository(db_session)
        await tag_repo.add_tag(created_trans.id, "groceries")

        # Check existence
        assert await tag_repo.exists(created_trans.id, "groceries") is True
        assert await tag_repo.exists(created_trans.id, "nonexistent") is False

    async def test_duplicate_tag_prevention(self, db_session, test_user, test_account):
        """Test that duplicate tags are prevented by unique constraint."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Transaction",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Add tag
        tag_repo = TransactionTagRepository(db_session)
        await tag_repo.add_tag(created_trans.id, "groceries")
        await db_session.commit()  # Commit first tag

        # Try to add same tag again (should raise integrity error)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            await tag_repo.add_tag(created_trans.id, "groceries")
            await db_session.commit()  # Need to commit to trigger constraint

    async def test_tags_sorted_alphabetically(self, db_session, test_user, test_account):
        """Test that tags are returned sorted alphabetically."""
        # Create transaction
        trans_repo = TransactionRepository(db_session)
        transaction = Transaction(
            account_id=test_account.id,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            currency="USD",
            description="Transaction",
            transaction_type=TransactionType.DEBIT,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        created_trans = await trans_repo.create(transaction)

        # Add tags in random order
        tag_repo = TransactionTagRepository(db_session)
        await tag_repo.add_tag(created_trans.id, "zebra")
        await tag_repo.add_tag(created_trans.id, "apple")
        await tag_repo.add_tag(created_trans.id, "mango")

        # Get tags
        tags = await tag_repo.get_tags(created_trans.id)

        # Should be sorted alphabetically
        assert tags[0].tag == "apple"
        assert tags[1].tag == "mango"
        assert tags[2].tag == "zebra"
