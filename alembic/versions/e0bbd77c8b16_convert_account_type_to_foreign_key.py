"""convert account type to foreign key

Revision ID: e0bbd77c8b16
Revises: a2abdbb7e119
Create Date: 2025-12-01 22:24:42.775816

This migration:
1. Adds account_type_id UUID column (nullable initially)
2. Creates foreign key constraint to account_types.id
3. Creates index on account_type_id
4. Migrates data: enum value → account_type.key mapping
5. Makes account_type_id NOT NULL
6. Drops old account_type enum column
7. Drops AccountType enum type
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e0bbd77c8b16"
down_revision: Union[str, Sequence[str], None] = "a2abdbb7e119"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Step 1: Add account_type_id column (nullable initially for migration)
    op.add_column(
        "accounts",
        sa.Column(
            "account_type_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Foreign key to account_types table",
        ),
    )

    # Step 2: Create foreign key constraint (with ON DELETE RESTRICT)
    op.create_foreign_key(
        "fk_accounts_account_type_id",
        "accounts",
        "account_types",
        ["account_type_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Step 3: Create index on account_type_id for query performance
    op.create_index("ix_accounts_account_type_id", "accounts", ["account_type_id"])

    # Step 4: Migrate data - map enum values to account_types records
    # This SQL maps:
    #   'checking' → account_types where key='checking'
    #   'savings' → account_types where key='savings'
    #   'investment' → account_types where key='investment'
    #   'other' → account_types where key='other'
    op.execute("""
        UPDATE accounts
        SET account_type_id = (
            SELECT id
            FROM account_types
            WHERE key = accounts.account_type::text
            LIMIT 1
        )
        WHERE account_type_id IS NULL;
    """)

    # Step 5: Verify all accounts have account_type_id set
    # This will fail the migration if any accounts still have NULL
    op.execute("""
        DO $$
        DECLARE
            null_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO null_count
            FROM accounts
            WHERE account_type_id IS NULL;

            IF null_count > 0 THEN
                RAISE EXCEPTION 'Migration failed: % accounts have NULL account_type_id', null_count;
            END IF;
        END $$;
    """)

    # Step 6: Make account_type_id NOT NULL (now that all data is migrated)
    op.alter_column(
        "accounts",
        "account_type_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Step 7: Drop old account_type enum column
    op.drop_column("accounts", "account_type")

    # Step 8: Drop AccountType enum type from database
    # Note: This will fail if any other tables/columns use this enum
    op.execute("DROP TYPE IF EXISTS accounttype")


def downgrade() -> None:
    """Downgrade database schema (rollback)."""

    # Step 1: Recreate AccountType enum
    op.execute("""
        CREATE TYPE accounttype AS ENUM (
            'checking',
            'savings',
            'investment',
            'other'
        )
    """)

    # Step 2: Add account_type enum column (nullable initially)
    op.add_column(
        "accounts",
        sa.Column(
            "account_type",
            postgresql.ENUM(
                "checking", "savings", "investment", "other", name="accounttype"
            ),
            nullable=True,
        ),
    )

    # Step 3: Restore data - map account_type.key back to enum
    op.execute("""
        UPDATE accounts
        SET account_type = account_types.key::accounttype
        FROM account_types
        WHERE accounts.account_type_id = account_types.id;
    """)

    # Step 4: Make account_type NOT NULL
    op.alter_column(
        "accounts",
        "account_type",
        existing_type=postgresql.ENUM(
            "checking", "savings", "investment", "other", name="accounttype"
        ),
        nullable=False,
    )

    # Step 5: Drop account_type_id foreign key
    op.drop_constraint("fk_accounts_account_type_id", "accounts", type_="foreignkey")

    # Step 6: Drop account_type_id index
    op.drop_index("ix_accounts_account_type_id", "accounts")

    # Step 7: Drop account_type_id column
    op.drop_column("accounts", "account_type_id")
