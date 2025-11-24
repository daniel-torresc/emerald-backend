"""
Transaction tag repository for database operations.

This module provides database operations for TransactionTag model, including:
- Tag management (add, remove, list tags)
- Tag autocomplete (get unique tags for account)
- Tag usage statistics
"""

import uuid

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction import Transaction, TransactionTag
from src.repositories.base import BaseRepository


class TransactionTagRepository(BaseRepository[TransactionTag]):
    """
    Repository for TransactionTag model database operations.

    Provides tag-specific queries in addition to base CRUD operations.

    Features:
    - Add/remove tags from transactions
    - List tags for a transaction
    - Get unique tags for an account (autocomplete)
    - Tag usage statistics

    Usage:
        tag_repo = TransactionTagRepository(session)
        await tag_repo.add_tag(transaction_id, "groceries")
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize TransactionTag repository.

        Args:
            session: Async database session
        """
        super().__init__(TransactionTag, session)

    async def add_tag(self, transaction_id: uuid.UUID, tag: str) -> TransactionTag:
        """
        Add a tag to a transaction.

        Tags are normalized (lowercased and trimmed) before storage.
        Duplicate tags are prevented by unique constraint.

        Args:
            transaction_id: UUID of the transaction
            tag: Tag text (will be normalized)

        Returns:
            Created TransactionTag instance

        Raises:
            IntegrityError: If tag already exists on this transaction

        Example:
            tag = await tag_repo.add_tag(
                transaction_id=transaction.id,
                tag="Groceries"  # Stored as "groceries"
            )
        """
        normalized_tag = tag.lower().strip()

        tag_instance = TransactionTag(
            transaction_id=transaction_id,
            tag=normalized_tag,
        )

        self.session.add(tag_instance)
        await self.session.flush()
        await self.session.refresh(tag_instance)
        return tag_instance

    async def remove_tag(self, transaction_id: uuid.UUID, tag: str) -> bool:
        """
        Remove a tag from a transaction.

        Tags are normalized (lowercased and trimmed) before lookup.

        Args:
            transaction_id: UUID of the transaction
            tag: Tag text to remove (will be normalized)

        Returns:
            True if tag was removed, False if not found

        Example:
            removed = await tag_repo.remove_tag(transaction.id, "groceries")
            if not removed:
                raise NotFoundError("Tag not found on transaction")
        """
        normalized_tag = tag.lower().strip()

        query = select(TransactionTag).where(
            TransactionTag.transaction_id == transaction_id,
            TransactionTag.tag == normalized_tag,
        )

        result = await self.session.execute(query)
        tag_instance = result.scalar_one_or_none()

        if tag_instance is None:
            return False

        await self.session.delete(tag_instance)
        await self.session.flush()
        return True

    async def get_tags(self, transaction_id: uuid.UUID) -> list[TransactionTag]:
        """
        Get all tags for a transaction.

        Args:
            transaction_id: UUID of the transaction

        Returns:
            List of TransactionTag instances ordered by tag name

        Example:
            tags = await tag_repo.get_tags(transaction.id)
            tag_names = [tag.tag for tag in tags]
            print(f"Tags: {', '.join(tag_names)}")
        """
        query = (
            select(TransactionTag)
            .where(TransactionTag.transaction_id == transaction_id)
            .order_by(TransactionTag.tag)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_tags_for_account(
        self, account_id: uuid.UUID, limit: int = 100
    ) -> list[str]:
        """
        Get all unique tags used in an account (for autocomplete).

        Returns distinct tag names sorted alphabetically.
        Only includes tags from non-deleted transactions.

        Args:
            account_id: UUID of the account
            limit: Maximum number of tags to return (default 100)

        Returns:
            List of unique tag names (strings) sorted alphabetically

        Example:
            # Get tags for autocomplete dropdown
            tags = await tag_repo.get_all_tags_for_account(account.id)
            # Returns: ["business", "food", "groceries", "restaurant", "travel"]
        """
        query = (
            select(distinct(TransactionTag.tag))
            .select_from(TransactionTag)
            .join(Transaction, TransactionTag.transaction_id == Transaction.id)
            .where(
                Transaction.account_id == account_id, Transaction.deleted_at.is_(None)
            )
            .order_by(TransactionTag.tag)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_tag_usage_counts(
        self, account_id: uuid.UUID, limit: int = 50
    ) -> list[tuple[str, int]]:
        """
        Get tag usage statistics for an account.

        Returns tags with their usage counts, sorted by usage descending.
        Only includes tags from non-deleted transactions.

        Args:
            account_id: UUID of the account
            limit: Maximum number of tags to return (default 50)

        Returns:
            List of (tag_name, usage_count) tuples sorted by count descending

        Example:
            # Get most popular tags
            tag_stats = await tag_repo.get_tag_usage_counts(account.id, limit=10)
            for tag, count in tag_stats:
                print(f"{tag}: {count} transactions")

            # Example output:
            # groceries: 45 transactions
            # restaurant: 32 transactions
            # gas: 28 transactions
        """
        query = (
            select(TransactionTag.tag, func.count(TransactionTag.id).label("count"))
            .select_from(TransactionTag)
            .join(Transaction, TransactionTag.transaction_id == Transaction.id)
            .where(
                Transaction.account_id == account_id, Transaction.deleted_at.is_(None)
            )
            .group_by(TransactionTag.tag)
            .order_by(func.count(TransactionTag.id).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def exists(self, transaction_id: uuid.UUID, tag: str) -> bool:
        """
        Check if a tag exists on a transaction.

        Tags are normalized (lowercased and trimmed) before lookup.

        Args:
            transaction_id: UUID of the transaction
            tag: Tag text to check (will be normalized)

        Returns:
            True if tag exists, False otherwise

        Example:
            if await tag_repo.exists(transaction.id, "groceries"):
                print("Transaction is already tagged as groceries")
        """
        normalized_tag = tag.lower().strip()

        query = select(TransactionTag).where(
            TransactionTag.transaction_id == transaction_id,
            TransactionTag.tag == normalized_tag,
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
