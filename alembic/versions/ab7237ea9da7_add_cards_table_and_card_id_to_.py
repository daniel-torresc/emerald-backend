"""add cards table and card_id to transactions

Revision ID: ab7237ea9da7
Revises: e0bbd77c8b16
Create Date: 2025-12-09 11:49:30.904991

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ab7237ea9da7"
down_revision: Union[str, Sequence[str], None] = "e0bbd77c8b16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create card_type enum (only if it doesn't exist)
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'card_type'"))
    if not result.scalar():
        conn.execute(
            sa.text("CREATE TYPE card_type AS ENUM ('credit_card', 'debit_card')")
        )

    # Create cards table
    op.create_table(
        "cards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "financial_institution_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "card_type",
            postgresql.ENUM(
                "credit_card", "debit_card", name="card_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("last_four_digits", sa.String(length=4), nullable=True),
        sa.Column("card_network", sa.String(length=50), nullable=True),
        sa.Column("expiry_month", sa.Integer(), nullable=True),
        sa.Column("expiry_year", sa.Integer(), nullable=True),
        sa.Column("credit_limit", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cards")),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("fk_cards_account_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["financial_institution_id"],
            ["financial_institutions.id"],
            name=op.f("fk_cards_financial_institution_id_financial_institutions"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "(expiry_month IS NULL) OR (expiry_month >= 1 AND expiry_month <= 12)",
            name=op.f("ck_cards_expiry_month_range"),
        ),
        sa.CheckConstraint(
            "(last_four_digits IS NULL) OR (last_four_digits ~ '^[0-9]{4}$')",
            name=op.f("ck_cards_last_four_digits_format"),
        ),
        sa.CheckConstraint(
            "(credit_limit IS NULL) OR (credit_limit > 0)",
            name=op.f("ck_cards_credit_limit_positive"),
        ),
    )

    # Create indexes for cards table
    op.create_index(op.f("ix_cards_account_id"), "cards", ["account_id"], unique=False)
    op.create_index(
        op.f("ix_cards_financial_institution_id"),
        "cards",
        ["financial_institution_id"],
        unique=False,
    )
    op.create_index(op.f("ix_cards_card_type"), "cards", ["card_type"], unique=False)
    op.create_index(op.f("ix_cards_deleted_at"), "cards", ["deleted_at"], unique=False)

    # Add card_id column to transactions table
    op.add_column(
        "transactions",
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_transactions_card_id_cards"),
        "transactions",
        "cards",
        ["card_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_transactions_card_id"), "transactions", ["card_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove card_id from transactions
    op.drop_index(op.f("ix_transactions_card_id"), table_name="transactions")
    op.drop_constraint(
        op.f("fk_transactions_card_id_cards"), "transactions", type_="foreignkey"
    )
    op.drop_column("transactions", "card_id")

    # Drop cards table indexes
    op.drop_index(op.f("ix_cards_deleted_at"), table_name="cards")
    op.drop_index(op.f("ix_cards_card_type"), table_name="cards")
    op.drop_index(op.f("ix_cards_financial_institution_id"), table_name="cards")
    op.drop_index(op.f("ix_cards_account_id"), table_name="cards")

    # Drop cards table
    op.drop_table("cards")

    # Drop card_type enum (only if it exists)
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'card_type'"))
    if result.scalar():
        conn.execute(sa.text("DROP TYPE card_type"))
