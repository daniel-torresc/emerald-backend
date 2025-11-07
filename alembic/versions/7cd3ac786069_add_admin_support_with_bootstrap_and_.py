"""add admin support with bootstrap and indexes

Revision ID: 7cd3ac786069
Revises: 5ed7d2606ef9
Create Date: 2025-11-07 12:29:00.676500

This migration adds:
1. bootstrap_state table for tracking initial admin setup
2. Performance indexes for admin queries
3. Indexes for audit log filtering

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7cd3ac786069'
down_revision: Union[str, Sequence[str], None] = '5ed7d2606ef9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add admin support."""

    # Create bootstrap_state table
    op.create_table(
        'bootstrap_state',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('completed = TRUE', name='ck_bootstrap_state_completed'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create performance indexes for admin queries on users table
    # Partial index for admin users only (more efficient than full index)
    op.create_index(
        'ix_users_is_admin_true',
        'users',
        ['is_admin'],
        postgresql_where=sa.text('is_admin = TRUE'),
        unique=False
    )

    # Partial index for soft-deleted users
    op.create_index(
        'ix_users_deleted_at_not_null',
        'users',
        ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NOT NULL'),
        unique=False
    )

    # Note: audit_logs already has composite indexes defined in the model's __table_args__
    # No additional indexes needed for audit logs at this time


def downgrade() -> None:
    """Downgrade schema to remove admin support."""

    # Drop indexes for users
    op.drop_index('ix_users_deleted_at_not_null', table_name='users')
    op.drop_index('ix_users_is_admin_true', table_name='users')

    # Drop bootstrap_state table
    op.drop_table('bootstrap_state')
