# Database Schema - Personal Finance Backend

**Related Plan**: `20251027_project-initialization.md`
**Last Updated**: October 27, 2025

---

## Schema Overview

This document details the complete database schema for the personal finance backend platform. The schema is designed for PostgreSQL and follows the standards defined in `.claude/standards/database.md`.

### Design Principles

1. **Normalization**: Third normal form (3NF) with denormalization only where performance requires
2. **Referential Integrity**: All foreign keys with explicit ON DELETE/ON UPDATE clauses
3. **Soft Deletes**: All user-facing tables include `deleted_at` for data retention
4. **Audit Trail**: Timestamps (`created_at`, `updated_at`) on all tables
5. **Decimal Precision**: All monetary amounts use NUMERIC(12, 2) type
6. **Hierarchies**: Adjacency list pattern for category trees

---

## Core Tables

### users

**Purpose**: Store user accounts and authentication credentials

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- 'user', 'admin'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    CONSTRAINT chk_username_length CHECK (LENGTH(username) >= 3 AND LENGTH(username) <= 100),
    CONSTRAINT chk_role CHECK (role IN ('user', 'admin'))
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE users IS 'User accounts with authentication credentials';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password (cost factor 12)';
COMMENT ON COLUMN users.role IS 'User role for authorization (user, admin)';
```

### refresh_tokens

**Purpose**: Store refresh tokens for JWT authentication

```sql
CREATE TABLE refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_expires_future CHECK (expires_at > created_at)
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token) WHERE revoked = FALSE;
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

COMMENT ON TABLE refresh_tokens IS 'JWT refresh tokens for extending user sessions';
```

### accounts

**Purpose**: Store bank accounts, credit cards, and other financial accounts

```sql
CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    opening_balance NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    current_balance NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    description TEXT,
    institution VARCHAR(200),
    account_number_last4 VARCHAR(4),
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_account_type CHECK (account_type IN ('checking', 'savings', 'credit_card', 'debit_card', 'loan', 'investment', 'cash', 'other')),
    CONSTRAINT chk_currency_format CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT chk_name_length CHECK (LENGTH(name) >= 1 AND LENGTH(name) <= 100)
);

CREATE INDEX idx_accounts_user_id ON accounts(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_accounts_account_type ON accounts(account_type);
CREATE INDEX idx_accounts_currency ON accounts(currency);
CREATE INDEX idx_accounts_deleted_at ON accounts(deleted_at) WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE accounts IS 'Financial accounts (bank accounts, credit cards, etc.)';
COMMENT ON COLUMN accounts.current_balance IS 'Calculated from transactions, updated via trigger';
COMMENT ON COLUMN accounts.account_number_last4 IS 'Last 4 digits for identification (optional)';
```

### account_permissions

**Purpose**: Track account sharing and user permissions

```sql
CREATE TABLE account_permissions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_level VARCHAR(20) NOT NULL,
    granted_by BIGINT NOT NULL REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_permission_level CHECK (permission_level IN ('owner', 'editor', 'viewer')),
    CONSTRAINT unq_account_user UNIQUE (account_id, user_id)
);

CREATE INDEX idx_account_permissions_account_id ON account_permissions(account_id);
CREATE INDEX idx_account_permissions_user_id ON account_permissions(user_id);
CREATE INDEX idx_account_permissions_level ON account_permissions(permission_level);

COMMENT ON TABLE account_permissions IS 'Account sharing permissions (owner/editor/viewer)';
COMMENT ON COLUMN account_permissions.permission_level IS 'owner: full control, editor: modify data, viewer: read-only';
```

### transactions

**Purpose**: Store financial transactions with full details

```sql
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    parent_id BIGINT REFERENCES transactions(id) ON DELETE SET NULL,
    import_batch_id BIGINT REFERENCES import_batches(id) ON DELETE SET NULL,

    operation_date DATE NOT NULL,
    value_date DATE,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,

    description VARCHAR(500) NOT NULL,
    merchant VARCHAR(200),
    transaction_type VARCHAR(50) NOT NULL DEFAULT 'debit',

    comment TEXT,
    tags TEXT[],

    created_by BIGINT NOT NULL REFERENCES users(id),
    updated_by BIGINT REFERENCES users(id),

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_amount_nonzero CHECK (amount != 0.00),
    CONSTRAINT chk_currency_format CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT chk_transaction_type CHECK (transaction_type IN ('debit', 'credit', 'transfer', 'fee', 'interest', 'dividend', 'other')),
    CONSTRAINT chk_description_length CHECK (LENGTH(description) >= 1 AND LENGTH(description) <= 500),
    CONSTRAINT chk_value_date CHECK (value_date IS NULL OR value_date >= operation_date - INTERVAL '30 days')
);

CREATE INDEX idx_transactions_account_id ON transactions(account_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_transactions_operation_date ON transactions(operation_date DESC);
CREATE INDEX idx_transactions_parent_id ON transactions(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_transactions_import_batch_id ON transactions(import_batch_id);
CREATE INDEX idx_transactions_created_by ON transactions(created_by);
CREATE INDEX idx_transactions_deleted_at ON transactions(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_transactions_amount ON transactions(amount);
CREATE INDEX idx_transactions_description_gin ON transactions USING gin(to_tsvector('english', description));

COMMENT ON TABLE transactions IS 'Financial transactions with full audit trail';
COMMENT ON COLUMN transactions.parent_id IS 'For split transactions, references parent transaction';
COMMENT ON COLUMN transactions.operation_date IS 'Date transaction occurred';
COMMENT ON COLUMN transactions.value_date IS 'Date transaction posted (can differ from operation date)';
COMMENT ON COLUMN transactions.tags IS 'Array of free-form tags for flexible organization';
```

### categories

**Purpose**: Hierarchical taxonomy for categorizing transactions

```sql
CREATE TABLE categories (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    parent_id BIGINT REFERENCES categories(id) ON DELETE RESTRICT,

    name VARCHAR(100) NOT NULL,
    taxonomy_type VARCHAR(50) NOT NULL DEFAULT 'primary',
    description TEXT,

    color VARCHAR(7),
    icon VARCHAR(50),

    is_predefined BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_taxonomy_type CHECK (taxonomy_type IN ('primary', 'trips', 'projects', 'people', 'custom')),
    CONSTRAINT chk_name_length CHECK (LENGTH(name) >= 1 AND LENGTH(name) <= 100),
    CONSTRAINT chk_color_format CHECK (color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'),
    CONSTRAINT chk_user_or_predefined CHECK (
        (user_id IS NOT NULL AND is_predefined = FALSE) OR
        (user_id IS NULL AND is_predefined = TRUE)
    ),
    CONSTRAINT unq_name_parent_taxonomy UNIQUE (name, parent_id, taxonomy_type, user_id)
);

CREATE INDEX idx_categories_user_id ON categories(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_categories_parent_id ON categories(parent_id);
CREATE INDEX idx_categories_taxonomy_type ON categories(taxonomy_type);
CREATE INDEX idx_categories_is_predefined ON categories(is_predefined);
CREATE INDEX idx_categories_is_active ON categories(is_active);
CREATE INDEX idx_categories_deleted_at ON categories(deleted_at) WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE categories IS 'Hierarchical categories with multiple taxonomy support';
COMMENT ON COLUMN categories.taxonomy_type IS 'Type of taxonomy: primary (expense categories), trips, projects, people, custom';
COMMENT ON COLUMN categories.is_predefined IS 'System-provided categories that users cannot delete';
COMMENT ON COLUMN categories.user_id IS 'NULL for predefined categories, user-specific for custom';
```

### transaction_categories

**Purpose**: Many-to-many relationship between transactions and categories

```sql
CREATE TABLE transaction_categories (
    id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    assigned_by BIGINT NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unq_transaction_category UNIQUE (transaction_id, category_id)
);

CREATE INDEX idx_transaction_categories_transaction_id ON transaction_categories(transaction_id);
CREATE INDEX idx_transaction_categories_category_id ON transaction_categories(category_id);
CREATE INDEX idx_transaction_categories_assigned_by ON transaction_categories(assigned_by);

COMMENT ON TABLE transaction_categories IS 'Many-to-many junction table for transaction categorization';
```

### categorization_rules

**Purpose**: Auto-categorization rules for transactions

```sql
CREATE TABLE categorization_rules (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT,

    matcher_type VARCHAR(50) NOT NULL,
    matcher_config JSONB NOT NULL,

    category_ids BIGINT[] NOT NULL,

    priority INTEGER NOT NULL DEFAULT 100,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    account_ids BIGINT[],

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_matcher_type CHECK (matcher_type IN ('keyword', 'regex', 'amount', 'composite')),
    CONSTRAINT chk_priority_range CHECK (priority >= 0 AND priority <= 1000),
    CONSTRAINT chk_category_ids_not_empty CHECK (array_length(category_ids, 1) > 0)
);

CREATE INDEX idx_categorization_rules_user_id ON categorization_rules(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_categorization_rules_enabled ON categorization_rules(enabled) WHERE enabled = TRUE;
CREATE INDEX idx_categorization_rules_priority ON categorization_rules(priority DESC);
CREATE INDEX idx_categorization_rules_deleted_at ON categorization_rules(deleted_at) WHERE deleted_at IS NOT NULL;

COMMENT ON TABLE categorization_rules IS 'User-defined rules for automatic transaction categorization';
COMMENT ON COLUMN categorization_rules.matcher_type IS 'Type of matching logic: keyword, regex, amount, composite';
COMMENT ON COLUMN categorization_rules.matcher_config IS 'JSON config for matcher (e.g., {keywords: [...]} or {pattern: "..."})';
COMMENT ON COLUMN categorization_rules.category_ids IS 'Array of category IDs to assign when rule matches';
COMMENT ON COLUMN categorization_rules.account_ids IS 'Array of account IDs rule applies to (NULL = all accounts)';
```

### import_batches

**Purpose**: Track CSV import operations for rollback capability

```sql
CREATE TABLE import_batches (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    imported_by BIGINT NOT NULL REFERENCES users(id),

    filename VARCHAR(255) NOT NULL,
    column_mapping JSONB NOT NULL,

    total_rows INTEGER NOT NULL,
    successful_rows INTEGER NOT NULL DEFAULT 0,
    skipped_rows INTEGER NOT NULL DEFAULT 0,
    failed_rows INTEGER NOT NULL DEFAULT 0,

    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    error_message TEXT,

    imported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_status CHECK (status IN ('processing', 'success', 'partial', 'failed', 'rolled_back')),
    CONSTRAINT chk_row_counts CHECK (total_rows = successful_rows + skipped_rows + failed_rows)
);

CREATE INDEX idx_import_batches_account_id ON import_batches(account_id);
CREATE INDEX idx_import_batches_imported_by ON import_batches(imported_by);
CREATE INDEX idx_import_batches_status ON import_batches(status);
CREATE INDEX idx_import_batches_imported_at ON import_batches(imported_at DESC);

COMMENT ON TABLE import_batches IS 'CSV import tracking for audit and rollback';
COMMENT ON COLUMN import_batches.column_mapping IS 'JSON mapping of CSV columns to transaction fields';
```

### audit_logs

**Purpose**: Comprehensive audit trail for all user actions

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,

    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT,

    old_values JSONB,
    new_values JSONB,
    metadata JSONB,

    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_action_type CHECK (action_type IN ('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'FAILED_LOGIN', 'PERMISSION_CHANGE', 'IMPORT', 'EXPORT', 'RULE_APPLY')),
    CONSTRAINT chk_entity_type CHECK (entity_type IN ('user', 'account', 'transaction', 'category', 'rule', 'permission', 'import_batch'))
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_logs_entity_type_id ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Make audit logs immutable
REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC;

COMMENT ON TABLE audit_logs IS 'Immutable audit trail for all user actions';
COMMENT ON COLUMN audit_logs.old_values IS 'State before change (NULL for CREATE)';
COMMENT ON COLUMN audit_logs.new_values IS 'State after change (NULL for DELETE)';
```

---

## Database Triggers

### update_updated_at_column

**Purpose**: Automatically update `updated_at` timestamp on row modification

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at column
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categorization_rules_updated_at BEFORE UPDATE ON categorization_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### update_account_balance

**Purpose**: Automatically update account balance when transactions change

```sql
CREATE OR REPLACE FUNCTION update_account_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- Handle INSERT
    IF TG_OP = 'INSERT' THEN
        UPDATE accounts
        SET current_balance = current_balance +
            CASE WHEN NEW.transaction_type IN ('credit', 'income') THEN NEW.amount
                 ELSE -NEW.amount
            END
        WHERE id = NEW.account_id;
        RETURN NEW;

    -- Handle UPDATE
    ELSIF TG_OP = 'UPDATE' THEN
        -- Reverse old transaction
        UPDATE accounts
        SET current_balance = current_balance -
            CASE WHEN OLD.transaction_type IN ('credit', 'income') THEN OLD.amount
                 ELSE -OLD.amount
            END
        WHERE id = OLD.account_id;

        -- Apply new transaction
        UPDATE accounts
        SET current_balance = current_balance +
            CASE WHEN NEW.transaction_type IN ('credit', 'income') THEN NEW.amount
                 ELSE -NEW.amount
            END
        WHERE id = NEW.account_id;
        RETURN NEW;

    -- Handle DELETE (soft delete sets deleted_at)
    ELSIF TG_OP = 'UPDATE' AND NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        UPDATE accounts
        SET current_balance = current_balance -
            CASE WHEN OLD.transaction_type IN ('credit', 'income') THEN OLD.amount
                 ELSE -OLD.amount
            END
        WHERE id = OLD.account_id;
        RETURN NEW;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_account_balance
    AFTER INSERT OR UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_account_balance();
```

---

## Recursive Queries for Category Trees

### Get Full Category Tree

```sql
WITH RECURSIVE category_tree AS (
    -- Anchor: Root categories (no parent)
    SELECT
        id,
        name,
        parent_id,
        taxonomy_type,
        1 AS level,
        ARRAY[id] AS path,
        name AS full_path
    FROM categories
    WHERE parent_id IS NULL
        AND taxonomy_type = 'primary'
        AND deleted_at IS NULL

    UNION ALL

    -- Recursive: Child categories
    SELECT
        c.id,
        c.name,
        c.parent_id,
        c.taxonomy_type,
        ct.level + 1,
        ct.path || c.id,
        ct.full_path || ' > ' || c.name
    FROM categories c
    INNER JOIN category_tree ct ON c.parent_id = ct.id
    WHERE c.deleted_at IS NULL
)
SELECT * FROM category_tree
ORDER BY path;
```

### Get All Descendants of a Category

```sql
WITH RECURSIVE descendants AS (
    -- Anchor: Start with specific category
    SELECT id, name, parent_id
    FROM categories
    WHERE id = $category_id

    UNION ALL

    -- Recursive: Get all children
    SELECT c.id, c.name, c.parent_id
    FROM categories c
    INNER JOIN descendants d ON c.parent_id = d.id
    WHERE c.deleted_at IS NULL
)
SELECT * FROM descendants;
```

### Get All Ancestors of a Category

```sql
WITH RECURSIVE ancestors AS (
    -- Anchor: Start with specific category
    SELECT id, name, parent_id
    FROM categories
    WHERE id = $category_id

    UNION ALL

    -- Recursive: Get parent
    SELECT c.id, c.name, c.parent_id
    FROM categories c
    INNER JOIN ancestors a ON c.id = a.parent_id
    WHERE c.deleted_at IS NULL
)
SELECT * FROM ancestors;
```

---

## Seed Data

### Predefined Primary Categories

```sql
-- Income categories
INSERT INTO categories (name, taxonomy_type, is_predefined, parent_id, color) VALUES
    ('Income', 'primary', TRUE, NULL, '#22c55e'),
    ('Salary', 'primary', TRUE, 1, '#16a34a'),
    ('Freelance', 'primary', TRUE, 1, '#15803d'),
    ('Investment Returns', 'primary', TRUE, 1, '#166534'),
    ('Gifts Received', 'primary', TRUE, 1, '#14532d');

-- Expense categories
INSERT INTO categories (name, taxonomy_type, is_predefined, parent_id, color) VALUES
    ('Expenses', 'primary', TRUE, NULL, '#ef4444'),
    ('Housing', 'primary', TRUE, 6, '#dc2626'),
    ('Transportation', 'primary', TRUE, 6, '#b91c1c'),
    ('Food & Dining', 'primary', TRUE, 6, '#991b1b'),
    ('Utilities', 'primary', TRUE, 6, '#7f1d1d'),
    ('Healthcare', 'primary', TRUE, 6, '#dc2626'),
    ('Entertainment', 'primary', TRUE, 6, '#b91c1c'),
    ('Shopping', 'primary', TRUE, 6, '#991b1b'),
    ('Personal Care', 'primary', TRUE, 6, '#7f1d1d'),
    ('Education', 'primary', TRUE, 6, '#dc2626'),
    ('Insurance', 'primary', TRUE, 6, '#b91c1c'),
    ('Savings & Investments', 'primary', TRUE, 6, '#991b1b'),
    ('Taxes', 'primary', TRUE, 6, '#7f1d1d'),
    ('Gifts & Donations', 'primary', TRUE, 6, '#dc2626'),
    ('Miscellaneous', 'primary', TRUE, 6, '#b91c1c');

-- Second level expense subcategories
INSERT INTO categories (name, taxonomy_type, is_predefined, parent_id) VALUES
    ('Rent/Mortgage', 'primary', TRUE, 7),
    ('Property Tax', 'primary', TRUE, 7),
    ('Home Maintenance', 'primary', TRUE, 7),
    ('Car Payment', 'primary', TRUE, 8),
    ('Gas/Fuel', 'primary', TRUE, 8),
    ('Public Transit', 'primary', TRUE, 8),
    ('Groceries', 'primary', TRUE, 9),
    ('Restaurants', 'primary', TRUE, 9),
    ('Coffee Shops', 'primary', TRUE, 9);
```

---

## Performance Considerations

### Indexes

All major query patterns are indexed:
- User lookups by email/username
- Account lookups by user
- Transaction lookups by account and date
- Category tree traversal (parent_id)
- Audit log queries by user and date
- Full-text search on transaction descriptions

### Partitioning Strategy (Future)

For tables that may grow large:
- `transactions`: Partition by year (operation_date)
- `audit_logs`: Partition by month (created_at)

### Connection Pooling

Recommended settings for 1-5 concurrent users:
- Min connections: 2
- Max connections: 10
- Connection timeout: 30 seconds

---

## Migration Strategy

### Initial Setup

1. Create database: `CREATE DATABASE emerald_prod;`
2. Create app user: `CREATE USER emerald_app WITH PASSWORD 'secure_password';`
3. Grant permissions: `GRANT ALL PRIVILEGES ON DATABASE emerald_prod TO emerald_app;`
4. Run Alembic migrations: `alembic upgrade head`

### Backup and Restore

**Backup**:
```bash
pg_dump -U postgres -F c -b -v -f emerald_backup_$(date +%Y%m%d).dump emerald_prod
```

**Restore**:
```bash
pg_restore -U postgres -d emerald_prod -v emerald_backup_20251027.dump
```

### Testing Migrations

Before applying to production:
1. Create test database from production backup
2. Run migrations: `alembic upgrade head`
3. Verify data integrity
4. Test application functionality
5. Document any issues
6. Only then apply to production

---

**End of Database Schema Documentation**
