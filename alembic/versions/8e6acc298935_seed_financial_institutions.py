"""seed financial institutions

Revision ID: 8e6acc298935
Revises: 411f995a959f
Create Date: 2025-11-27 22:04:41.319857

This migration seeds the financial_institutions table with initial institution data.

Initial seed includes:
- Santander (Spain)
- BBVA (Spain)

Additional institutions can be added via admin API or future migrations.

This migration is idempotent - it checks if institutions already exist before inserting.
"""

from typing import Sequence, Union
from datetime import datetime, UTC
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8e6acc298935"
down_revision: Union[str, Sequence[str], None] = "411f995a959f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Seed initial financial institutions.

    Seeds the database with 2 major Spanish banks to start.
    This migration is idempotent - safe to run multiple times.
    """
    # Create table reference
    financial_institutions = sa.table(
        "financial_institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(200)),
        sa.Column("short_name", sa.String(100)),
        sa.Column("swift_code", sa.String(11)),
        sa.Column("routing_number", sa.String(9)),
        sa.Column("country_code", sa.String(2)),
        sa.Column(
            "institution_type",
            postgresql.ENUM(name="institution_type", create_type=False),
        ),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("website_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # Define seed data
    now = datetime.now(UTC)
    seed_institutions = [
        {
            "id": uuid.uuid4(),
            "name": "Banco Santander, S.A.",
            "short_name": "Santander",
            "swift_code": "BSCHESMM",
            "routing_number": None,
            "country_code": "ES",
            "institution_type": "bank",
            "logo_url": "https://logo.clearbit.com/santander.com",
            "website_url": "https://www.santander.com",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid.uuid4(),
            "name": "Banco Bilbao Vizcaya Argentaria, S.A.",
            "short_name": "BBVA",
            "swift_code": "BBVAESMM",
            "routing_number": None,
            "country_code": "ES",
            "institution_type": "bank",
            "logo_url": "https://logo.clearbit.com/bbva.com",
            "website_url": "https://www.bbva.com",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    # Check if any institutions already exist (idempotent check)
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT COUNT(*) FROM financial_institutions"))
    count = result.scalar()

    # Only insert if table is empty
    if count == 0:
        op.bulk_insert(financial_institutions, seed_institutions)
        print(f"✅ Seeded {len(seed_institutions)} financial institutions")
    else:
        print(f"⏭️  Skipping seed - {count} institutions already exist")


def downgrade() -> None:
    """
    Remove seed data.

    Deletes the seeded institutions by SWIFT code.
    """
    # Delete seed institutions by SWIFT code
    op.execute(
        """
        DELETE FROM financial_institutions
        WHERE swift_code IN ('BSCHESMM', 'BBVAESMM')
        """
    )
