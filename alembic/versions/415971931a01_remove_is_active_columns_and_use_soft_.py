"""remove is_active columns and use soft delete consistently

Revision ID: 415971931a01
Revises: 2daac3b155e4
Create Date: 2025-12-11 17:33:45.068130

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "415971931a01"
down_revision: Union[str, Sequence[str], None] = "2daac3b155e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop is_active column and index from account_types
    op.drop_index(op.f("ix_account_types_is_active"), table_name="account_types")
    op.drop_column("account_types", "is_active")

    # Drop is_active column and index from accounts
    op.drop_index(op.f("ix_accounts_is_active"), table_name="accounts")
    op.drop_column("accounts", "is_active")

    # Add deleted_at column and index to financial_institutions, drop is_active
    op.add_column(
        "financial_institutions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_financial_institutions_deleted_at"),
        "financial_institutions",
        ["deleted_at"],
        unique=False,
    )
    op.drop_index(
        op.f("ix_financial_institutions_is_active"), table_name="financial_institutions"
    )
    op.drop_column("financial_institutions", "is_active")

    # Drop is_active column and index from users
    op.drop_index(op.f("ix_users_is_active"), table_name="users")
    op.drop_column("users", "is_active")


def downgrade() -> None:
    """Downgrade schema."""
    # Restore is_active column and index to users
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_users_is_active"), "users", ["is_active"], unique=False)

    # Restore is_active column and index to financial_institutions, remove deleted_at
    op.add_column(
        "financial_institutions",
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
            comment="Whether the institution is operational",
        ),
    )
    op.create_index(
        op.f("ix_financial_institutions_is_active"),
        "financial_institutions",
        ["is_active"],
        unique=False,
    )
    op.drop_index(
        op.f("ix_financial_institutions_deleted_at"),
        table_name="financial_institutions",
    )
    op.drop_column("financial_institutions", "deleted_at")

    # Restore is_active column and index to accounts
    op.add_column(
        "accounts",
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_accounts_is_active"), "accounts", ["is_active"], unique=False
    )

    # Restore is_active column and index to account_types
    op.add_column(
        "account_types",
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
            comment="Whether the type is available for selection",
        ),
    )
    op.create_index(
        op.f("ix_account_types_is_active"), "account_types", ["is_active"], unique=False
    )
