"""link accounts to financial institutions

Revision ID: a2abdbb7e119
Revises: 59adc075b6ea
Create Date: 2025-12-01 20:56:21.011466

CRITICAL: This is a destructive migration that deletes all existing accounts.
This is ONLY safe because there is no production data. In production, a data
migration strategy would be required to map bank_name to institution_id.

Changes:
1. Delete all existing accounts (development data only - clean slate)
2. Add financial_institution_id column (UUID NOT NULL)
3. Add foreign key constraint to financial_institutions (ON DELETE RESTRICT)
4. Add index on financial_institution_id for query performance
5. Remove bank_name column (replaced by FK to institutions table)

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a2abdbb7e119"
down_revision: Union[str, Sequence[str], None] = "59adc075b6ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Link accounts to financial institutions.

    WARNING: This migration deletes all existing accounts. Only safe in development.
    """
    # Step 1: Clean slate - delete all existing test data
    # This is ONLY safe because there is no production data
    op.execute("DELETE FROM accounts")

    # Step 2: Add new financial_institution_id column (NOT NULL from start)
    op.add_column(
        "accounts",
        sa.Column(
            "financial_institution_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Financial institution this account belongs to (mandatory)",
        ),
    )

    # Step 3: Add foreign key constraint with ON DELETE RESTRICT
    # RESTRICT prevents deleting institutions that have linked accounts
    op.create_foreign_key(
        "fk_accounts_financial_institution",
        "accounts",
        "financial_institutions",
        ["financial_institution_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Step 4: Add index for query performance
    op.create_index(
        "idx_accounts_financial_institution_id",
        "accounts",
        ["financial_institution_id"],
    )

    # Step 5: Remove old bank_name column (replaced by FK)
    op.drop_column("accounts", "bank_name")


def downgrade() -> None:
    """
    Downgrade schema: Restore bank_name field.

    NOTE: This will lose institution references. Use with caution.
    """
    # Reverse Step 5: Re-add bank_name column
    op.add_column(
        "accounts",
        sa.Column(
            "bank_name",
            sa.String(100),
            nullable=True,
            comment="Name of the financial institution",
        ),
    )

    # Reverse Step 4: Drop index
    op.drop_index("idx_accounts_financial_institution_id", table_name="accounts")

    # Reverse Step 3: Drop foreign key
    op.drop_constraint(
        "fk_accounts_financial_institution", "accounts", type_="foreignkey"
    )

    # Reverse Step 2: Drop financial_institution_id column
    op.drop_column("accounts", "financial_institution_id")
