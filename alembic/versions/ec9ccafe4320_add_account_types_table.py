"""add account types table

Revision ID: ec9ccafe4320
Revises: 8e6acc298935
Create Date: 2025-11-28 19:40:00.000000

This migration creates the account_types table for master data management.

Table: account_types
- Centralized repository of account types (checking, savings, investment, HSA, 401k, etc.)
- Used by accounts to categorize financial accounts
- Administrator-managed, globally available to all users
- Uses is_active flag instead of soft delete

Columns:
- id: UUID primary key
- key: Unique identifier for programmatic use (VARCHAR 50, required, unique)
- name: Display name shown to users (VARCHAR 100, required)
- description: Detailed description (VARCHAR 500, optional)
- icon_url: URL to icon image (VARCHAR 500, optional)
- is_active: Whether type is available for selection (BOOLEAN, default TRUE)
- sort_order: Controls display order (INTEGER, default 0)
- created_at: Creation timestamp
- updated_at: Last update timestamp

Indexes:
- Primary key on id
- Unique index on key (from unique constraint)
- is_active (for filtering)
- sort_order (for ordering)

Constraints:
- key must be unique globally
- key must match pattern ^[a-z0-9_]+$ (lowercase, alphanumeric, underscore only)

Seed Data:
- 4 default account types: checking, savings, investment, other
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "ec9ccafe4320"
down_revision: Union[str, Sequence[str], None] = "8e6acc298935"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create account_types table with seed data.

    Creates master data table for account types with all required
    columns, indexes, constraints, and 4 default seed types.
    """
    # Create account_types table
    op.create_table(
        "account_types",
        # Identification fields
        sa.Column(
            "key",
            sa.String(length=50),
            nullable=False,
            comment="Unique identifier for programmatic use (lowercase, alphanumeric, underscore)",
        ),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
            comment="Display name shown to users",
        ),
        sa.Column(
            "description",
            sa.String(length=500),
            nullable=True,
            comment="Detailed description of the account type",
        ),
        # Visual identity
        sa.Column(
            "icon_url",
            sa.String(length=500),
            nullable=True,
            comment="URL to icon image for UI display",
        ),
        # Status and ordering
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
            comment="Whether the type is available for selection",
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Integer for controlling display order (lower numbers appear first)",
        ),
        # Standard fields (id, timestamps)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Primary key
        sa.PrimaryKeyConstraint("id", name=op.f("pk_account_types")),
        # Unique constraint on key
        sa.UniqueConstraint("key", name=op.f("uq_account_types_key")),
        # Check constraint for key format (lowercase, alphanumeric, underscore only)
        sa.CheckConstraint(
            "key ~ '^[a-z0-9_]+$'", name=op.f("ck_account_types_key_format")
        ),
    )

    # Create indexes
    op.create_index(
        op.f("ix_account_types_is_active"), "account_types", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_account_types_sort_order"),
        "account_types",
        ["sort_order"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_types_created_at"),
        "account_types",
        ["created_at"],
        unique=False,
    )

    # Seed default account types (idempotent)
    op.execute("""
        INSERT INTO account_types (key, name, description, is_active, sort_order, created_at, updated_at)
        VALUES
            ('checking', 'Checking Account',
             'Standard checking account for daily transactions and bill payments',
             true, 1, NOW(), NOW()),
            ('savings', 'Savings Account',
             'Savings account for building emergency funds and long-term savings',
             true, 2, NOW(), NOW()),
            ('investment', 'Investment Account',
             'Investment and brokerage accounts for stocks, bonds, and mutual funds',
             true, 3, NOW(), NOW()),
            ('other', 'Other',
             'Other financial accounts not covered by standard types',
             true, 99, NOW(), NOW())
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    """
    Drop account_types table.
    """
    # Drop indexes
    op.drop_index(op.f("ix_account_types_created_at"), table_name="account_types")
    op.drop_index(op.f("ix_account_types_sort_order"), table_name="account_types")
    op.drop_index(op.f("ix_account_types_is_active"), table_name="account_types")

    # Drop table (cascades to seed data)
    op.drop_table("account_types")
