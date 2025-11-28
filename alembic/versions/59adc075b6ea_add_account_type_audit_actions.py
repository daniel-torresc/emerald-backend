"""add account type audit actions

Revision ID: 59adc075b6ea
Revises: ec9ccafe4320
Create Date: 2025-11-28 19:42:32.108023

This migration adds new audit action enum values for account type operations:
- CREATE_ACCOUNT_TYPE
- UPDATE_ACCOUNT_TYPE
- DEACTIVATE_ACCOUNT_TYPE

These actions enable comprehensive audit logging for account type master data management.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "59adc075b6ea"
down_revision: Union[str, Sequence[str], None] = "ec9ccafe4320"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add account type audit action enum values.

    PostgreSQL enum values must be added outside of a transaction,
    so we use an autocommit block.
    """
    # Add new audit action enum values (outside transaction)
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE audit_action_enum ADD VALUE IF NOT EXISTS 'CREATE_ACCOUNT_TYPE'"
        )
        op.execute(
            "ALTER TYPE audit_action_enum ADD VALUE IF NOT EXISTS 'UPDATE_ACCOUNT_TYPE'"
        )
        op.execute(
            "ALTER TYPE audit_action_enum ADD VALUE IF NOT EXISTS 'DEACTIVATE_ACCOUNT_TYPE'"
        )


def downgrade() -> None:
    """
    PostgreSQL does not support removing enum values.

    To downgrade, you would need to:
    1. Ensure no audit_logs use these values
    2. Recreate the entire enum without these values
    3. Update all columns using the enum

    This is complex and risky, so we leave the enum values in place.
    They won't cause issues if account types feature is not used.
    """
    # No downgrade - PostgreSQL doesn't support removing enum values
    # The values remain but won't be used if account types feature is not active
    pass
