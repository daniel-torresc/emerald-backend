# Implementation Plan: Merge Alembic Migrations into Single Initial Schema

## Executive Summary

This plan outlines the process of consolidating four separate Alembic migration files into a single "initial schema" migration for the Emerald Finance Platform. The application is in early development with no production users, making this an ideal time to simplify the migration history.

### Primary Objectives

1. **Consolidate Migration History**: Merge all existing migrations into one comprehensive initial schema migration
2. **Preserve Schema Integrity**: Ensure the consolidated migration creates the exact same database schema as the current migration chain
3. **Clean Migration Directory**: Remove outdated migration files and establish a clean starting point
4. **Update Database State**: Properly stamp existing databases to reflect the new migration structure

### Expected Outcomes

- Single `initial_schema` migration file containing all tables, indexes, constraints, and enums
- Cleaner migration history for faster test execution
- Simplified onboarding for new developers
- Baseline for all future migrations
- No data loss or schema changes

### Success Criteria

- All tables, indexes, constraints, and enums present in consolidated migration
- Test database creation time reduced (fewer migrations to run)
- Migration history shows single head at initial revision
- Existing development databases can be stamped to new revision without data loss
- All tests pass after migration consolidation

---

## Technical Architecture

### 2.1 System Design Overview

**Current State:**
- Four sequential migrations creating the database schema:
  1. `f13dbedae659_initial_migration_create_users_roles_.py` (base)
  2. `5ed7d2606ef9_create_accounts_and_account_shares_.py`
  3. `7cd3ac786069_add_admin_support_with_bootstrap_and_.py`
  4. `1d78ffc27a9c_create_transactions_and_transaction_.py` (head)

**Target State:**
- Single migration: `<new_revision>_initial_schema.py`
- Contains all schema elements from the four migrations
- Serves as the new base revision for all future migrations

**Schema Elements to Consolidate:**

**Tables (10 total):**
1. `roles` - User roles and permissions
2. `users` - User accounts and authentication
3. `audit_logs` - Audit trail for all operations
4. `refresh_tokens` - JWT refresh token management
5. `user_roles` - Many-to-many user-role relationship
6. `accounts` - Financial accounts
7. `account_shares` - Shared account permissions
8. `bootstrap_state` - Initial admin setup tracking
9. `transactions` - Financial transactions
10. `transaction_tags` - Transaction categorization tags

**PostgreSQL Enums (5 total):**
1. `audit_action_enum` - Audit log action types
2. `audit_status_enum` - Audit log status values
3. `accounttype` - Account type classification
4. `permissionlevel` - Account sharing permission levels
5. `transactiontype` - Transaction type classification

**PostgreSQL Extensions:**
1. `pg_trgm` - Trigram extension for fuzzy text search

**Indexes:**
- 100+ indexes across all tables (standard, composite, partial, GIN trigram)

**Constraints:**
- Primary keys, foreign keys, unique constraints, check constraints

### 2.2 Technology Decisions

**[Alembic]**
- **Purpose**: Database migration management for SQLAlchemy
- **Why this choice**: Already in use; industry-standard for Python/SQLAlchemy projects
- **Version**: Current version in project (compatible with SQLAlchemy 2.x)
- **Alternatives considered**: Django migrations (not applicable - not using Django), Flyway (Java-focused)

**[pg_dump]**
- **Purpose**: Extract current database schema as SQL
- **Why this choice**: Most reliable way to capture exact production schema state
- **Version**: PostgreSQL client version matching database version
- **Alternatives considered**: Manual schema extraction (error-prone), Alembic autogenerate (may miss custom SQL)

**[alembic stamp]**
- **Purpose**: Mark database as being at specific migration version without running migrations
- **Why this choice**: Allows existing databases to skip consolidated migration (schema already exists)
- **Version**: Built into Alembic
- **Alternatives considered**: Drop and recreate databases (loses data), manual version table updates (fragile)

### 2.3 File Structure

```
emerald-backend/
├── alembic/
│   ├── versions/
│   │   ├── <new_revision>_initial_schema.py    # NEW: Consolidated migration
│   │   ├── f13dbedae659_initial_migration_create_users_roles_.py    # DELETE
│   │   ├── 5ed7d2606ef9_create_accounts_and_account_shares_.py     # DELETE
│   │   ├── 7cd3ac786069_add_admin_support_with_bootstrap_and_.py   # DELETE
│   │   └── 1d78ffc27a9c_create_transactions_and_transaction_.py    # DELETE
│   ├── env.py                                  # No changes
│   └── script.py.mako                          # No changes
└── alembic.ini                                 # No changes
```

**Directory Purpose:**
- `alembic/versions/`: Contains all migration files; consolidated to single file
- `alembic/`: Alembic configuration and environment setup

---

## Implementation Specification

### 3.1 Component Breakdown

#### Component: Database Schema Inspection

**Files Involved:**
- Existing development database
- `pg_dump` utility
- `/tmp/current_schema.sql` (temporary output)

**Purpose**: Capture the exact current schema state to ensure the consolidated migration creates identical structure

**Implementation Requirements:**

1. **Core Logic**:
   - Connect to development database with current schema (at head revision `1d78ffc27a9c`)
   - Use `pg_dump` to export schema-only SQL
   - Filter output to include only relevant DDL (exclude alembic_version table)
   - Verify all 10 tables, 5 enums, and pg_trgm extension are present

2. **Data Handling**:
   - Input: Development database connection string
   - Output: SQL file with complete schema definition
   - Validation: Check for presence of all expected tables and indexes

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Database not at head revision (warn user to upgrade first)
   - [ ] Handle case: pg_dump not available (provide installation instructions)
   - [ ] Validate: All expected tables present in dump
   - [ ] Error: Connection failure to database

4. **Dependencies**:
   - External: PostgreSQL client tools (pg_dump)
   - Internal: Development database in running state

5. **Testing Requirements**:
   - [ ] Unit test: Not applicable (manual verification step)
   - [ ] Integration test: Verify pg_dump output contains all tables
   - [ ] E2E test: Full migration consolidation process

**Acceptance Criteria**:
- [ ] Schema dump file contains all 10 tables
- [ ] Schema dump includes all 5 enum definitions
- [ ] Schema dump includes pg_trgm extension
- [ ] File size reasonable (indicates complete schema, not empty)

**Implementation Notes**:
- Use `--schema-only` flag to exclude data
- Use `--no-owner --no-acl` to make schema portable
- Consider excluding `alembic_version` table from dump

---

#### Component: Consolidated Migration File Generation

**Files Involved**:
- `alembic/versions/<new_revision>_initial_schema.py`
- Existing migration files (for reference)

**Purpose**: Create a single migration file that establishes the complete database schema from scratch

**Implementation Requirements**:

1. **Core Logic**:
   - Generate new revision ID using `alembic revision -m "initial schema"`
   - Set `down_revision = None` (this is the first migration)
   - Consolidate all `upgrade()` operations from four migrations into one
   - Consolidate all `downgrade()` operations (reverse order)
   - Preserve all table creation order (dependencies first)

2. **Data Handling**:
   - Input: Content from four existing migrations
   - Output: Single migration file with complete schema
   - Operation order: Extensions → Enums → Tables (dependency order) → Indexes

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Enum already exists (use `CREATE TYPE IF NOT EXISTS` or check first)
   - [ ] Handle case: Extension already exists (use `CREATE EXTENSION IF NOT EXISTS`)
   - [ ] Validate: Foreign key references only point to tables created earlier in migration
   - [ ] Error: Syntax errors in consolidated SQL

4. **Dependencies**:
   - Internal: Alembic revision command
   - Internal: Content from existing migrations

5. **Testing Requirements**:
   - [ ] Unit test: Migration file syntax is valid Python
   - [ ] Integration test: Run migration on blank database successfully
   - [ ] Integration test: Downgrade removes all schema elements
   - [ ] E2E test: Schema created matches current production schema

**Acceptance Criteria**:
- [ ] Migration file has `down_revision = None`
- [ ] All 10 tables created in correct dependency order
- [ ] All 5 enums defined before tables that use them
- [ ] pg_trgm extension installed before GIN indexes created
- [ ] All indexes, constraints, and checks present
- [ ] Downgrade reverses all operations in correct order
- [ ] File includes comprehensive docstring explaining contents

**Implementation Notes**:
- Table creation order matters due to foreign keys:
  1. `roles` and `users` (independent, but users references itself)
  2. `audit_logs`, `refresh_tokens`, `user_roles` (depend on users/roles)
  3. `accounts` (depends on users)
  4. `account_shares` (depends on accounts and users)
  5. `bootstrap_state` (depends on users)
  6. `transactions` (depends on accounts and users, self-referential)
  7. `transaction_tags` (depends on transactions)

- Enum creation order:
  1. `audit_action_enum` and `audit_status_enum` (for audit_logs)
  2. `accounttype` (for accounts)
  3. `permissionlevel` (for account_shares)
  4. `transactiontype` (for transactions)

- Use Alembic's `op.f()` function for index/constraint names (ensures consistent naming)

- Include migration header docstring with:
  - Revision ID
  - Down revision (None)
  - Creation date
  - Description of all schema elements created
  - Note that this consolidates previous migrations

---

#### Component: Old Migration File Cleanup

**Files Involved**:
- `alembic/versions/f13dbedae659_initial_migration_create_users_roles_.py`
- `alembic/versions/5ed7d2606ef9_create_accounts_and_account_shares_.py`
- `alembic/versions/7cd3ac786069_add_admin_support_with_bootstrap_and_.py`
- `alembic/versions/1d78ffc27a9c_create_transactions_and_transaction_.py`

**Purpose**: Remove obsolete migration files to clean up migration history

**Implementation Requirements**:

1. **Core Logic**:
   - Delete four old migration files
   - Keep files in version control history (git) if needed for reference
   - Optionally archive to `.archive/old_migrations/` before deletion

2. **Data Handling**:
   - Input: List of old migration file paths
   - Output: Clean versions directory with only new migration

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Files already deleted (ignore)
   - [ ] Handle case: Files referenced by other code (should not be)
   - [ ] Validate: New migration file exists before deleting old ones
   - [ ] Error: Permission denied when deleting files

4. **Dependencies**:
   - Internal: New consolidated migration must exist and be tested

5. **Testing Requirements**:
   - [ ] Unit test: Verify old files removed
   - [ ] Integration test: Alembic still functions with only new migration
   - [ ] E2E test: Can create new database from scratch

**Acceptance Criteria**:
- [ ] Four old migration files deleted
- [ ] Only new initial_schema migration remains in versions/
- [ ] `alembic history` shows clean linear history
- [ ] `alembic heads` shows single head

**Implementation Notes**:
- Execute this step AFTER consolidated migration is tested and verified
- Consider keeping backups during testing phase
- Git history preserves old files if needed for reference

---

#### Component: Database Version Stamping

**Files Involved**:
- Development database `alembic_version` table
- `alembic stamp` command

**Purpose**: Update existing databases to reflect new migration structure without re-running migrations

**Implementation Requirements**:

1. **Core Logic**:
   - For databases at old head (`1d78ffc27a9c`): stamp to new revision
   - Update `alembic_version` table to point to new initial_schema revision
   - No actual schema changes (database already has correct schema)

2. **Data Handling**:
   - Input: Current revision ID in database
   - Output: Updated alembic_version table with new revision ID
   - Validation: Verify database is at expected old head before stamping

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Database at intermediate revision (must upgrade first)
   - [ ] Handle case: Database at unknown revision (manual intervention required)
   - [ ] Validate: Database schema matches expected state before stamping
   - [ ] Error: alembic_version table doesn't exist (database not initialized)

4. **Dependencies**:
   - Internal: New consolidated migration must exist
   - Internal: Old migrations must still exist when stamping (remove after)
   - External: Database connection

5. **Testing Requirements**:
   - [ ] Integration test: Stamp development database successfully
   - [ ] Integration test: Verify stamped database passes all application tests
   - [ ] Integration test: Can create new migrations after stamping

**Acceptance Criteria**:
- [ ] `alembic current` shows new revision ID
- [ ] Database schema unchanged after stamping
- [ ] Application tests pass against stamped database
- [ ] Can run `alembic upgrade head` without errors (no-op)

**Implementation Notes**:
- This is a one-time operation per database
- For fresh databases (tests, new developers): skip stamping, just run migration
- For existing databases: stamp to avoid re-running migrations
- Command: `alembic stamp <new_revision_id>`

---

### 3.2 Detailed File Specifications

#### `alembic/versions/<new_revision>_initial_schema.py`

**Purpose**: Complete initial database schema migration for Emerald Finance Platform

**Implementation**:

```python
"""Initial schema for Emerald Finance Platform

Revision ID: <new_revision>
Revises:
Create Date: 2025-11-14

This migration consolidates all previous migrations into a single initial schema.
It creates the complete database structure for the Emerald Finance Platform,
including:

Tables:
- roles: User roles and permissions
- users: User accounts and authentication
- audit_logs: Complete audit trail
- refresh_tokens: JWT token management
- user_roles: User-role associations
- accounts: Financial accounts
- account_shares: Shared account permissions
- bootstrap_state: Initial setup tracking
- transactions: Financial transactions
- transaction_tags: Transaction categorization

Enums:
- audit_action_enum: Audit action types
- audit_status_enum: Audit status values
- accounttype: Account classification
- permissionlevel: Permission levels for sharing
- transactiontype: Transaction types

Extensions:
- pg_trgm: Trigram fuzzy search support

Previous migrations consolidated:
- f13dbedae659: Initial migration (users, roles, audit_logs, refresh_tokens)
- 5ed7d2606ef9: Accounts and account shares
- 7cd3ac786069: Admin support with bootstrap state
- 1d78ffc27a9c: Transactions and transaction tags
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '<new_revision>'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Creates complete database schema from scratch.
    """
    # =========================================================================
    # STEP 1: Install PostgreSQL Extensions
    # =========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # =========================================================================
    # STEP 2: Create Enums
    # =========================================================================

    # Enums for audit_logs table
    op.execute("""
        CREATE TYPE audit_action_enum AS ENUM (
            'LOGIN', 'LOGOUT', 'LOGIN_FAILED', 'PASSWORD_CHANGE',
            'TOKEN_REFRESH', 'CREATE', 'READ', 'UPDATE', 'DELETE',
            'PERMISSION_GRANT', 'PERMISSION_REVOKE', 'ROLE_ASSIGN',
            'ROLE_REMOVE', 'ACCOUNT_ACTIVATE', 'ACCOUNT_DEACTIVATE',
            'ACCOUNT_LOCK', 'ACCOUNT_UNLOCK', 'RATE_LIMIT_EXCEEDED',
            'INVALID_TOKEN', 'PERMISSION_DENIED', 'SPLIT_TRANSACTION',
            'JOIN_TRANSACTION'
        )
    """)

    op.execute("""
        CREATE TYPE audit_status_enum AS ENUM (
            'SUCCESS', 'FAILURE', 'PARTIAL'
        )
    """)

    # Enums for accounts table
    op.execute("""
        CREATE TYPE accounttype AS ENUM (
            'SAVINGS', 'CREDIT_CARD', 'DEBIT_CARD', 'LOAN',
            'INVESTMENT', 'OTHER'
        )
    """)

    # Enums for account_shares table
    op.execute("""
        CREATE TYPE permissionlevel AS ENUM (
            'OWNER', 'EDITOR', 'VIEWER'
        )
    """)

    # Enums for transactions table
    op.execute("""
        CREATE TYPE transactiontype AS ENUM (
            'debit', 'credit', 'transfer', 'fee', 'interest', 'other'
        )
    """)

    # =========================================================================
    # STEP 3: Create Base Tables (no dependencies)
    # =========================================================================

    # roles table
    op.create_table(
        'roles',
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles'))
    )
    op.create_index(op.f('ix_roles_created_at'), 'roles', ['created_at'], unique=False)
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # users table
    op.create_table(
        'users',
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_created_by'), 'users', ['created_by'], unique=False)
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_is_admin'), 'users', ['is_admin'], unique=False)
    op.create_index(op.f('ix_users_updated_by'), 'users', ['updated_by'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)

    # Partial indexes for users (from admin migration)
    op.create_index(
        'ix_users_is_admin_true',
        'users',
        ['is_admin'],
        postgresql_where=sa.text('is_admin = TRUE'),
        unique=False
    )
    op.create_index(
        'ix_users_deleted_at_not_null',
        'users',
        ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NOT NULL'),
        unique=False
    )

    # =========================================================================
    # STEP 4: Create Dependent Tables (depend on users/roles)
    # =========================================================================

    # audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', postgresql.ENUM(name='audit_action_enum'), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('status', postgresql.ENUM(name='audit_status_enum'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_logs_user_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_action_date', 'audit_logs', ['action', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    op.create_index('ix_audit_logs_failures', 'audit_logs', ['status', 'created_at'], unique=False,
                    postgresql_where=sa.text("status = 'FAILURE'"))
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_ip_address'), 'audit_logs', ['ip_address'], unique=False)
    op.create_index('ix_audit_logs_request', 'audit_logs', ['request_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_request_id'), 'audit_logs', ['request_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_status'), 'audit_logs', ['status'], unique=False)
    op.create_index('ix_audit_logs_user_date', 'audit_logs', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    # refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('token_family_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens'))
    )
    op.create_index('ix_refresh_tokens_cleanup', 'refresh_tokens', ['expires_at', 'is_revoked'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_created_at'), 'refresh_tokens', ['created_at'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_expires_at'), 'refresh_tokens', ['expires_at'], unique=False)
    op.create_index('ix_refresh_tokens_family', 'refresh_tokens', ['token_family_id', 'is_revoked'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_id'), 'refresh_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_is_revoked'), 'refresh_tokens', ['is_revoked'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token_family_id'), 'refresh_tokens', ['token_family_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_user_valid', 'refresh_tokens', ['user_id', 'is_revoked', 'expires_at'], unique=False)

    # user_roles table
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], name=op.f('fk_user_roles_assigned_by_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles'))
    )

    # bootstrap_state table
    op.create_table(
        'bootstrap_state',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('completed = TRUE', name='ck_bootstrap_state_completed'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # =========================================================================
    # STEP 5: Create Account Tables
    # =========================================================================

    # accounts table
    op.create_table(
        'accounts',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('account_type', postgresql.ENUM(name='accounttype'), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('opening_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f('ck_accounts_ck_accounts_currency_format')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_accounts_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_accounts'))
    )
    op.create_index(op.f('ix_accounts_account_name'), 'accounts', ['account_name'], unique=False)
    op.create_index(op.f('ix_accounts_account_type'), 'accounts', ['account_type'], unique=False)
    op.create_index(op.f('ix_accounts_created_at'), 'accounts', ['created_at'], unique=False)
    op.create_index(op.f('ix_accounts_created_by'), 'accounts', ['created_by'], unique=False)
    op.create_index(op.f('ix_accounts_currency'), 'accounts', ['currency'], unique=False)
    op.create_index(op.f('ix_accounts_deleted_at'), 'accounts', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'], unique=False)
    op.create_index(op.f('ix_accounts_is_active'), 'accounts', ['is_active'], unique=False)
    op.create_index(op.f('ix_accounts_updated_by'), 'accounts', ['updated_by'], unique=False)
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)

    # Partial unique index for account names
    op.execute("""
        CREATE UNIQUE INDEX idx_accounts_user_name_unique
        ON accounts(user_id, LOWER(account_name))
        WHERE deleted_at IS NULL
    """)

    # account_shares table
    op.create_table(
        'account_shares',
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('permission_level', postgresql.ENUM(name='permissionlevel'), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_account_shares_account_id_accounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_account_shares_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_account_shares'))
    )
    op.create_index(op.f('ix_account_shares_account_id'), 'account_shares', ['account_id'], unique=False)
    op.create_index(op.f('ix_account_shares_created_at'), 'account_shares', ['created_at'], unique=False)
    op.create_index(op.f('ix_account_shares_created_by'), 'account_shares', ['created_by'], unique=False)
    op.create_index(op.f('ix_account_shares_deleted_at'), 'account_shares', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_account_shares_id'), 'account_shares', ['id'], unique=False)
    op.create_index(op.f('ix_account_shares_permission_level'), 'account_shares', ['permission_level'], unique=False)
    op.create_index(op.f('ix_account_shares_updated_by'), 'account_shares', ['updated_by'], unique=False)
    op.create_index(op.f('ix_account_shares_user_id'), 'account_shares', ['user_id'], unique=False)

    # Composite index for permission lookups
    op.create_index(
        'idx_account_shares_permission_lookup',
        'account_shares',
        ['account_id', 'user_id', 'deleted_at']
    )

    # Partial unique index for account shares
    op.execute("""
        CREATE UNIQUE INDEX idx_account_shares_unique
        ON account_shares(account_id, user_id)
        WHERE deleted_at IS NULL
    """)

    # =========================================================================
    # STEP 6: Create Transaction Tables
    # =========================================================================

    # transactions table
    op.create_table(
        'transactions',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Foreign Keys
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),

        # Transaction Data
        sa.Column('transaction_date', sa.Date, nullable=False),
        sa.Column('value_date', sa.Date, nullable=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('merchant', sa.String(100), nullable=True),
        sa.Column('transaction_type', postgresql.ENUM(name='transactiontype'), nullable=False),
        sa.Column('user_notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Soft Delete
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),

        # Audit Fields
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Constraints
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_transactions_currency_format'),
        sa.CheckConstraint("amount != 0", name='ck_transactions_amount_nonzero'),
    )

    # Create indexes for transactions table
    op.create_index('ix_transactions_account_id', 'transactions', ['account_id'])
    op.create_index('ix_transactions_transaction_date', 'transactions', ['transaction_date'])
    op.create_index('ix_transactions_transaction_type', 'transactions', ['transaction_type'])
    op.create_index('ix_transactions_deleted_at', 'transactions', ['deleted_at'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])
    op.create_index('ix_transactions_created_by', 'transactions', ['created_by'])
    op.create_index('ix_transactions_updated_by', 'transactions', ['updated_by'])

    # Partial index for split transactions
    op.create_index(
        'ix_transactions_parent_transaction_id',
        'transactions',
        ['parent_transaction_id'],
        postgresql_where=sa.text('parent_transaction_id IS NOT NULL'),
    )

    # Composite indexes
    op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'transaction_date'])
    op.create_index('ix_transactions_account_deleted', 'transactions', ['account_id', 'deleted_at'])

    # GIN indexes for trigram fuzzy search
    op.execute("CREATE INDEX ix_transactions_merchant_trgm ON transactions USING GIN (merchant gin_trgm_ops)")
    op.execute("CREATE INDEX ix_transactions_description_trgm ON transactions USING GIN (description gin_trgm_ops)")

    # transaction_tags table
    op.create_table(
        'transaction_tags',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Foreign Key
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),

        # Tag Data
        sa.Column('tag', sa.String(50), nullable=False),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('transaction_id', 'tag', name='uq_transaction_tags_transaction_tag'),
    )

    # Create indexes for transaction_tags table
    op.create_index('ix_transaction_tags_transaction_id', 'transaction_tags', ['transaction_id'])
    op.create_index('ix_transaction_tags_tag', 'transaction_tags', ['tag'])
    op.create_index('ix_transaction_tags_created_at', 'transaction_tags', ['created_at'])


def downgrade() -> None:
    """
    Downgrade schema.

    Removes all schema elements in reverse order.
    """
    # Drop tables in reverse dependency order
    op.drop_table('transaction_tags')
    op.drop_table('transactions')
    op.drop_table('account_shares')
    op.drop_table('accounts')
    op.drop_table('bootstrap_state')
    op.drop_table('user_roles')
    op.drop_table('refresh_tokens')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('roles')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS transactiontype')
    op.execute('DROP TYPE IF EXISTS permissionlevel')
    op.execute('DROP TYPE IF EXISTS accounttype')
    op.execute('DROP TYPE IF EXISTS audit_status_enum')
    op.execute('DROP TYPE IF EXISTS audit_action_enum')

    # Note: We don't drop pg_trgm extension as it might be used elsewhere
    # If needed, manually drop with: DROP EXTENSION IF EXISTS pg_trgm
```

**Edge Cases**:
- When pg_trgm extension already exists: Use `CREATE EXTENSION IF NOT EXISTS`
- When enums already exist: Use raw SQL with error handling or check first
- When running downgrade: Some operations may fail if data exists (expected)

**Tests**:
- [ ] Test: Migration runs successfully on blank PostgreSQL database
- [ ] Test: All tables created with correct column types
- [ ] Test: All indexes created (verify with `\d+ table_name` in psql)
- [ ] Test: Foreign keys enforce referential integrity
- [ ] Test: Check constraints prevent invalid data
- [ ] Test: Downgrade removes all schema elements
- [ ] Test: Can run upgrade after downgrade (idempotent)

---

## Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Preparation and Validation (Size: S, Priority: P0)

**Goal**: Prepare for migration consolidation by backing up current state and validating schema consistency

**Scope**:
- ✅ Include: Database schema inspection, backup creation, validation
- ❌ Exclude: Actual migration file creation and consolidation

**Components to Implement**:
- [ ] Schema inspection and documentation
- [ ] Development database backup
- [ ] Validation tests

**Detailed Tasks**:

1. [ ] Inspect current database schema
   - Run `uv run alembic current` to verify at head revision
   - Export schema using `pg_dump --schema-only --no-owner --no-acl emerald_db > /tmp/schema_before_consolidation.sql`
   - Review schema dump to confirm all expected tables present

2. [ ] Create backup of development database
   - Run `pg_dump emerald_db > /tmp/emerald_db_backup_$(date +%Y%m%d).sql`
   - Verify backup file size is reasonable
   - Test restore to temporary database (optional but recommended)

3. [ ] Document current migration chain
   - Run `uv run alembic history --verbose` and save output
   - Note revision IDs: base (`f13dbedae659`) to head (`1d78ffc27a9c`)
   - Count total tables, indexes, constraints in current schema

4. [ ] Verify test suite baseline
   - Run full test suite: `uv run pytest`
   - Ensure all tests pass before starting consolidation
   - Document test execution time (baseline for improvement measurement)

**Dependencies**:
- Requires: PostgreSQL client tools installed (pg_dump, psql)
- Requires: Development database running and accessible
- Blocks: Phase 2 (cannot proceed until validation complete)

**Validation Criteria** (Phase complete when):
- [ ] Current revision confirmed as `1d78ffc27a9c`
- [ ] Schema dump file exists and contains all 10 tables
- [ ] Backup file created successfully
- [ ] All tests passing (baseline established)
- [ ] Migration history documented

**Risk Factors**:
- Database connection issues (mitigation: verify connection before starting)
- pg_dump not installed (mitigation: provide installation instructions)
- Tests failing before consolidation (mitigation: fix tests before proceeding)

**Estimated Effort**: 1 hour for 1 developer

---

#### Phase 2: Consolidated Migration Creation (Size: M, Priority: P0)

**Goal**: Create and test the new consolidated initial_schema migration file

**Scope**:
- ✅ Include: New migration file creation, content consolidation, syntax validation
- ❌ Exclude: Old migration removal, database stamping

**Components to Implement**:
- [ ] New migration file generation
- [ ] Migration content consolidation
- [ ] Fresh database testing

**Detailed Tasks**:

1. [ ] Generate new migration file
   - Run `uv run alembic revision -m "initial schema"`
   - Note new revision ID generated
   - Verify file created in `alembic/versions/`

2. [ ] Set migration metadata
   - Edit new migration file
   - Set `down_revision = None` (this is base migration)
   - Set `branch_labels = None`
   - Set `depends_on = None`
   - Add comprehensive docstring (see detailed file specification above)

3. [ ] Consolidate upgrade() operations
   - Copy extension installation from transaction migration
   - Copy enum creation from all migrations (5 enums total)
   - Copy table creation in dependency order:
     - roles, users (base tables)
     - audit_logs, refresh_tokens, user_roles (depend on users/roles)
     - bootstrap_state (depends on users)
     - accounts (depends on users)
     - account_shares (depends on accounts and users)
     - transactions (depends on accounts and users)
     - transaction_tags (depends on transactions)
   - Copy all index creation statements
   - Preserve all constraints and custom indexes

4. [ ] Consolidate downgrade() operations
   - Drop tables in reverse order
   - Drop enums after all tables dropped
   - Add note about pg_trgm extension (don't drop automatically)

5. [ ] Test migration on fresh database
   - Create temporary test database: `createdb emerald_migration_test`
   - Run migration: `uv run alembic upgrade head` (with test DB configured)
   - Verify all tables created: `psql emerald_migration_test -c "\dt"`
   - Verify all indexes created: Check index counts match expected
   - Test downgrade: `uv run alembic downgrade base`
   - Verify all tables removed
   - Clean up: `dropdb emerald_migration_test`

6. [ ] Compare schemas
   - Create database from new migration
   - Export schema: `pg_dump --schema-only emerald_migration_test > /tmp/schema_after_consolidation.sql`
   - Compare with original: `diff /tmp/schema_before_consolidation.sql /tmp/schema_after_consolidation.sql`
   - Investigate any differences (should be minimal, mostly ordering)

**Dependencies**:
- Requires: Phase 1 complete (backup and validation done)
- Requires: Alembic installed and configured
- Blocks: Phase 3 (cannot remove old migrations until new one tested)

**Validation Criteria** (Phase complete when):
- [ ] New migration file created with correct metadata
- [ ] Migration runs successfully on blank database
- [ ] All 10 tables created with correct structure
- [ ] All enums, indexes, and constraints present
- [ ] Downgrade removes all schema elements cleanly
- [ ] Schema comparison shows equivalent structure
- [ ] Migration file includes comprehensive documentation

**Risk Factors**:
- Missing indexes or constraints (mitigation: thorough comparison with original schema)
- Incorrect table creation order (mitigation: test on blank database)
- Enum creation errors (mitigation: use raw SQL with proper error handling)

**Estimated Effort**: 3-4 hours for 1 developer

---

#### Phase 3: Migration History Cleanup (Size: S, Priority: P1)

**Goal**: Remove old migration files and update database version stamps

**Scope**:
- ✅ Include: Old file deletion, database stamping, history verification
- ❌ Exclude: Schema changes (already complete in Phase 2)

**Components to Implement**:
- [ ] Database version stamping
- [ ] Old migration file removal
- [ ] History verification

**Detailed Tasks**:

1. [ ] Stamp existing databases to new revision
   - For development database (if keeping data):
     - Verify at old head: `uv run alembic current`
     - Stamp to new revision: `uv run alembic stamp <new_revision_id>`
     - Verify stamp: `uv run alembic current`
   - Note: Test databases will be recreated fresh, no stamping needed

2. [ ] Remove old migration files
   - Optional: Archive old migrations first
     - `mkdir -p .archive/old_migrations`
     - `mv alembic/versions/f13dbedae659_*.py .archive/old_migrations/`
     - `mv alembic/versions/5ed7d2606ef9_*.py .archive/old_migrations/`
     - `mv alembic/versions/7cd3ac786069_*.py .archive/old_migrations/`
     - `mv alembic/versions/1d78ffc27a9c_*.py .archive/old_migrations/`
   - Or delete directly: `rm alembic/versions/{f13dbedae659,5ed7d2606ef9,7cd3ac786069,1d78ffc27a9c}_*.py`

3. [ ] Verify migration history
   - Run `uv run alembic history`
   - Should show only new initial_schema migration
   - Run `uv run alembic heads`
   - Should show single head
   - Run `uv run alembic current`
   - Should show current database at new revision

4. [ ] Test development workflow
   - Verify can run application against stamped database
   - Verify all application tests pass
   - Verify can create new migration: `uv run alembic revision -m "test migration"`
   - Delete test migration after verification

5. [ ] Update documentation
   - Update README or development docs if they reference old migrations
   - Document the consolidation for team reference
   - Note new baseline revision ID

**Dependencies**:
- Requires: Phase 2 complete (new migration tested and working)
- Requires: All team members aware of changes (coordination)

**Validation Criteria** (Phase complete when):
- [ ] Development database stamped to new revision
- [ ] Old migration files removed or archived
- [ ] `alembic history` shows clean linear history
- [ ] `alembic heads` shows single head
- [ ] All application tests pass
- [ ] Can create new migrations successfully
- [ ] Team members notified of changes

**Risk Factors**:
- Accidentally stamping wrong revision (mitigation: verify revision ID before stamping)
- Deleting old migrations before stamping (mitigation: follow phase order strictly)
- Team member confusion (mitigation: clear communication and documentation)

**Estimated Effort**: 1-2 hours for 1 developer

---

### 4.2 Implementation Sequence

```
Phase 1: Preparation (P0, 1 hour)
  ↓
Phase 2: Migration Creation (P0, 3-4 hours) ← Cannot start until Phase 1 validation complete
  ↓
Phase 3: Cleanup (P1, 1-2 hours) ← Cannot start until Phase 2 migration tested
```

**Rationale for ordering**:
- Phase 1 first because: Establishes baseline and ensures safe starting point with backups
- Phase 2 depends on Phase 1 because: Need validated current state before creating new migration
- Phase 3 depends on Phase 2 because: Cannot remove old migrations until new one is tested and working
- Phases must run sequentially, no parallelization possible

**Quick Wins** (if applicable):
- After Phase 2 completes: New developers can use simplified single-migration setup immediately
- Test execution time improves as soon as test databases use new single migration

---

## Simplicity & Design Validation

### Simplicity Checklist

- [x] Is this the SIMPLEST solution that solves the problem?
  - Yes: Consolidates 4 migrations into 1, reducing complexity

- [x] Have we avoided premature optimization?
  - Yes: This is optimization based on actual need (early-stage app with no users)

- [x] Does this align with existing patterns in the codebase?
  - Yes: Uses standard Alembic migration patterns, just consolidated

- [x] Can we deliver value in smaller increments?
  - Partially: Could keep old migrations, but consolidation is atomic operation

- [x] Are we solving the actual problem vs. a perceived problem?
  - Yes: Actual problem - unnecessary migration complexity for early-stage app

### Alternatives Considered

**Alternative 1: Keep all existing migrations**
- **Description**: Leave migration history as-is, continue adding new migrations
- **Why not chosen**: Accumulates technical debt; slower test execution; harder onboarding for new devs; no benefit at this early stage with no production users

**Alternative 2: Use Alembic's merge command**
- **Description**: Use `alembic merge` to create merge migration linking all branches
- **Why not chosen**: Doesn't reduce number of migrations; adds complexity rather than removing it; designed for branch reconciliation, not consolidation

**Alternative 3: Manual SQL schema file (no Alembic)**
- **Description**: Abandon Alembic, use raw SQL schema file
- **Why not chosen**: Loses migration management benefits; harder to track future changes; not aligned with project's SQLAlchemy/Alembic architecture

### Rationale

The proposed approach (single consolidated migration) is preferred because:
- **Simplicity**: One migration is simpler than four
- **Performance**: Faster test database creation (4x fewer migrations to run)
- **Maintainability**: Easier for new developers to understand complete schema
- **Timing**: Early stage of application (no production data) makes this safe
- **Reversibility**: Can always add new migrations for future changes
- **Standard practice**: Common pattern for early-stage applications (see Django's squashmigrations)

---

## References & Related Documents

### Alembic Documentation
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) - Official Alembic documentation
- [Working with Branches](https://alembic.sqlalchemy.org/en/latest/branches.html) - Alembic branch management
- [Cookbook - Squashing Migrations](https://github.com/sqlalchemy/alembic/discussions/1572) - Community discussion on squashing migrations

### Best Practices
- [Best Practices for Alembic Schema Migration](https://www.pingcap.com/article/best-practices-alembic-schema-migration/) - Production migration strategies
- [Squash Migrations Using Alembic and Postgres](https://notes.alexkehayias.com/squash-migrations-using-alembic/) - Practical guide to migration consolidation
- [Database Migrations with Alembic](https://testdriven.io/blog/alembic-database-migrations/) - Comprehensive tutorial

### Related Tools
- [pg_dump Documentation](https://www.postgresql.org/docs/current/app-pgdump.html) - PostgreSQL schema extraction
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) - ORM reference for model definitions

### Project Context
- `.features/descriptions/merge-alembic-migrations.md` - Original feature request
- `alembic/env.py:1` - Alembic environment configuration
- `alembic.ini:1` - Alembic configuration file
- `src/models/__init__.py:1` - SQLAlchemy model registry

### Performance Context
- [Warehouse Issue #17590](https://github.com/pypi/warehouse/issues/17590) - Real-world example of test performance improvement from migration squashing (PyPI project reduced 246 migrations)

---

## Additional Notes

### Testing Strategy

1. **Unit Tests**: Not applicable for migration files (structural, not logic)

2. **Integration Tests**:
   - Create fresh database from new migration
   - Verify all models can be instantiated
   - Verify all relationships work correctly
   - Verify constraints enforce data integrity

3. **E2E Tests**:
   - Run full application test suite against new migration
   - Verify no test failures introduced
   - Measure test execution time improvement

### Rollback Plan

If consolidation causes issues:

1. **Immediate Rollback** (before old migrations deleted):
   - Restore old migration files from git history
   - Stamp database back to old head: `alembic stamp 1d78ffc27a9c`
   - Delete new consolidated migration
   - Verify application works normally

2. **After Old Migrations Deleted**:
   - Restore old migrations from `.archive/old_migrations/` or git
   - Follow same steps as immediate rollback

### Team Coordination

- **Communication**: Notify all developers before performing consolidation
- **Timing**: Perform during low-activity period (no active feature branches with new migrations)
- **Documentation**: Update onboarding docs to reflect new baseline migration
- **Git**: Commit consolidation as single atomic commit for easy reversion

### Future Considerations

- **Migration Pruning**: Consider periodic consolidation as project grows (every 6-12 months)
- **Production Migrations**: When app reaches production, never consolidate migrations that have run in production
- **Branching Strategy**: Use feature flags or coordination to prevent migration conflicts in multi-developer environments
