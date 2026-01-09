"""update transaction model fields

Revision ID: a1b2c3d4e5f6
Revises: 415971931a01
Create Date: 2026-01-09

Changes:
- Rename description -> original_description
- Add user_description column
- Rename user_notes -> comments
- Create transactionreviewstatus enum
- Add review_status column with default
- Add index on review_status
- Drop transaction_type column and index
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "415971931a01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # 1. Rename description -> original_description
    op.alter_column(
        "transactions",
        "description",
        new_column_name="original_description",
    )

    # 2. Add user_description column
    op.add_column(
        "transactions",
        sa.Column("user_description", sa.String(500), nullable=True),
    )

    # 3. Copy original_description to user_description for existing data
    conn.execute(
        sa.text("UPDATE transactions SET user_description = original_description")
    )

    # 4. Rename user_notes -> comments
    op.alter_column(
        "transactions",
        "user_notes",
        new_column_name="comments",
    )

    # 5. Create transactionreviewstatus enum (if not exists)
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'transactionreviewstatus'")
    )
    if not result.scalar():
        conn.execute(
            sa.text(
                "CREATE TYPE transactionreviewstatus AS ENUM ('to_review', 'reviewed')"
            )
        )

    # 6. Add review_status column
    op.add_column(
        "transactions",
        sa.Column(
            "review_status",
            postgresql.ENUM(
                "to_review",
                "reviewed",
                name="transactionreviewstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="to_review",
        ),
    )

    # 7. Add index on review_status
    op.create_index(
        op.f("ix_transactions_review_status"),
        "transactions",
        ["review_status"],
        unique=False,
    )

    # 8. Drop transaction_type index first
    op.drop_index(
        op.f("ix_transactions_transaction_type"),
        table_name="transactions",
    )

    # 9. Drop transaction_type column
    op.drop_column("transactions", "transaction_type")


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    # 1. Re-add transaction_type column with default
    op.add_column(
        "transactions",
        sa.Column(
            "transaction_type",
            postgresql.ENUM(
                "income",
                "expense",
                "transfer",
                name="transactiontype",
                create_type=False,
            ),
            nullable=False,
            server_default="expense",
        ),
    )

    # 2. Re-create transaction_type index
    op.create_index(
        op.f("ix_transactions_transaction_type"),
        "transactions",
        ["transaction_type"],
        unique=False,
    )

    # 3. Drop review_status index
    op.drop_index(
        op.f("ix_transactions_review_status"),
        table_name="transactions",
    )

    # 4. Drop review_status column
    op.drop_column("transactions", "review_status")

    # 5. Drop transactionreviewstatus enum
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'transactionreviewstatus'")
    )
    if result.scalar():
        conn.execute(sa.text("DROP TYPE transactionreviewstatus"))

    # 6. Rename comments -> user_notes
    op.alter_column(
        "transactions",
        "comments",
        new_column_name="user_notes",
    )

    # 7. Drop user_description column
    op.drop_column("transactions", "user_description")

    # 8. Rename original_description -> description
    op.alter_column(
        "transactions",
        "original_description",
        new_column_name="description",
    )
