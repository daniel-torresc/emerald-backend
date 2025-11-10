"""create transactions and transaction_tags tables

Revision ID: 1d78ffc27a9c
Revises: 7cd3ac786069
Create Date: 2025-11-08 18:29:03.263823

This migration implements Phase 3: Transaction Management System

Creates:
1. pg_trgm extension for fuzzy text search
2. transactiontype enum for transaction types
3. transactions table for financial transactions
4. transaction_tags table for transaction categorization
5. Performance indexes for queries and searches
6. Composite indexes for common query patterns
7. GIN indexes for fuzzy search on merchant and description
8. Unique constraints for data integrity
9. Foreign key constraints with proper cascades
10. Check constraints for data validation

Phase 3 enables:
- Full CRUD operations on transactions
- Transaction splitting for shared expenses
- Free-form tags for flexible categorization
- Fuzzy search on merchant and description (handles typos)
- Real-time balance calculations
- Complete audit trail for compliance
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1d78ffc27a9c'
down_revision: Union[str, Sequence[str], None] = '7cd3ac786069'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Creates transaction management tables and indexes for Phase 3.
    """
    # Install pg_trgm extension for fuzzy text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Add new audit action types for transaction operations
    op.execute("ALTER TYPE audit_action_enum ADD VALUE IF NOT EXISTS 'SPLIT_TRANSACTION'")
    op.execute("ALTER TYPE audit_action_enum ADD VALUE IF NOT EXISTS 'JOIN_TRANSACTION'")

    # Create TransactionType enum (check if exists first)
    transaction_type_enum = postgresql.ENUM(
        'debit', 'credit', 'transfer', 'fee', 'interest', 'other',
        name='transactiontype',
        create_type=False,
    )
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    # Create transactions table
    op.create_table(
        'transactions',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Foreign Keys
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),

        # Transaction Data
        sa.Column('transaction_date', sa.Date, nullable=False),
        sa.Column('value_date', sa.Date, nullable=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('merchant', sa.String(100), nullable=True),
        sa.Column('transaction_type', transaction_type_enum, nullable=False),
        sa.Column('user_notes', sa.Text, nullable=True),

        # Timestamps (from TimestampMixin)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Soft Delete (from SoftDeleteMixin)
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),

        # Audit Fields (from AuditFieldsMixin)
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Constraints
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_transactions_currency_format'),
        sa.CheckConstraint("amount != 0", name='ck_transactions_amount_nonzero'),
    )

    # Create transaction_tags table
    op.create_table(
        'transaction_tags',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Foreign Key
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),

        # Tag Data
        sa.Column('tag', sa.String(50), nullable=False),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('transaction_id', 'tag', name='uq_transaction_tags_transaction_tag'),
    )

    # Create indexes for transactions table
    op.create_index('ix_transactions_account_id', 'transactions', ['account_id'])
    op.create_index('ix_transactions_transaction_date', 'transactions', ['transaction_date'])
    op.create_index('ix_transactions_transaction_type', 'transactions', ['transaction_type'])
    op.create_index('ix_transactions_deleted_at', 'transactions', ['deleted_at'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])
    op.create_index('ix_transactions_created_by', 'transactions', ['created_by'])
    op.create_index('ix_transactions_updated_by', 'transactions', ['updated_by'])

    # Partial index for split transactions (only index when parent_transaction_id is NOT NULL)
    op.create_index(
        'ix_transactions_parent_transaction_id',
        'transactions',
        ['parent_transaction_id'],
        postgresql_where=sa.text('parent_transaction_id IS NOT NULL'),
    )

    # Composite index for common queries (account + date range)
    op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'transaction_date'])

    # Composite index for soft delete queries (account + deleted_at for balance calculations)
    op.create_index('ix_transactions_account_deleted', 'transactions', ['account_id', 'deleted_at'])

    # GIN indexes for trigram fuzzy search
    op.execute("CREATE INDEX ix_transactions_merchant_trgm ON transactions USING GIN (merchant gin_trgm_ops)")
    op.execute("CREATE INDEX ix_transactions_description_trgm ON transactions USING GIN (description gin_trgm_ops)")

    # Create indexes for transaction_tags table
    op.create_index('ix_transaction_tags_transaction_id', 'transaction_tags', ['transaction_id'])
    op.create_index('ix_transaction_tags_tag', 'transaction_tags', ['tag'])
    op.create_index('ix_transaction_tags_created_at', 'transaction_tags', ['created_at'])


def downgrade() -> None:
    """
    Downgrade schema.

    Removes transaction management tables and extensions.
    """
    # Drop tables (cascades will handle foreign keys)
    op.drop_table('transaction_tags')
    op.drop_table('transactions')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS transactiontype')

    # Note: We don't drop pg_trgm extension as it might be used elsewhere
    # If needed, manually drop with: DROP EXTENSION IF EXISTS pg_trgm
