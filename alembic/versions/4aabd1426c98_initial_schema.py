"""Initial schema for Emerald Finance Platform

Revision ID: 4aabd1426c98
Revises: 9cfdc3051d85
Create Date: 2025-11-14

This migration consolidates all previous migrations into a single initial schema.
It creates the complete database structure for the Emerald Finance Platform.

Prerequisites:
- Depends on migration 9cfdc3051d85_create_enums_and_extensions which creates:
  * All PostgreSQL enum types (audit_action_enum, audit_status_enum, accounttype, permissionlevel, transactiontype)
  * PostgreSQL pg_trgm extension for fuzzy text search

Tables Created:
- roles: User roles and permissions
- users: User accounts and authentication
- audit_logs: Complete audit trail
- refresh_tokens: JWT token management
- user_roles: User-role associations
- accounts: Financial accounts
- account_shares: Shared account permissions
- transactions: Financial transactions
- transaction_tags: Transaction categorization

This consolidates migrations from:
- f13dbedae659_initial_migration (users, roles, audit, tokens)
- 7cd3ac786069_add_admin_support (admin flags, bootstrap)
- 5ed7d2606ef9_create_accounts (accounts, shares)
- 1d78ffc27a9c_create_transactions (transactions, tags)
"""
from typing import Sequence, Union
from datetime import datetime, UTC
import uuid
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from argon2 import PasswordHasher

# revision identifiers, used by Alembic.
revision: str = '4aabd1426c98'
down_revision: Union[str, Sequence[str], None] = '9cfdc3051d85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Creates complete database schema from scratch.

    This consolidates migrations from:
    - f13dbedae659_initial_migration (users, roles, audit, tokens)
    - 7cd3ac786069_add_admin_support (admin flags, bootstrap)
    - 5ed7d2606ef9_create_accounts (accounts, shares)
    - 1d78ffc27a9c_create_transactions (transactions, tags)

    Note: This migration depends on 9cfdc3051d85_create_enums_and_extensions
    which creates all required enum types and PostgreSQL extensions.
    """
    # =========================================================================
    # STEP 1: Create Base Tables (no dependencies)
    # =========================================================================

    # roles table
    op.create_table(
        'roles',
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles'))
    )
    op.create_index(op.f('ix_roles_created_at'), 'roles', ['created_at'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # users table
    op.create_table(
        'users',
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_created_by'), 'users', ['created_by'], unique=False)
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_is_admin'), 'users', ['is_admin'], unique=False)
    op.create_index(op.f('ix_users_updated_at'), 'users', ['updated_at'], unique=False)
    op.create_index(op.f('ix_users_updated_by'), 'users', ['updated_by'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Partial indexes for users
    op.create_index(
        'ix_users_is_admin_true',
        'users',
        ['is_admin'],
        postgresql_where=sa.text('is_admin = TRUE'),
        unique=False
    )
    # Partial index for soft-deleted users - improves performance of deleted user queries
    op.create_index(
        'ix_users_deleted_at_not_null',
        'users',
        ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NOT NULL'),
        unique=False
    )

    # =========================================================================
    # STEP 2: Create Dependent Tables (depend on users/roles)
    # =========================================================================

    # audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', postgresql.ENUM(name='audit_action_enum', create_type=False), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('status', postgresql.ENUM(name='audit_status_enum', create_type=False), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
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
                    postgresql_where=sa.text("status = 'FAILURE'::audit_status_enum"))
    op.create_index(op.f('ix_audit_logs_ip_address'), 'audit_logs', ['ip_address'], unique=False)
    op.create_index('ix_audit_logs_request', 'audit_logs', ['request_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_request_id'), 'audit_logs', ['request_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_status'), 'audit_logs', ['status'], unique=False)
    op.create_index('ix_audit_logs_user_date', 'audit_logs', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    # NEW: Added composite index for user + action queries (e.g., "show all LOGIN actions for user X")
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'], unique=False)

    # refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('token_family_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens'))
    )
    op.create_index('ix_refresh_tokens_cleanup', 'refresh_tokens', ['expires_at', 'is_revoked'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_created_at'), 'refresh_tokens', ['created_at'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_expires_at'), 'refresh_tokens', ['expires_at'], unique=False)
    op.create_index('ix_refresh_tokens_family', 'refresh_tokens', ['token_family_id', 'is_revoked'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_is_revoked'), 'refresh_tokens', ['is_revoked'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token_family_id'), 'refresh_tokens', ['token_family_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_user_valid', 'refresh_tokens', ['user_id', 'is_revoked', 'expires_at'], unique=False)

    # user_roles table
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], name=op.f('fk_user_roles_assigned_by_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles'))
    )

    # =========================================================================
    # STEP 3: Create Account Tables
    # From: 5ed7d2606ef9_create_accounts
    # =========================================================================

    # accounts table
    op.create_table(
        'accounts',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('account_type', postgresql.ENUM(name='accounttype', create_type=False), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('opening_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        # FIXED: Removed op.f() wrapper to avoid double-prefixing constraint name
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_accounts_currency_format'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_accounts_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_accounts'))
    )
    op.create_index(op.f('ix_accounts_account_name'), 'accounts', ['account_name'], unique=False)
    op.create_index(op.f('ix_accounts_account_type'), 'accounts', ['account_type'], unique=False)
    op.create_index(op.f('ix_accounts_created_at'), 'accounts', ['created_at'], unique=False)
    op.create_index(op.f('ix_accounts_created_by'), 'accounts', ['created_by'], unique=False)
    op.create_index(op.f('ix_accounts_currency'), 'accounts', ['currency'], unique=False)
    op.create_index(op.f('ix_accounts_deleted_at'), 'accounts', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_accounts_is_active'), 'accounts', ['is_active'], unique=False)
    op.create_index(op.f('ix_accounts_updated_at'), 'accounts', ['updated_at'], unique=False)
    op.create_index(op.f('ix_accounts_updated_by'), 'accounts', ['updated_by'], unique=False)
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)

    # Partial unique index - enforces uniqueness only for non-deleted records
    op.execute("""
        CREATE UNIQUE INDEX idx_accounts_user_name_unique
        ON accounts(user_id, LOWER(account_name))
        WHERE deleted_at IS NULL
    """)

    # account_shares table
    op.create_table(
        'account_shares',
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_level', postgresql.ENUM(name='permissionlevel', create_type=False), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_account_shares_account_id_accounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_account_shares_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_account_shares'))
    )
    op.create_index(op.f('ix_account_shares_account_id'), 'account_shares', ['account_id'], unique=False)
    op.create_index(op.f('ix_account_shares_created_at'), 'account_shares', ['created_at'], unique=False)
    op.create_index(op.f('ix_account_shares_created_by'), 'account_shares', ['created_by'], unique=False)
    op.create_index(op.f('ix_account_shares_deleted_at'), 'account_shares', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_account_shares_permission_level'), 'account_shares', ['permission_level'], unique=False)
    op.create_index(op.f('ix_account_shares_updated_by'), 'account_shares', ['updated_by'], unique=False)
    op.create_index(op.f('ix_account_shares_user_id'), 'account_shares', ['user_id'], unique=False)

    # Composite index for permission lookups
    op.create_index(
        'idx_account_shares_permission_lookup',
        'account_shares',
        ['account_id', 'user_id', 'deleted_at']
    )

    # Partial unique index - enforces uniqueness only for non-deleted records
    op.execute("""
        CREATE UNIQUE INDEX idx_account_shares_unique
        ON account_shares(account_id, user_id)
        WHERE deleted_at IS NULL
    """)

    # =========================================================================
    # STEP 4: Create Transaction Tables
    # From: 1d78ffc27a9c_create_transactions
    # =========================================================================

    # transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_transaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('value_date', sa.Date(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('merchant', sa.String(length=100), nullable=True),
        sa.Column('transaction_type', postgresql.ENUM(name='transactiontype', create_type=False), nullable=False),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        # FIXED: Standardized FK declarations using explicit ForeignKeyConstraint
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_transactions_currency_format'),
        # Note: Zero-amount transactions are allowed (e.g., fee waivers, promotional credits)
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_transactions_account_id_accounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_transaction_id'], ['transactions.id'], name=op.f('fk_transactions_parent_transaction_id_transactions'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_transactions_created_by_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_transactions_updated_by_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_transactions'))
    )

    # Create indexes for transactions table
    op.create_index(op.f('ix_transactions_account_id'), 'transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_transactions_transaction_date'), 'transactions', ['transaction_date'], unique=False)
    # NEW: Added value_date index for financial reporting queries
    op.create_index(op.f('ix_transactions_value_date'), 'transactions', ['value_date'], unique=False)
    op.create_index(op.f('ix_transactions_transaction_type'), 'transactions', ['transaction_type'], unique=False)
    op.create_index(op.f('ix_transactions_deleted_at'), 'transactions', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_transactions_created_at'), 'transactions', ['created_at'], unique=False)
    op.create_index(op.f('ix_transactions_updated_at'), 'transactions', ['updated_at'], unique=False)
    op.create_index(op.f('ix_transactions_created_by'), 'transactions', ['created_by'], unique=False)
    op.create_index(op.f('ix_transactions_updated_by'), 'transactions', ['updated_by'], unique=False)

    # Partial index for split transactions
    op.create_index(
        'ix_transactions_parent_transaction_id',
        'transactions',
        ['parent_transaction_id'],
        postgresql_where=sa.text('parent_transaction_id IS NOT NULL'),
    )

    # Composite indexes
    op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'transaction_date'], unique=False)
    op.create_index('ix_transactions_account_deleted', 'transactions', ['account_id', 'deleted_at'], unique=False)

    # GIN indexes for trigram fuzzy search on text fields
    op.execute("CREATE INDEX ix_transactions_merchant_trgm ON transactions USING GIN (merchant gin_trgm_ops)")
    op.execute("CREATE INDEX ix_transactions_description_trgm ON transactions USING GIN (description gin_trgm_ops)")

    # transaction_tags table
    op.create_table(
        'transaction_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('transaction_id', 'tag', name='uq_transaction_tags_transaction_tag'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], name=op.f('fk_transaction_tags_transaction_id_transactions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_transaction_tags'))
    )

    # Create indexes for transaction_tags table
    op.create_index(op.f('ix_transaction_tags_transaction_id'), 'transaction_tags', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_transaction_tags_tag'), 'transaction_tags', ['tag'], unique=False)
    op.create_index(op.f('ix_transaction_tags_created_at'), 'transaction_tags', ['created_at'], unique=False)

    # =========================================================================
    # STEP 5: Seed Initial Superuser (idempotent)
    # =========================================================================

    # Get database connection
    bind = op.get_bind()

    # Check if any admin user exists (idempotency)
    result = bind.execute(sa.text(
        "SELECT id FROM users WHERE is_admin = TRUE AND deleted_at IS NULL LIMIT 1"
    ))
    existing_admin = result.first()

    if existing_admin:
        print("⏭️  Skipping superuser creation: Admin user(s) already exist")
    else:
        # Read and validate environment variables
        from src.core.config import settings

        username = settings.superadmin_username
        email = settings.superadmin_email
        password = settings.superadmin_password
        full_name = settings.superadmin_full_name
        permissions = settings.superadmin_permissions

        # Validate uniqueness (username and email)
        result = bind.execute(sa.text(
            "SELECT id FROM users WHERE (username = :username OR email = :email) "
            "AND deleted_at IS NULL"
        ), {"username": username, "email": email})
        existing_user = result.first()

        if existing_user:
            raise ValueError(
                f"Cannot create superuser: Username '{username}' or email '{email}' already exists. "
                f"Check your SUPERADMIN_USERNAME and SUPERADMIN_EMAIL environment variables."
            )

        # Hash password using Argon2id (match application config)
        pwd_hasher = PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
            hash_len=32,
            salt_len=16,
        )
        password_hash = pwd_hasher.hash(password)

        # Create user record
        user_id = uuid.uuid4()
        now = datetime.now(UTC)

        bind.execute(sa.text(
            "INSERT INTO users (id, username, email, password_hash, full_name, "
            "is_active, is_admin, created_at, updated_at, deleted_at) "
            "VALUES (:id, :username, :email, :password_hash, :full_name, "
            ":is_active, :is_admin, :created_at, :updated_at, :deleted_at)"
        ), {
            "id": str(user_id),
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "is_active": True,
            "is_admin": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        })

        # Create or get admin role
        result = bind.execute(sa.text(
            "SELECT id FROM roles WHERE name = 'admin'"
        ))
        admin_role = result.first()

        if admin_role:
            role_id = admin_role[0]
        else:
            role_id = uuid.uuid4()
            # Convert permissions list to JSON string for PostgreSQL JSONB
            permissions_json = json.dumps(permissions)

            bind.execute(sa.text(
                "INSERT INTO roles (id, name, description, permissions, created_at, updated_at) "
                "VALUES (:id, :name, :description, CAST(:permissions AS jsonb), :created_at, :updated_at)"
            ), {
                "id": str(role_id),
                "name": "admin",
                "description": "System Administrator with full access",
                "permissions": permissions_json,
                "created_at": now,
                "updated_at": now,
            })

        # Link user to admin role
        bind.execute(sa.text(
            "INSERT INTO user_roles (user_id, role_id, assigned_at) "
            "VALUES (:user_id, :role_id, :assigned_at)"
        ), {
            "user_id": str(user_id),
            "role_id": str(role_id),
            "assigned_at": now,
        })

        # Create audit log entry
        new_values_json = json.dumps({
            'username': username,
            'email': email,
            'full_name': full_name,
            'is_admin': True,
            'is_active': True,
        })

        bind.execute(sa.text(
            "INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, "
            "description, new_values, ip_address, user_agent, request_id, status, created_at) "
            "VALUES (:id, :user_id, :action, :entity_type, :entity_id, "
            ":description, CAST(:new_values AS jsonb), :ip_address, :user_agent, :request_id, :status, :created_at)"
        ), {
            "id": str(uuid.uuid4()),
            "user_id": None,  # System operation
            "action": "CREATE",
            "entity_type": "user",
            "entity_id": str(user_id),
            "description": f"Migration: Initial superuser '{username}' created from environment config",
            "new_values": new_values_json,
            "ip_address": None,
            "user_agent": "alembic-migration",
            "request_id": None,
            "status": "SUCCESS",
            "created_at": now,
        })

        print(f"✅ Successfully created superuser: {username} ({email})")


def downgrade() -> None:
    """
    Downgrade schema.

    Removes all schema elements in reverse order.

    Note: This migration depends on 9cfdc3051d85_create_enums_and_extensions
    which will drop the enum types and PostgreSQL extensions when downgraded.
    """
    # =========================================================================
    # STEP 0: Soft-delete superuser before dropping tables
    # =========================================================================
    bind = op.get_bind()

    try:
        from src.core.config import settings
        username = settings.superadmin_username
        now = datetime.now(UTC)

        bind.execute(sa.text(
            "UPDATE users SET deleted_at = :deleted_at "
            "WHERE username = :username AND is_admin = TRUE"
        ), {"deleted_at": now, "username": username})

        print(f"✅ Soft-deleted superuser: {username}")
    except Exception as e:
        print(f"⚠️  Could not soft-delete superuser: {e}")

    # =========================================================================
    # STEP 1: Drop manually created indexes (not managed by drop_table)
    # =========================================================================
    # Transaction table GIN indexes (created with raw SQL)
    op.execute('DROP INDEX IF EXISTS ix_transactions_description_trgm')
    op.execute('DROP INDEX IF EXISTS ix_transactions_merchant_trgm')

    # Account shares partial unique index
    op.execute('DROP INDEX IF EXISTS idx_account_shares_unique')

    # Accounts partial unique index
    op.execute('DROP INDEX IF EXISTS idx_accounts_user_name_unique')

    # =========================================================================
    # STEP 2: Drop tables in reverse dependency order
    # =========================================================================
    op.drop_table('transaction_tags')
    op.drop_table('transactions')
    op.drop_table('account_shares')
    op.drop_table('accounts')
    op.drop_table('user_roles')
    op.drop_table('refresh_tokens')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('roles')
