"""create_enums_and_extensions

Revision ID: 9cfdc3051d85
Revises:
Create Date: 2025-11-14 14:22:28.202178

This migration creates all PostgreSQL enums and extensions required by the Emerald Finance Platform.

Enums:
- audit_action_enum: Audit action types
- audit_status_enum: Audit status values
- accounttype: Account classification
- permissionlevel: Permission levels for sharing
- transactiontype: Transaction types

Extensions:
- pg_trgm: Trigram fuzzy search support

===============================================================================
ENUM EVOLUTION GUIDE
===============================================================================

PostgreSQL ENUMs cannot be modified directly within a transaction, which makes
them tricky to evolve. Here are the recommended approaches:

1. ADDING A NEW VALUE (Recommended for most cases)
   ------------------------------------------------
   Use ALTER TYPE ... ADD VALUE outside of a transaction:

   ```python
   def upgrade():
       # Use op.execute() with explicit connection
       with op.get_context().autocommit_block():
           op.execute("ALTER TYPE transactiontype ADD VALUE 'REFUND'")
   ```

   Note: New values are always added at the end. You cannot specify position
   within a transaction.

2. REMOVING A VALUE (Complex - requires recreation)
   --------------------------------------------------
   PostgreSQL doesn't support removing enum values. You must:

   a) Create a new enum with desired values:
   ```python
   def upgrade():
       # Create new enum
       op.execute("CREATE TYPE transactiontype_new AS ENUM ('DEBIT', 'CREDIT', 'TRANSFER')")

       # Update all columns to use new enum (with casting)
       op.execute('''
           ALTER TABLE transactions
           ALTER COLUMN transaction_type TYPE transactiontype_new
           USING transaction_type::text::transactiontype_new
       ''')

       # Drop old enum and rename new one
       op.execute('DROP TYPE transactiontype')
       op.execute('ALTER TYPE transactiontype_new RENAME TO transactiontype')
   ```

   b) In downgrade, reverse the process

3. RENAMING A VALUE (Complex - requires column updates)
   -----------------------------------------------------
   ```python
   def upgrade():
       # Update all existing values first
       op.execute("UPDATE transactions SET transaction_type = 'NEW_NAME' WHERE transaction_type = 'OLD_NAME'")

       # Then recreate the enum (see approach #2)
   ```

4. BEST PRACTICES
   ----------------
   - Always create enums explicitly BEFORE tables (as done in this migration)
   - Use checkfirst=True to avoid duplicate creation errors
   - Use create_type=False when referencing existing enums in columns
   - Document enum values in docstrings
   - Consider using VARCHAR with CHECK constraints for frequently-changing types
   - For complex enum evolution, test thoroughly on a copy of production data

===============================================================================
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9cfdc3051d85"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create PostgreSQL extensions and enum types.

    This migration creates:
    1. pg_trgm extension for trigram-based fuzzy text search
    2. All enum types used throughout the schema
    """
    # =========================================================================
    # STEP 1: Install PostgreSQL Extensions
    # =========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # =========================================================================
    # STEP 2: Create Enums (explicitly, before tables)
    # =========================================================================
    # Create all enum types first to ensure they exist before table creation
    # Using checkfirst=True to avoid duplicate creation errors
    audit_action_enum = postgresql.ENUM(
        "LOGIN",
        "LOGOUT",
        "LOGIN_FAILED",
        "PASSWORD_CHANGE",
        "TOKEN_REFRESH",
        "CREATE",
        "READ",
        "UPDATE",
        "DELETE",
        "PERMISSION_GRANT",
        "PERMISSION_REVOKE",
        "ACCOUNT_ACTIVATE",
        "ACCOUNT_DEACTIVATE",
        "ACCOUNT_LOCK",
        "ACCOUNT_UNLOCK",
        "RATE_LIMIT_EXCEEDED",
        "INVALID_TOKEN",
        "PERMISSION_DENIED",
        "SPLIT_TRANSACTION",
        "JOIN_TRANSACTION",
        name="audit_action_enum",
    )
    audit_status_enum = postgresql.ENUM(
        "SUCCESS", "FAILURE", "PARTIAL", name="audit_status_enum"
    )
    # UPDATED: Changed to match new business requirements for metadata endpoints
    # AccountType: checking, savings, investment, other (removed credit_card, debit_card, loan)
    # TransactionType: income, expense, transfer (removed debit, credit, fee, interest, other)
    accounttype_enum = postgresql.ENUM(
        "checking", "savings", "investment", "other", name="accounttype"
    )
    permissionlevel_enum = postgresql.ENUM(
        "owner", "editor", "viewer", name="permissionlevel"
    )
    transactiontype_enum = postgresql.ENUM(
        "income", "expense", "transfer", name="transactiontype"
    )

    audit_action_enum.create(op.get_bind(), checkfirst=True)
    audit_status_enum.create(op.get_bind(), checkfirst=True)
    accounttype_enum.create(op.get_bind(), checkfirst=True)
    permissionlevel_enum.create(op.get_bind(), checkfirst=True)
    transactiontype_enum.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """
    Drop all enum types and PostgreSQL extensions.
    """
    # =========================================================================
    # STEP 1: Drop enum types explicitly
    # =========================================================================
    transactiontype_enum = postgresql.ENUM(name="transactiontype")
    permissionlevel_enum = postgresql.ENUM(name="permissionlevel")
    accounttype_enum = postgresql.ENUM(name="accounttype")
    audit_status_enum = postgresql.ENUM(name="audit_status_enum")
    audit_action_enum = postgresql.ENUM(name="audit_action_enum")

    transactiontype_enum.drop(op.get_bind(), checkfirst=True)
    permissionlevel_enum.drop(op.get_bind(), checkfirst=True)
    accounttype_enum.drop(op.get_bind(), checkfirst=True)
    audit_status_enum.drop(op.get_bind(), checkfirst=True)
    audit_action_enum.drop(op.get_bind(), checkfirst=True)

    # =========================================================================
    # STEP 2: Drop PostgreSQL extension
    # =========================================================================
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
