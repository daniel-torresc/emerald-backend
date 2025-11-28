"""add institution type enum

Revision ID: 42098b69a0a9
Revises: 4aabd1426c98
Create Date: 2025-11-27 22:02:33.330987

This migration creates the institution_type enum for categorizing financial institutions.

Enum Values:
- bank: Traditional banks (commercial, retail, universal banks)
- credit_union: Credit unions and cooperative banks
- brokerage: Investment firms and brokerage houses
- fintech: Financial technology companies
- other: Other financial institutions

This enum is used by the financial_institutions table to classify institutions
for filtering and reporting purposes.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '42098b69a0a9'
down_revision: Union[str, Sequence[str], None] = '4aabd1426c98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create institution_type enum.

    This enum categorizes financial institutions into 5 types:
    bank, credit_union, brokerage, fintech, other.
    """
    # Create institution_type enum
    institution_type_enum = postgresql.ENUM(
        "bank",
        "credit_union",
        "brokerage",
        "fintech",
        "other",
        name="institution_type",
    )
    institution_type_enum.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """
    Drop institution_type enum.
    """
    # Drop institution_type enum
    institution_type_enum = postgresql.ENUM(name="institution_type")
    institution_type_enum.drop(op.get_bind(), checkfirst=True)
