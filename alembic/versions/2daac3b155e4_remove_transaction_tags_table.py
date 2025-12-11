"""remove transaction tags table

Revision ID: 2daac3b155e4
Revises: ab7237ea9da7
Create Date: 2025-12-11 13:27:54.090462

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2daac3b155e4"
down_revision: Union[str, Sequence[str], None] = "ab7237ea9da7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop transaction_tags table."""
    # Drop transaction_tags table (CASCADE handles foreign keys automatically)
    op.drop_table("transaction_tags")


def downgrade() -> None:
    """Recreate transaction_tags table for rollback capability."""
    # Recreate transaction_tags table with full structure
    op.create_table(
        "transaction_tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transaction_tags"),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_transaction_tags_transaction_id_transactions",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "transaction_id", "tag", name="uq_transaction_tags_transaction_tag"
        ),
    )
    # Recreate indexes
    op.create_index(
        "ix_transaction_tags_transaction_id",
        "transaction_tags",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_transaction_tags_tag", "transaction_tags", ["tag"], unique=False
    )
