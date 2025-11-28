"""create financial institutions table

Revision ID: 411f995a959f
Revises: 42098b69a0a9
Create Date: 2025-11-27 22:03:58.123456

This migration creates the financial_institutions table for master data management.

Table: financial_institutions
- Centralized repository of financial institutions (banks, credit unions, brokerages, fintech)
- Used by accounts to link to standardized institution data
- Supports SWIFT codes (international) and routing numbers (US)
- Uses is_active flag instead of soft delete

Columns:
- id: UUID primary key
- name: Official legal name (VARCHAR 200, required)
- short_name: Common/display name (VARCHAR 100, required)
- swift_code: BIC/SWIFT code (VARCHAR 11, optional, unique if provided)
- routing_number: ABA routing number (VARCHAR 9, optional, unique if provided)
- country_code: ISO 3166-1 alpha-2 code (VARCHAR 2, required)
- institution_type: Enum (bank, credit_union, brokerage, fintech, other)
- logo_url: URL to logo (VARCHAR 500, optional)
- website_url: Official website (VARCHAR 500, optional)
- is_active: Operational status (BOOLEAN, default TRUE)
- created_at: Creation timestamp
- updated_at: Last update timestamp

Indexes:
- Primary key on id
- name (for searching)
- short_name (for searching)
- Partial unique index on swift_code (WHERE swift_code IS NOT NULL)
- Partial unique index on routing_number (WHERE routing_number IS NOT NULL)
- country_code (for filtering)
- institution_type (for filtering)
- is_active (for filtering)

Constraints:
- country_code must be exactly 2 characters
- routing_number must be exactly 9 characters (if provided)
- swift_code must be 8 or 11 characters (if provided)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '411f995a959f'
down_revision: Union[str, Sequence[str], None] = '42098b69a0a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create financial_institutions table.

    Creates master data table for financial institutions with all required
    columns, indexes, and constraints.
    """
    # Create financial_institutions table
    op.create_table(
        "financial_institutions",
        # Identification fields
        sa.Column("name", sa.String(length=200), nullable=False, comment="Official legal name of the institution"),
        sa.Column("short_name", sa.String(length=100), nullable=False, comment="Common/display name used in UI"),

        # Banking identifiers
        sa.Column("swift_code", sa.String(length=11), nullable=True, comment="BIC/SWIFT code (8 or 11 alphanumeric characters)"),
        sa.Column("routing_number", sa.String(length=9), nullable=True, comment="ABA routing number for US banks (9 digits)"),

        # Geographic information
        sa.Column("country_code", sa.String(length=2), nullable=False, comment="ISO 3166-1 alpha-2 country code (e.g., US, GB, DE)"),

        # Institution classification
        sa.Column(
            "institution_type",
            postgresql.ENUM(name="institution_type", create_type=False),
            nullable=False,
            comment="Type of financial institution"
        ),

        # Metadata
        sa.Column("logo_url", sa.String(length=500), nullable=True, comment="URL to institution's logo image"),
        sa.Column("website_url", sa.String(length=500), nullable=True, comment="Official website URL"),

        # Status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
            comment="Whether the institution is operational"
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_financial_institutions")),

        # Check constraints
        sa.CheckConstraint(
            "LENGTH(country_code) = 2",
            name=op.f("ck_financial_institutions_country_code_length")
        ),
        sa.CheckConstraint(
            "routing_number IS NULL OR LENGTH(routing_number) = 9",
            name=op.f("ck_financial_institutions_routing_number_length")
        ),
        sa.CheckConstraint(
            "swift_code IS NULL OR LENGTH(swift_code) IN (8, 11)",
            name=op.f("ck_financial_institutions_swift_code_length")
        ),
    )

    # Create standard indexes
    op.create_index(
        op.f("ix_financial_institutions_name"),
        "financial_institutions",
        ["name"],
        unique=False
    )
    op.create_index(
        op.f("ix_financial_institutions_short_name"),
        "financial_institutions",
        ["short_name"],
        unique=False
    )
    op.create_index(
        op.f("ix_financial_institutions_country_code"),
        "financial_institutions",
        ["country_code"],
        unique=False
    )
    op.create_index(
        op.f("ix_financial_institutions_institution_type"),
        "financial_institutions",
        ["institution_type"],
        unique=False
    )
    op.create_index(
        op.f("ix_financial_institutions_is_active"),
        "financial_institutions",
        ["is_active"],
        unique=False
    )
    op.create_index(
        op.f("ix_financial_institutions_created_at"),
        "financial_institutions",
        ["created_at"],
        unique=False
    )

    # Create partial unique indexes (uniqueness only for non-NULL values)
    # SWIFT code must be unique if provided
    op.create_index(
        "ix_financial_institutions_swift_code_unique",
        "financial_institutions",
        ["swift_code"],
        unique=True,
        postgresql_where=sa.text("swift_code IS NOT NULL")
    )

    # Routing number must be unique if provided
    op.create_index(
        "ix_financial_institutions_routing_number_unique",
        "financial_institutions",
        ["routing_number"],
        unique=True,
        postgresql_where=sa.text("routing_number IS NOT NULL")
    )


def downgrade() -> None:
    """
    Drop financial_institutions table.
    """
    # Drop all indexes
    op.drop_index(
        "ix_financial_institutions_routing_number_unique",
        table_name="financial_institutions"
    )
    op.drop_index(
        "ix_financial_institutions_swift_code_unique",
        table_name="financial_institutions"
    )
    op.drop_index(
        op.f("ix_financial_institutions_created_at"),
        table_name="financial_institutions"
    )
    op.drop_index(
        op.f("ix_financial_institutions_is_active"),
        table_name="financial_institutions"
    )
    op.drop_index(
        op.f("ix_financial_institutions_institution_type"),
        table_name="financial_institutions"
    )
    op.drop_index(
        op.f("ix_financial_institutions_country_code"),
        table_name="financial_institutions"
    )
    op.drop_index(
        op.f("ix_financial_institutions_short_name"),
        table_name="financial_institutions"
    )
    op.drop_index(
        op.f("ix_financial_institutions_name"),
        table_name="financial_institutions"
    )

    # Drop table
    op.drop_table("financial_institutions")
