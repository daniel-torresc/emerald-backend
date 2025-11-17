# Implementation Plan: Remove Bootstrap Endpoint

**Date:** 2025-11-11
**Feature:** Remove Bootstrap Endpoint and Replace with Alembic Migration
**Priority:** P1 (High)
**Complexity:** Medium

---

## 1. Executive Summary

This implementation removes the `/api/v1/admin/bootstrap` HTTP endpoint and replaces it with an Alembic database migration that automatically creates the initial superuser during database setup. This change improves security, simplifies deployment, and follows infrastructure-as-code best practices.

### Current State
- Manual bootstrap via HTTP endpoint: `POST /api/v1/admin/bootstrap`
- Superuser credentials read from environment variables prefixed with `BOOTSTRAP_ADMIN_*`
- Bootstrap state tracked in `bootstrap_state` table to prevent duplicate execution
- Bootstrap logic in `AdminService.bootstrap_first_admin()` method
- Dedicated route handler in `/api/v1/admin/bootstrap`

### Desired State
- Automatic superuser creation via Alembic data migration
- Environment variables renamed from `BOOTSTRAP_ADMIN_*` to `SUPERADMIN_*` prefix
- No HTTP endpoint for bootstrap operations
- Simplified deployment process (database migration handles initialization)
- Backward-compatible migration approach (can run on existing installations)

### Primary Objectives
1. **Remove HTTP endpoint** and all associated code (route handler, service method, schemas)
2. **Rename environment variables** to use `SUPERADMIN_*` prefix for clarity
3. **Create idempotent Alembic migration** that seeds the superuser during database setup
4. **Remove bootstrap_state table**
5. **Update all tests** to reflect the new initialization approach
6. **Update documentation** to guide users on the new deployment process

### Expected Outcomes
- **Improved Security**: No unauthenticated HTTP endpoint that could be exploited
- **Simplified Deployment**: One-command database setup (`alembic upgrade head`)
- **Better DevOps Practices**: Infrastructure-as-code approach for initial data
- **Cleaner Codebase**: Remove ~200 lines of bootstrap-specific code
- **Consistent Experience**: Same initialization process in development, staging, and production

### Success Criteria
- ✅ All bootstrap endpoint code removed
- ✅ Environment variables renamed and validated
- ✅ Data migration creates superuser correctly
- ✅ Migration is idempotent (safe to run multiple times)
- ✅ All tests pass with 100% coverage for new migration logic
- ✅ Documentation updated with new setup process

---

## 2. Technical Architecture

### 2.1 System Design Overview

**Architecture Pattern**: Data Migration with Environment Configuration

```
┌─────────────────────────────────────────────────────────────┐
│                    Deployment Process                        │
├─────────────────────────────────────────────────────────────┤
│  1. Set environment variables (SUPERADMIN_*)                │
│  2. Run: alembic upgrade head                               │
│  3. Migration creates superuser if not exists               │
│  4. Application starts with superuser ready                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Migration Execution Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Alembic Migration                                          │
│       │                                                     │
│       ├─► Read SUPERADMIN_* env vars                        │
│       │                                                     │
│       ├─► Check if superuser exists                         │
│       │   (query users where is_admin=true)                 │
│       │                                                     │
│       ├─► If exists: Skip (idempotent)                      │
│       │                                                     │
│       ├─► If not exists:                                    │
│       │   ├─► Validate env vars                             │
│       │   ├─► Hash password (Argon2id)                      │
│       │   ├─► Insert user record                            │
│       │   ├─► Create/get admin role                         │
│       │   ├─► Link user to role                             │
│       │   └─► Create audit log entry                        │
│       │                                                     │
│       └─► Migration complete                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Components**:

1. **Alembic Migration Script** (`YYYYMMDD_seed_superuser.py`)
   - Reads environment variables using Pydantic Settings
   - Performs idempotent superuser creation
   - Handles all edge cases (duplicate username/email, missing role)
   - Creates audit log entry

2. **Configuration Updates** (`src/core/config.py`)
   - Rename fields from `bootstrap_admin_*` to `superadmin_*`
   - Maintain validation rules (min length, email format, password strength)
   - Keep default permissions list

3. **Code Removal**
   - Delete bootstrap route handler
   - Delete bootstrap service method
   - Remove bootstrap-related tests
   - Delete `bootstrap_state` table

**Integration Points**:
- ✅ Existing Alembic migration system
- ✅ Existing configuration system (Pydantic Settings)
- ✅ Existing security utilities (password hashing)
- ✅ Existing audit logging system
- ✅ Existing user/role repository pattern

**Data Flow**:
```
Environment Variables → Pydantic Settings → Migration Script → Database
```

### 2.2 Technology Decisions

**[Alembic Data Migration]**
- **Purpose**: Automatically seed initial superuser during database setup
- **Why this choice**:
  - Already integrated in project for schema migrations
  - Supports both schema and data migrations
  - Runs in controlled environment (no HTTP exposure)
  - Idempotent by design (can check state before inserting)
  - Version controlled with migration history
- **Version**: Latest stable (already in use: Alembic 1.13+)
- **Alternatives considered**:
  - CLI command (`python -m src.cli bootstrap`) - Rejected: Extra step, not automated
  - Docker entrypoint script - Rejected: Less portable, harder to test
  - Keep HTTP endpoint - Rejected: Security risk, violates infrastructure-as-code principles

**[SQLAlchemy Core for Data Insertion]**
- **Purpose**: Insert user data in migration script
- **Why this choice**:
  - Recommended approach for Alembic data migrations (per research)
  - Lightweight table definitions (avoid ORM model mismatches)
  - Works at any migration state (no dependency on current models)
  - Supports async operations via `op.get_bind()`
- **Alternatives considered**:
  - `op.bulk_insert()` - Rejected: Cannot handle relationships (user_roles junction table)
  - ORM models directly - Rejected: Migration might not match current model state
  - Raw SQL - Rejected: Less portable, harder to maintain

**[Argon2id Password Hashing]**
- **Purpose**: Hash superuser password in migration
- **Why this choice**:
  - Already used throughout application
  - NIST-recommended algorithm (2025 standard)
  - Must match existing password hashing for authentication to work
- **Version**: argon2-cffi (already in dependencies)
- **Alternatives considered**: None (must match existing implementation)

**[Pydantic Settings for Configuration]**
- **Purpose**: Read and validate environment variables
- **Why this choice**:
  - Already used for all configuration
  - Provides validation (email format, password strength)
  - Easy to access from migration via `from src.core.config import settings`
- **Version**: Pydantic 2.x (already in use)
- **Alternatives considered**:
  - `os.environ.get()` directly - Rejected: No validation, error-prone
  - Config file (YAML/JSON) - Rejected: Secrets should be in env vars, not files

### 2.3 File Structure

```
emerald-backend/
├── alembic/
│   └── versions/
│       ├── 7cd3ac786069_add_admin_support_with_bootstrap_and_.py  # LEGACY (keep)
│       └── YYYYMMDD_seed_initial_superuser.py                     # NEW MIGRATION
│
├── src/
│   ├── core/
│   │   └── config.py                        # MODIFY: Rename env vars
│   │
│   ├── api/
│   │   └── routes/
│   │       └── admin.py                     # MODIFY: Remove bootstrap route
│   │
│   ├── services/
│   │   └── admin_service.py                 # MODIFY: Remove bootstrap methods
│   │
│   └── models/
│       └── bootstrap.py                     # DELETE
│
├── tests/
│   ├── integration/
│   │   └── test_admin_routes.py             # MODIFY: Remove bootstrap tests
│   │
│   └── e2e/
│       └── test_admin_workflow.py           # MODIFY: Remove bootstrap workflow
│
├── .env.example                              # MODIFY: Update variable names
└── README.md                                 # MODIFY: Update setup instructions
```

**Directory Purpose**:
- `alembic/versions/`: Contains all database migrations (schema + data)
- `src/core/`: Application configuration and settings
- `src/api/routes/`: HTTP endpoint definitions
- `src/services/`: Business logic layer
- `tests/`: Test suites (unit, integration, e2e)

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Alembic Data Migration for Superuser Seeding

**Files Involved**:
- `alembic/versions/YYYYMMDD_seed_initial_superuser.py` (new)
- `alembic/env.py` (reference only, no changes needed)

**Purpose**: Create the initial superuser account during database initialization in an idempotent, secure manner.

**Implementation Requirements**:

1. **Core Logic**:
   - Generate migration: `alembic revision -m "seed initial superuser"`
   - Import required modules in migration file:
     - `from sqlalchemy.sql import table, column`
     - `from sqlalchemy import String, Boolean, DateTime, select, insert`
     - `from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB`
     - `from argon2 import PasswordHasher`
     - `from datetime import datetime, UTC`
     - `import uuid`
   - Define lightweight table representations (no ORM models):
     ```python
     users_table = table('users',
         column('id', PG_UUID),
         column('username', String),
         column('email', String),
         column('password_hash', String),
         column('full_name', String),
         column('is_active', Boolean),
         column('is_admin', Boolean),
         column('created_at', DateTime),
         column('updated_at', DateTime),
         column('deleted_at', DateTime),
     )

     roles_table = table('roles',
         column('id', PG_UUID),
         column('name', String),
         column('description', String),
         column('permissions', JSONB),
         column('created_at', DateTime),
         column('updated_at', DateTime),
     )

     user_roles_table = table('user_roles',
         column('user_id', PG_UUID),
         column('role_id', PG_UUID),
     )

     audit_logs_table = table('audit_logs',
         column('id', PG_UUID),
         column('user_id', PG_UUID),
         column('action', String),
         column('entity_type', String),
         column('entity_id', PG_UUID),
         column('description', String),
         column('new_values', JSONB),
         column('ip_address', String),
         column('user_agent', String),
         column('request_id', String),
         column('created_at', DateTime),
     )
     ```

2. **Data Handling**:

   **upgrade() function**:
   ```python
   def upgrade() -> None:
       """Create initial superuser if no admin users exist."""

       # Get database connection
       bind = op.get_bind()

       # Step 1: Check if any admin user exists (idempotency)
       result = bind.execute(
           select(users_table.c.id)
           .where(users_table.c.is_admin == True)
           .where(users_table.c.deleted_at.is_(None))
           .limit(1)
       )
       existing_admin = result.first()

       if existing_admin:
           print("⏭️  Skipping superuser creation: Admin user(s) already exist")
           return

       # Step 2: Read and validate environment variables
       from src.core.config import settings

       username = settings.superadmin_username
       email = settings.superadmin_email
       password = settings.superadmin_password
       full_name = settings.superadmin_full_name
       permissions = settings.superadmin_permissions

       # Step 3: Validate uniqueness (username and email)
       result = bind.execute(
           select(users_table.c.id)
           .where(
               (users_table.c.username == username) |
               (users_table.c.email == email)
           )
           .where(users_table.c.deleted_at.is_(None))
       )
       existing_user = result.first()

       if existing_user:
           raise ValueError(
               f"Cannot create superuser: Username '{username}' or email '{email}' already exists. "
               f"Check your SUPERADMIN_USERNAME and SUPERADMIN_EMAIL environment variables."
           )

       # Step 4: Hash password using Argon2id (same as application)
       pwd_hasher = PasswordHasher(
           time_cost=2,
           memory_cost=65536,  # 64 MB
           parallelism=4,
           hash_len=32,
           salt_len=16,
       )
       password_hash = pwd_hasher.hash(password)

       # Step 5: Create user record
       user_id = uuid.uuid4()
       now = datetime.now(UTC)

       bind.execute(
           insert(users_table).values(
               id=user_id,
               username=username,
               email=email,
               password_hash=password_hash,
               full_name=full_name,
               is_active=True,
               is_admin=True,
               created_at=now,
               updated_at=now,
               deleted_at=None,
           )
       )

       # Step 6: Create or get admin role
       result = bind.execute(
           select(roles_table.c.id)
           .where(roles_table.c.name == 'admin')
       )
       admin_role = result.first()

       if admin_role:
           role_id = admin_role[0]
       else:
           role_id = uuid.uuid4()
           bind.execute(
               insert(roles_table).values(
                   id=role_id,
                   name='admin',
                   description='System Administrator with full access',
                   permissions=permissions,
                   created_at=now,
                   updated_at=now,
               )
           )

       # Step 7: Link user to admin role
       bind.execute(
           insert(user_roles_table).values(
               user_id=user_id,
               role_id=role_id,
           )
       )

       # Step 8: Create audit log entry
       bind.execute(
           insert(audit_logs_table).values(
               id=uuid.uuid4(),
               user_id=None,  # System operation
               action='CREATE',
               entity_type='user',
               entity_id=user_id,
               description=f"Migration: Initial superuser '{username}' created from environment config",
               new_values={
                   'username': username,
                   'email': email,
                   'full_name': full_name,
                   'is_admin': True,
                   'is_active': True,
               },
               ip_address=None,
               user_agent='alembic-migration',
               request_id=None,
               created_at=now,
           )
       )

       print(f"✅ Successfully created superuser: {username} ({email})")
   ```

   **downgrade() function**:
   ```python
   def downgrade() -> None:
       """
       Remove superuser created by this migration.

       WARNING: This is destructive. Only execute in development.
       In production, manually verify before running downgrade.
       """
       bind = op.get_bind()

       # Read username from environment
       from src.core.config import settings
       username = settings.superadmin_username

       # Find the user
       result = bind.execute(
           select(users_table.c.id)
           .where(users_table.c.username == username)
           .where(users_table.c.is_admin == True)
       )
       user = result.first()

       if not user:
           print(f"⏭️  No superuser '{username}' found to remove")
           return

       user_id = user[0]

       # Soft delete (set deleted_at)
       from sqlalchemy import update
       now = datetime.now(UTC)

       bind.execute(
           update(users_table)
           .where(users_table.c.id == user_id)
           .values(deleted_at=now)
       )

       print(f"✅ Soft-deleted superuser: {username}")
   ```

3. **Edge Cases & Error Handling**:
   - [ ] **Handle missing environment variables**: Pydantic Settings will raise `ValidationError` if required env vars are missing. Let it fail loudly (don't catch).
   - [ ] **Handle admin already exists**: Check before creating (idempotency). If admin exists, print skip message and return early.
   - [ ] **Handle duplicate username/email**: Query before insert. If exists, raise `ValueError` with clear message.
   - [ ] **Handle weak password**: Pydantic Settings validates minimum 8 characters. Consider adding entropy check in migration.
   - [ ] **Handle missing admin role**: Create role if it doesn't exist (don't assume it exists).
   - [ ] **Handle argon2 import error**: Add try/except around import. If fails, provide clear message: "Install argon2-cffi: uv add argon2-cffi"
   - [ ] **Handle database connection errors**: Alembic handles this. Let exceptions propagate.
   - [ ] **Handle transaction rollback**: Use Alembic's transaction management (automatic).

4. **Dependencies**:
   - Internal: `src.core.config.settings` (Pydantic Settings)
   - External: `argon2-cffi`, `sqlalchemy`, `alembic`

5. **Testing Requirements**:
   - [ ] **Unit test**: Test migration can read environment variables correctly
   - [ ] **Unit test**: Test migration skips when admin exists (idempotency)
   - [ ] **Unit test**: Test migration creates user with correct fields
   - [ ] **Unit test**: Test migration hashes password correctly (verify with `verify_password()`)
   - [ ] **Unit test**: Test migration creates admin role if missing
   - [ ] **Unit test**: Test migration links user to role
   - [ ] **Unit test**: Test migration creates audit log entry
   - [ ] **Unit test**: Test migration raises error on duplicate username/email
   - [ ] **Integration test**: Run migration against test database, verify user can log in
   - [ ] **Integration test**: Run migration twice, verify idempotency (no duplicate users)
   - [ ] **E2E test**: Full deployment flow (fresh DB → migrate → login as superuser)

**Acceptance Criteria**:
- [ ] Migration file created with descriptive name
- [ ] Migration is idempotent (safe to run multiple times)
- [ ] Superuser is created with correct fields (username, email, password_hash, is_admin=true)
- [ ] Password is hashed with Argon2id (matches application standard)
- [ ] Admin role is created with full permissions
- [ ] User-role relationship is established
- [ ] Audit log entry is created
- [ ] Migration prints clear success/skip messages
- [ ] Environment variable validation errors are clear
- [ ] Downgrade function soft-deletes the superuser

**Implementation Notes**:
- Migration filename format: `YYYYMMDD_HHMMSS_seed_initial_superuser.py`
- Use `op.get_bind()` to get synchronous connection (Alembic requirement)
- Import settings inside `upgrade()` function (avoid module-level imports that might fail)
- Print informative messages for operators (they'll see this during deployment)
- Keep migration focused: Only create ONE superuser, don't seed other data
- Follow Alembic best practices: Reversible migrations (upgrade + downgrade)

---

#### Component: Configuration Variable Renaming

**Files Involved**:
- `src/core/config.py`
- `.env.example`
- `README.md` (documentation)

**Purpose**: Rename environment variables from `BOOTSTRAP_ADMIN_*` prefix to `SUPERADMIN_*` prefix for semantic clarity.

**Implementation Requirements**:

1. **Core Logic**:
   - Open `src/core/config.py`
   - Locate the `Settings` class (Pydantic BaseSettings)
   - Find all `bootstrap_admin_*` fields
   - Rename each field and its corresponding environment variable:
     - `bootstrap_admin_username` → `superadmin_username`
     - `bootstrap_admin_email` → `superadmin_email`
     - `bootstrap_admin_password` → `superadmin_password`
     - `bootstrap_admin_full_name` → `superadmin_full_name`
     - `bootstrap_admin_permissions` → `superadmin_permissions`
   - Update field descriptions to reflect migration usage:
     ```python
     superadmin_username: str = Field(
         ...,
         min_length=3,
         max_length=50,
         description="Initial superuser username (used during database migration)"
     )
     ```

2. **Data Handling**:
   - **Input**: Environment variables `SUPERADMIN_USERNAME`, `SUPERADMIN_EMAIL`, etc.
   - **Output**: Pydantic `Settings` object with validated fields
   - **Validation Rules** (keep existing):
     - `username`: 3-50 characters, required
     - `email`: Valid email format (EmailStr), required
     - `password`: Minimum 8 characters, required
     - `full_name`: Optional string
     - `permissions`: List of permission strings, defaults to full admin permissions

3. **Edge Cases & Error Handling**:
   - [ ] **Handle missing required variables**: Pydantic raises `ValidationError` with clear field name
   - [ ] **Handle invalid email**: Pydantic validates against `EmailStr` type
   - [ ] **Handle short password**: Pydantic validates `min_length=8`
   - [ ] **Handle empty permissions list**: Default to full permissions if not provided

4. **Dependencies**:
   - External: `pydantic`, `pydantic-settings`

5. **Testing Requirements**:
   - [ ] **Unit test**: Settings load correctly with new variable names
   - [ ] **Unit test**: Validation fails with missing required variables
   - [ ] **Unit test**: Validation fails with invalid email format
   - [ ] **Unit test**: Validation fails with short password (<8 chars)
   - [ ] **Unit test**: Default permissions are applied when not specified

**Acceptance Criteria**:
- [ ] All config fields renamed from `bootstrap_admin_*` to `superadmin_*`
- [ ] Field descriptions updated to mention "migration" instead of "bootstrap endpoint"
- [ ] Validation rules preserved (min_length, email format, etc.)
- [ ] Default permissions list unchanged
- [ ] No references to old variable names in codebase (verified via grep)

**Implementation Notes**:
- Use global find/replace: `bootstrap_admin_` → `superadmin_`
- Update comments and docstrings to reflect new purpose
- Keep validation strict: These are critical security credentials

---

#### Component: Bootstrap Endpoint Removal

**Files Involved**:
- `src/api/routes/admin.py`
- `src/services/admin_service.py`
- `src/models/bootstrap.py` (mark deprecated, keep for backward compatibility)

**Purpose**: Remove the HTTP endpoint and service logic for bootstrap, as it's replaced by the migration.

**Implementation Requirements**:

1. **Core Logic**:

   **In `src/api/routes/admin.py`**:
   - Locate the `@router.post("/bootstrap", ...)` endpoint (around line 40-90)
   - Delete the entire function `async def bootstrap_first_admin(...)`
   - Delete any imports used only by this endpoint
   - Update the module docstring to remove bootstrap endpoint from the list

   **In `src/services/admin_service.py`**:
   - Locate the `bootstrap_first_admin()` method (around line 126-257)
   - Delete the entire method
   - Locate the `is_bootstrap_completed()` method
   - Delete the entire method
   - Locate the `has_any_admin()` method
   - **KEEP** `has_any_admin()` - it's used by other admin creation logic for validation
   - Remove any imports used only by bootstrap methods (check `from src.models.bootstrap import BootstrapState`)

   **In `src/models/bootstrap.py`**:
   - **DO NOT DELETE** the file (backward compatibility with existing databases)
   - Add deprecation notice at the top:
     ```python
     """
     BootstrapState model (DEPRECATED)

     This model is no longer used as of migration YYYYMMDD_seed_initial_superuser.
     The bootstrap endpoint has been removed in favor of automatic superuser creation
     via Alembic data migration.

     This file is kept for backward compatibility with existing databases that have
     the bootstrap_state table. It can be removed in a future major version after
     a deprecation period.

     DO NOT USE IN NEW CODE.
     """
     ```

2. **Data Handling**:
   - No data handling needed (pure deletion)

3. **Edge Cases & Error Handling**:
   - [ ] **Ensure no other code references deleted methods**: Run grep to find all usages
   - [ ] **Verify imports are cleaned up**: Check for unused imports after deletion
   - [ ] **Verify routes still mount correctly**: Test that admin router still loads

4. **Dependencies**:
   - None (this is code removal)

5. **Testing Requirements**:
   - [ ] **Integration test**: Verify `POST /api/v1/admin/bootstrap` returns 404 (endpoint removed)
   - [ ] **Integration test**: Verify other admin endpoints still work (list, create, update, delete)
   - [ ] **Unit test**: Verify `AdminService` no longer has `bootstrap_first_admin` method
   - [ ] **Code coverage**: Ensure test coverage doesn't drop after deletion

**Acceptance Criteria**:
- [ ] Bootstrap endpoint deleted from `admin.py`
- [ ] `bootstrap_first_admin()` method deleted from `admin_service.py`
- [ ] `is_bootstrap_completed()` method deleted from `admin_service.py`
- [ ] `has_any_admin()` method **preserved** (used elsewhere)
- [ ] `bootstrap.py` model file kept with deprecation notice
- [ ] No references to deleted code found via `grep -r "bootstrap_first_admin"`
- [ ] No references to deleted code found via `grep -r "is_bootstrap_completed"`
- [ ] All imports cleaned up (no unused imports)
- [ ] Router still loads without errors

**Implementation Notes**:
- Use grep to find all references before deleting:
  ```bash
  grep -r "bootstrap_first_admin" src/
  grep -r "is_bootstrap_completed" src/
  grep -r "/bootstrap" src/
  ```
- Check import statements - `BootstrapState` might be imported in other files
- Keep deletion focused: Don't accidentally remove adjacent code
- Preserve git history: Make deletion a separate commit

---

#### Component: Test Suite Updates

**Files Involved**:
- `tests/integration/test_admin_routes.py`
- `tests/e2e/test_admin_workflow.py`
- `tests/conftest.py` (fixture updates if needed)
- `tests/unit/alembic/test_seed_superuser_migration.py` (new test file)

**Purpose**: Update existing tests to remove bootstrap tests and add new tests for the migration.

**Implementation Requirements**:

1. **Core Logic**:

   **In `tests/integration/test_admin_routes.py`**:
   - Locate and delete:
     - `test_bootstrap_first_admin_success()`
     - `test_bootstrap_cannot_bootstrap_twice()`
     - `test_bootstrap_requires_password_in_env()`
   - Update module docstring to remove bootstrap endpoint from the list

   **In `tests/e2e/test_admin_workflow.py`**:
   - Locate any end-to-end tests that use the bootstrap endpoint
   - Replace bootstrap calls with direct user creation or use the migration approach
   - Update test setup to assume superuser exists (created by migration in test DB setup)

   **In `tests/conftest.py`**:
   - Locate the `admin_user` fixture (if it uses bootstrap)
   - Update to create admin user directly via repository or service, NOT via bootstrap endpoint
   - Ensure test database runs migrations before tests (superuser should be created automatically)

   **Create `tests/unit/alembic/test_seed_superuser_migration.py`** (new file):
   ```python
   """
   Unit tests for the seed_initial_superuser Alembic migration.

   Tests the migration logic in isolation without running full migration.
   """

   import pytest
   from sqlalchemy import create_engine, MetaData, Table, Column, String, Boolean, DateTime
   from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
   from datetime import datetime, UTC
   import uuid


   @pytest.fixture
   def mock_db_engine():
       """Create in-memory SQLite database for testing migration logic."""
       engine = create_engine("sqlite:///:memory:")
       # Define minimal schema for testing
       metadata = MetaData()

       users = Table('users', metadata,
           Column('id', String, primary_key=True),
           Column('username', String, nullable=False),
           Column('email', String, nullable=False),
           Column('password_hash', String, nullable=False),
           Column('full_name', String),
           Column('is_active', Boolean, default=True),
           Column('is_admin', Boolean, default=False),
           Column('created_at', DateTime, nullable=False),
           Column('updated_at', DateTime, nullable=False),
           Column('deleted_at', DateTime),
       )

       roles = Table('roles', metadata,
           Column('id', String, primary_key=True),
           Column('name', String, nullable=False, unique=True),
           Column('description', String),
           Column('permissions', String),  # SQLite doesn't have JSONB, use String
           Column('created_at', DateTime, nullable=False),
           Column('updated_at', DateTime, nullable=False),
       )

       user_roles = Table('user_roles', metadata,
           Column('user_id', String, nullable=False),
           Column('role_id', String, nullable=False),
       )

       metadata.create_all(engine)
       return engine


   def test_migration_creates_superuser_when_none_exists(mock_db_engine, monkeypatch):
       """Test migration creates superuser when no admin exists."""
       # Set environment variables
       monkeypatch.setenv("SUPERADMIN_USERNAME", "testadmin")
       monkeypatch.setenv("SUPERADMIN_EMAIL", "admin@test.com")
       monkeypatch.setenv("SUPERADMIN_PASSWORD", "TestPassword123!")
       monkeypatch.setenv("SUPERADMIN_FULL_NAME", "Test Admin")

       # Simulate migration upgrade logic (extract into testable function)
       # ... test implementation ...

       # Verify user was created
       with mock_db_engine.connect() as conn:
           result = conn.execute("SELECT * FROM users WHERE username = 'testadmin'")
           user = result.fetchone()
           assert user is not None
           assert user['is_admin'] is True
           assert user['email'] == 'admin@test.com'


   def test_migration_is_idempotent(mock_db_engine, monkeypatch):
       """Test running migration twice doesn't create duplicate users."""
       # Set environment variables
       monkeypatch.setenv("SUPERADMIN_USERNAME", "testadmin")
       monkeypatch.setenv("SUPERADMIN_EMAIL", "admin@test.com")
       monkeypatch.setenv("SUPERADMIN_PASSWORD", "TestPassword123!")

       # Run migration logic twice
       # ... test implementation ...

       # Verify only one user exists
       with mock_db_engine.connect() as conn:
           result = conn.execute("SELECT COUNT(*) FROM users WHERE username = 'testadmin'")
           count = result.scalar()
           assert count == 1


   def test_migration_raises_error_on_duplicate_username(mock_db_engine, monkeypatch):
       """Test migration fails if username already exists."""
       # Pre-populate database with user
       with mock_db_engine.connect() as conn:
           conn.execute(
               "INSERT INTO users (id, username, email, password_hash, is_admin, created_at, updated_at) "
               "VALUES (?, ?, ?, ?, ?, ?, ?)",
               (str(uuid.uuid4()), "testadmin", "other@test.com", "hash", False, datetime.now(UTC), datetime.now(UTC))
           )

       # Set environment variables with same username
       monkeypatch.setenv("SUPERADMIN_USERNAME", "testadmin")
       monkeypatch.setenv("SUPERADMIN_EMAIL", "admin@test.com")
       monkeypatch.setenv("SUPERADMIN_PASSWORD", "TestPassword123!")

       # Run migration and expect error
       with pytest.raises(ValueError, match="Username .* already exists"):
           # ... test implementation ...
           pass


   # Additional tests:
   # - test_migration_creates_admin_role_if_missing
   # - test_migration_links_user_to_existing_admin_role
   # - test_migration_creates_audit_log_entry
   # - test_migration_hashes_password_correctly
   ```

2. **Data Handling**:
   - Tests create mock data as needed
   - Use test fixtures for database setup
   - Isolate migration logic for unit testing

3. **Edge Cases & Error Handling**:
   - [ ] **Test migration with missing env vars**: Verify clear error message
   - [ ] **Test migration with invalid email**: Verify Pydantic validation error
   - [ ] **Test migration with weak password**: Verify validation error
   - [ ] **Test migration idempotency**: Run twice, verify only one user created
   - [ ] **Test migration with existing username**: Verify error raised
   - [ ] **Test migration with existing email**: Verify error raised

4. **Dependencies**:
   - Internal: Migration script, config module
   - External: `pytest`, `pytest-asyncio`, `httpx` (for integration tests)

5. **Testing Requirements**:
   - [ ] All new migration tests pass
   - [ ] All existing tests still pass after bootstrap removal
   - [ ] Test coverage remains at or above 80%
   - [ ] No broken fixtures after changes

**Acceptance Criteria**:
- [ ] Bootstrap endpoint tests removed (3 tests deleted)
- [ ] Migration unit tests added (minimum 7 tests)
- [ ] Integration tests updated to not use bootstrap endpoint
- [ ] E2E tests updated to assume migration-created superuser
- [ ] All tests pass (`pytest tests/`)
- [ ] Test coverage report shows adequate coverage for migration logic
- [ ] No flaky tests introduced

**Implementation Notes**:
- Consider extracting migration logic into a helper function for easier testing
- Use `monkeypatch` fixture to set environment variables in tests
- Use in-memory SQLite or test PostgreSQL database for migration tests
- Mock `argon2` if needed to speed up tests (but verify hash format in one integration test)

---

#### Component: Documentation Updates

**Files Involved**:
- `README.md`
- `.env.example`
- `alembic/versions/YYYYMMDD_seed_initial_superuser.py` (inline documentation)

**Purpose**: Update all documentation to reflect the new initialization process and environment variable names.

**Implementation Requirements**:

1. **Core Logic**:

   **In `README.md`**:
   - Locate the "Getting Started" or "Installation" section
   - Find any references to bootstrap endpoint or `POST /api/v1/admin/bootstrap`
   - Replace with migration-based instructions:
     ```markdown
     ## Initial Setup

     1. **Configure superuser credentials** (required for first deployment):
        ```bash
        export SUPERADMIN_USERNAME="admin"
        export SUPERADMIN_EMAIL="admin@yourdomain.com"
        export SUPERADMIN_PASSWORD="YourSecurePassword123!"
        export SUPERADMIN_FULL_NAME="System Administrator"
        ```

     2. **Run database migrations** (this will create the superuser):
        ```bash
        uv run alembic upgrade head
        ```

     3. **Start the application**:
        ```bash
        uv run uvicorn src.main:app --reload
        ```

     4. **Log in as superuser**:
        ```bash
        curl -X POST http://localhost:8000/api/v1/auth/login \
          -H "Content-Type: application/json" \
          -d '{"username":"admin","password":"YourSecurePassword123!"}'
        ```

     The superuser is created automatically during the first database migration.
     No additional bootstrap steps are required.
     ```

   - Update any API documentation sections:
     - Remove `/api/v1/admin/bootstrap` from endpoint list
     - Update admin management section to clarify superuser is created via migration

   - Add a "Migration from Bootstrap Endpoint" section for existing users:
     ```markdown
     ## Migration from Bootstrap Endpoint (Existing Installations)

     If you previously used the `/api/v1/admin/bootstrap` endpoint:

     1. **Update environment variables** in your `.env` file:
        - `BOOTSTRAP_ADMIN_USERNAME` → `SUPERADMIN_USERNAME`
        - `BOOTSTRAP_ADMIN_EMAIL` → `SUPERADMIN_EMAIL`
        - `BOOTSTRAP_ADMIN_PASSWORD` → `SUPERADMIN_PASSWORD`
        - `BOOTSTRAP_ADMIN_FULL_NAME` → `SUPERADMIN_FULL_NAME`

     2. **Run the migration**:
        ```bash
        uv run alembic upgrade head
        ```

     The migration is idempotent. If an admin user already exists, the migration
     will skip superuser creation and your existing admin will continue to work.

     3. **Remove any bootstrap scripts** from your deployment automation.

     The bootstrap endpoint has been removed for security reasons. All future
     deployments will use the migration-based approach.
     ```

   **In `.env.example`**:
   - Locate the "Bootstrap Admin Configuration" section (lines 103-116)
   - Update section header and all variable names:
     ```bash
     # -----------------------------------------------------------------------------
     # Superuser Configuration (for Database Migration)
     # -----------------------------------------------------------------------------
     # REQUIRED: Set these values before running database migrations!
     # The initial superuser is created automatically by the Alembic migration
     # during 'alembic upgrade head'. This only happens once - if an admin user
     # already exists, the migration will skip superuser creation.

     SUPERADMIN_USERNAME="admin"
     SUPERADMIN_EMAIL="admin@example.com"
     SUPERADMIN_PASSWORD="CHANGE_THIS_SECURE_PASSWORD_123!"
     SUPERADMIN_FULL_NAME="System Administrator"

     # Optional: Override default permissions (defaults to full admin access)
     # SUPERADMIN_PERMISSIONS='["users:read:all","users:write:all","admin:manage:all"]'
     ```

2. **Data Handling**:
   - No data handling (documentation only)

3. **Edge Cases & Error Handling**:
   - [ ] Ensure examples use valid, secure passwords
   - [ ] Provide clear warnings about changing credentials in production
   - [ ] Include troubleshooting section for common migration errors

4. **Dependencies**:
   - None (documentation only)

5. **Testing Requirements**:
   - [ ] Manual review: Follow README instructions on fresh environment
   - [ ] Manual review: Verify all commands work as documented
   - [ ] Manual review: Check for broken links or references

**Acceptance Criteria**:
- [ ] README.md updated with migration-based setup instructions
- [ ] README.md includes migration guide for existing installations
- [ ] README.md removes all references to bootstrap endpoint
- [ ] `.env.example` updated with new variable names and clear comments
- [ ] All examples use realistic, secure values
- [ ] Documentation is clear and actionable for new users

**Implementation Notes**:
- Use clear, step-by-step instructions
- Include code examples that can be copy-pasted
- Add warnings for production deployments
- Consider adding a troubleshooting section

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

This feature can be completed in a single phase, as all components are tightly coupled and should be deployed together.

#### Phase 1: Replace Bootstrap with Migration (Size: M, Priority: P0)

**Goal**: Remove the HTTP bootstrap endpoint and replace it with an automated Alembic data migration, improving security and simplifying deployment.

**Scope**:
- ✅ Include:
  - Create Alembic data migration for superuser seeding
  - Rename environment variables from `BOOTSTRAP_ADMIN_*` to `SUPERADMIN_*`
  - Remove bootstrap endpoint from API routes
  - Remove bootstrap service methods
  - Update all tests (delete bootstrap tests, add migration tests)
  - Update documentation (README, .env.example)
  - Deprecate `bootstrap_state` table (keep for backward compatibility)

- ❌ Exclude:
  - Deleting `bootstrap_state` table (keep for backward compatibility)
  - Deleting `bootstrap.py` model file (mark deprecated only)
  - Modifying admin user management features (unrelated)
  - Changing password hashing algorithm (no need)

**Components to Implement**:
- [x] Alembic migration: `seed_initial_superuser.py`
- [x] Configuration updates: Rename env vars in `config.py`
- [x] Endpoint removal: Delete bootstrap route and service methods
- [x] Test updates: Remove old tests, add migration tests
- [x] Documentation updates: README and .env.example

**Detailed Tasks**:

1. [ ] **Create Alembic data migration**
   - Run: `alembic revision -m "seed initial superuser"`
   - Open generated migration file in `alembic/versions/`
   - Implement `upgrade()` function with superuser creation logic
   - Implement `downgrade()` function with soft-delete logic
   - Add imports: `sqlalchemy.sql.table`, `argon2.PasswordHasher`, `uuid`, `datetime`
   - Define lightweight table representations (users, roles, user_roles, audit_logs)
   - Add idempotency check (skip if admin exists)
   - Add username/email uniqueness check (raise error if duplicate)
   - Hash password with Argon2id (match application config)
   - Create user record with all required fields
   - Create or get admin role
   - Link user to role via user_roles junction table
   - Create audit log entry
   - Add informative print statements for operators
   - Test migration manually: `alembic upgrade head` and verify user created

2. [ ] **Rename environment variables in configuration**
   - Open `src/core/config.py`
   - Find `Settings` class (Pydantic BaseSettings)
   - Rename fields:
     - `bootstrap_admin_username` → `superadmin_username`
     - `bootstrap_admin_email` → `superadmin_email`
     - `bootstrap_admin_password` → `superadmin_password`
     - `bootstrap_admin_full_name` → `superadmin_full_name`
     - `bootstrap_admin_permissions` → `superadmin_permissions`
   - Update field descriptions to mention "migration" instead of "bootstrap endpoint"
   - Verify no other files reference old variable names: `grep -r "bootstrap_admin" src/`
   - Update `.env.example` with new variable names and updated comments

3. [ ] **Remove bootstrap endpoint and service methods**
   - Open `src/api/routes/admin.py`
   - Delete `@router.post("/bootstrap", ...)` endpoint function
   - Delete any imports used only by bootstrap endpoint
   - Update module docstring to remove bootstrap from endpoint list
   - Open `src/services/admin_service.py`
   - Delete `bootstrap_first_admin()` method
   - Delete `is_bootstrap_completed()` method
   - Keep `has_any_admin()` method (used elsewhere)
   - Remove `BootstrapState` import if not used elsewhere
   - Verify no references to deleted methods: `grep -r "bootstrap_first_admin\|is_bootstrap_completed" src/`
   - Open `src/models/bootstrap.py`
   - Add deprecation notice at top of file
   - Do NOT delete the file (backward compatibility)

4. [ ] **Update test suite**
   - Create `tests/unit/alembic/test_seed_superuser_migration.py`
   - Write unit tests for migration logic:
     - Test superuser creation when none exists
     - Test idempotency (run twice, only one user created)
     - Test error on duplicate username
     - Test error on duplicate email
     - Test admin role creation
     - Test user-role linking
     - Test password hashing
   - Open `tests/integration/test_admin_routes.py`
   - Delete bootstrap endpoint tests:
     - `test_bootstrap_first_admin_success()`
     - `test_bootstrap_cannot_bootstrap_twice()`
     - `test_bootstrap_requires_password_in_env()`
   - Update module docstring to remove bootstrap tests
   - Open `tests/e2e/test_admin_workflow.py`
   - Update any tests that used bootstrap endpoint to use migration approach
   - Open `tests/conftest.py`
   - Update `admin_user` fixture if it used bootstrap (create directly instead)
   - Run full test suite: `uv run pytest tests/`
   - Verify all tests pass
   - Check coverage: `uv run pytest --cov=src tests/`

5. [ ] **Update documentation**
   - Open `README.md`
   - Locate "Getting Started" or "Installation" section
   - Replace bootstrap endpoint instructions with migration-based instructions
   - Add example commands for setting env vars and running migration
   - Remove `/api/v1/admin/bootstrap` from API endpoint list
   - Add "Migration from Bootstrap Endpoint" section for existing users
   - Include troubleshooting section for common migration errors
   - Open `.env.example`
   - Update "Bootstrap Admin Configuration" section:
     - Change header to "Superuser Configuration"
     - Update all variable names to `SUPERADMIN_*`
     - Update comments to mention "migration" instead of "endpoint"
   - Review all changes for clarity and completeness

6. [ ] **Integration testing on clean database**
   - Drop test database: `dropdb emerald_test_db`
   - Create fresh test database: `createdb emerald_test_db`
   - Run migrations: `uv run alembic upgrade head`
   - Verify superuser created: `psql emerald_test_db -c "SELECT username, email, is_admin FROM users;"`
   - Start application: `uv run uvicorn src.main:app --reload`
   - Test login with superuser credentials
   - Verify bootstrap endpoint returns 404: `curl -X POST http://localhost:8000/api/v1/admin/bootstrap`
   - Verify other admin endpoints still work (list users, create admin, etc.)

7. [ ] **Manual testing on existing database**
   - Use existing database with bootstrap_state table
   - Run new migration: `uv run alembic upgrade head`
   - Verify migration skips superuser creation (admin already exists)
   - Verify existing admin can still log in
   - Verify application starts without errors

**Dependencies**:
- Requires: Clean understanding of current bootstrap implementation (already gathered)
- Requires: Alembic setup (already exists)
- Requires: Test infrastructure (already exists)
- Blocks: Any future admin management features that might reference bootstrap

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (minimum 80% coverage for new migration code)
- [ ] Migration works on fresh database (creates superuser)
- [ ] Migration is idempotent on existing database (skips if admin exists)
- [ ] Superuser can log in via `/api/v1/auth/login`
- [ ] Bootstrap endpoint returns 404
- [ ] All admin management endpoints still work
- [ ] Documentation is clear and complete
- [ ] No references to old `BOOTSTRAP_ADMIN_*` variables in codebase
- [ ] Code reviewed and approved
- [ ] Manual testing completed on both fresh and existing databases

**Risk Factors**:
- **Risk**: Migration fails in production due to missing environment variables
  - **Mitigation**: Add clear error messages, validate env vars in CI/CD before deployment, document required variables prominently
- **Risk**: Existing installations break due to renamed environment variables
  - **Mitigation**: Document migration path clearly, add backward compatibility notes, test on existing database
- **Risk**: Password hashing in migration doesn't match application (login fails)
  - **Mitigation**: Use exact same `PasswordHasher` config as application, add integration test for login after migration
- **Risk**: Migration is not idempotent (creates duplicate users on re-run)
  - **Mitigation**: Test idempotency thoroughly, add explicit check for existing admin before insert
- **Risk**: Tests fail due to missing fixtures after bootstrap removal
  - **Mitigation**: Update fixtures to create admin users directly, verify all tests pass before merging

**Estimated Effort**: 1-2 days for 1 developer

---

### 4.2 Implementation Sequence

```
Single Phase (P0, 1-2 days)
  │
  ├─► Task 1: Create Alembic migration (3-4 hours)
  │    ├─► Write upgrade() logic
  │    ├─► Write downgrade() logic
  │    └─► Manual testing
  │
  ├─► Task 2: Rename environment variables (30 minutes)
  │    ├─► Update config.py
  │    └─► Update .env.example
  │
  ├─► Task 3: Remove bootstrap code (1 hour)
  │    ├─► Delete endpoint
  │    ├─► Delete service methods
  │    └─► Add deprecation notice
  │
  ├─► Task 4: Update tests (2-3 hours)
  │    ├─► Create migration unit tests
  │    ├─► Delete bootstrap tests
  │    └─► Fix broken fixtures
  │
  ├─► Task 5: Update documentation (1 hour)
  │    ├─► Update README.md
  │    └─► Update .env.example
  │
  └─► Task 6: Integration & manual testing (1-2 hours)
       ├─► Test on fresh database
       ├─► Test on existing database
       └─► Verify all endpoints work
```

**Rationale for ordering**:
1. **Create migration first** - Core functionality, needed for testing other changes
2. **Rename env vars second** - Migration depends on these being correct
3. **Remove bootstrap code third** - Safe to remove after migration works
4. **Update tests fourth** - Verify all changes work correctly
5. **Update docs fifth** - Document the working solution
6. **Integration testing last** - Final validation before deployment

**Quick Wins**:
- After Task 1 (migration), you can deploy with both systems (migration + endpoint) for safer rollout
- After Task 2 (env var rename), new deployments are cleaner (better naming)
- After Task 3 (remove endpoint), security is improved (no unauthenticated endpoint)

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. Alembic data migrations are the standard approach for seeding initial data in database-driven applications. The solution removes code rather than adding complexity.

- [x] **Have we avoided premature optimization?**
  - Yes. The migration is straightforward: check, insert, done. No caching, no distributed locks, no over-engineering.

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. The project already uses Alembic for schema migrations, Pydantic Settings for configuration, and Argon2id for password hashing. This solution reuses all existing patterns.

- [x] **Can we deliver value in smaller increments?**
  - The implementation is already broken into small tasks (6 tasks, each 30 minutes to 4 hours). Each task can be committed separately.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. The actual problem is: "The HTTP bootstrap endpoint is a security risk and complicates deployment." The solution directly addresses both issues by removing the endpoint and automating initialization.

### Alternatives Considered

**Alternative 1: Keep HTTP endpoint, add authentication**
- **Description**: Require admin authentication for `/api/v1/admin/bootstrap`
- **Why rejected**:
  - Chicken-and-egg problem: Need admin to create first admin
  - Still requires manual HTTP call during deployment
  - Doesn't follow infrastructure-as-code best practices
  - Adds complexity instead of removing it

**Alternative 2: CLI command (`python -m src.cli bootstrap`)**
- **Description**: Create a CLI command for bootstrapping instead of HTTP endpoint
- **Why rejected**:
  - Still requires manual step during deployment (not automated)
  - Needs separate documentation and error handling
  - Less portable (requires Python environment to be set up first)
  - Alembic migration is more standard and already runs during deployment

**Alternative 3: Docker entrypoint script**
- **Description**: Add shell script to Docker entrypoint that creates superuser
- **Why rejected**:
  - Ties solution to Docker (not portable to other deployment methods)
  - Shell scripts are harder to test and maintain
  - Duplicates logic that Alembic already provides
  - No transaction safety or rollback capability

**Alternative 4: Application startup hook**
- **Description**: Create superuser automatically on first application startup
- **Why rejected**:
  - Race condition if multiple app instances start simultaneously
  - Mixes application code with infrastructure setup
  - Slower application startup
  - Harder to debug (happens in background during startup)
  - Database migrations are the standard place for this

### Rationale

The **Alembic data migration approach** is preferred because:

1. **Security**: No unauthenticated HTTP endpoint exposed to the network
2. **Automation**: Superuser creation happens automatically during `alembic upgrade head` (already part of deployment)
3. **Simplicity**: Removes ~200 lines of code (endpoint, service methods, tests)
4. **Standard Practice**: Data migrations are the industry-standard solution for seeding initial data
5. **Transaction Safety**: Alembic provides transaction management and rollback capability
6. **Portability**: Works in any deployment environment (Docker, VM, serverless, local)
7. **Testability**: Migration logic can be tested in isolation with unit tests
8. **Idempotency**: Safe to run multiple times (checks if admin exists before creating)
9. **Version Control**: Migration is checked into git with clear history
10. **Consistency**: Same approach works for development, staging, and production

---

## 6. References & Related Documents

### Internal Documentation
- [Admin Creation Support Feature Plan](../plans/20251107_admin-creation-support.md) - Original bootstrap implementation
- [Backend Development Standards](../../.claude/standards/backend.md) - Python/FastAPI standards
- [Database Standards](../../.claude/standards/database.md) - PostgreSQL and Alembic guidelines
- [Security Standards](../../.claude/standards/security.md) - Password hashing and security best practices

### External Resources

**Alembic Documentation**:
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) - Official Alembic documentation
- [How do I execute inserts and updates in an Alembic upgrade script?](https://stackoverflow.com/questions/24612395/how-do-i-execute-inserts-and-updates-in-an-alembic-upgrade-script) - Stack Overflow guide on data migrations
- [Best Practices for Alembic Schema Migration](https://www.pingcap.com/article/best-practices-alembic-schema-migration/) - Industry best practices

**Data Migration Patterns**:
- [Alembic — Data migration basics](https://medium.com/@csakash03/alembic-data-migration-basics-780c89333583) - Medium article on data migrations
- [Creating seed data in a flask-migrate or alembic migration](https://stackoverflow.com/questions/19334604/creating-seed-data-in-a-flask-migrate-or-alembic-migration) - Stack Overflow examples
- [Database Migrations with Alembic and FastAPI](https://adex.ltd/database-migrations-with-alembic-and-fastapi-a-comprehensive-guide-using-poetry) - FastAPI-specific guide

**Security Best Practices**:
- [Alembic Migration Best Practices: Storing Connection Strings Safely](https://iifx.dev/en/articles/124465043) - Security considerations for migrations
- [Argon2 Password Hashing](https://www.password-hashing.net/) - NIST-recommended algorithm
- OWASP Password Storage Cheat Sheet - Best practices for password hashing

**SQLAlchemy Resources**:
- [SQLAlchemy Core](https://docs.sqlalchemy.org/en/20/core/) - Core API for data insertion
- [SQLAlchemy 2.0 Migration Guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html) - Modern SQLAlchemy patterns

### Related Issues
- Security concern: Unauthenticated bootstrap endpoint could be exploited if left enabled in production
- Deployment complexity: Manual bootstrap step is easy to forget or misconfigure
- Documentation burden: Bootstrap endpoint requires extensive documentation and troubleshooting

### Design Decisions Log
- **2025-11-11**: Decision to remove HTTP bootstrap endpoint in favor of Alembic migration
- **2025-11-11**: Decision to rename `BOOTSTRAP_ADMIN_*` to `SUPERADMIN_*` for clarity
- **2025-11-11**: Decision to keep `bootstrap_state` table for backward compatibility (mark deprecated)

---

## Appendix A: Migration Code Template

For quick reference, here's the complete migration file structure:

```python
"""seed initial superuser

Revision ID: YYYYMMDD_HHMMSS
Revises: <previous_revision>
Create Date: YYYY-MM-DD HH:MM:SS.SSSSSS

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import select, insert, update
from sqlalchemy.sql import table, column
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from argon2 import PasswordHasher
from datetime import datetime, UTC
import uuid

# revision identifiers, used by Alembic.
revision: str = 'YYYYMMDD_HHMMSS'
down_revision: Union[str, None] = '<previous_revision>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define lightweight table representations
users_table = table('users',
    column('id', PG_UUID),
    column('username', String),
    column('email', String),
    column('password_hash', String),
    column('full_name', String),
    column('is_active', Boolean),
    column('is_admin', Boolean),
    column('created_at', DateTime),
    column('updated_at', DateTime),
    column('deleted_at', DateTime),
)

roles_table = table('roles',
    column('id', PG_UUID),
    column('name', String),
    column('description', String),
    column('permissions', JSONB),
    column('created_at', DateTime),
    column('updated_at', DateTime),
)

user_roles_table = table('user_roles',
    column('user_id', PG_UUID),
    column('role_id', PG_UUID),
)

audit_logs_table = table('audit_logs',
    column('id', PG_UUID),
    column('user_id', PG_UUID),
    column('action', String),
    column('entity_type', String),
    column('entity_id', PG_UUID),
    column('description', String),
    column('new_values', JSONB),
    column('ip_address', String),
    column('user_agent', String),
    column('request_id', String),
    column('created_at', DateTime),
)


def upgrade() -> None:
    """Create initial superuser if no admin users exist."""

    # Get database connection
    bind = op.get_bind()

    # Check if any admin user exists (idempotency)
    result = bind.execute(
        select(users_table.c.id)
        .where(users_table.c.is_admin == True)
        .where(users_table.c.deleted_at.is_(None))
        .limit(1)
    )
    existing_admin = result.first()

    if existing_admin:
        print("⏭️  Skipping superuser creation: Admin user(s) already exist")
        return

    # Read environment variables
    from src.core.config import settings

    username = settings.superadmin_username
    email = settings.superadmin_email
    password = settings.superadmin_password
    full_name = settings.superadmin_full_name
    permissions = settings.superadmin_permissions

    # Validate uniqueness
    result = bind.execute(
        select(users_table.c.id)
        .where(
            (users_table.c.username == username) |
            (users_table.c.email == email)
        )
        .where(users_table.c.deleted_at.is_(None))
    )
    existing_user = result.first()

    if existing_user:
        raise ValueError(
            f"Cannot create superuser: Username '{username}' or email '{email}' already exists. "
            f"Check your SUPERADMIN_USERNAME and SUPERADMIN_EMAIL environment variables."
        )

    # Hash password
    pwd_hasher = PasswordHasher(
        time_cost=2,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
    )
    password_hash = pwd_hasher.hash(password)

    # Create user
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    bind.execute(
        insert(users_table).values(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            is_active=True,
            is_admin=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
    )

    # Get or create admin role
    result = bind.execute(
        select(roles_table.c.id)
        .where(roles_table.c.name == 'admin')
    )
    admin_role = result.first()

    if admin_role:
        role_id = admin_role[0]
    else:
        role_id = uuid.uuid4()
        bind.execute(
            insert(roles_table).values(
                id=role_id,
                name='admin',
                description='System Administrator with full access',
                permissions=permissions,
                created_at=now,
                updated_at=now,
            )
        )

    # Link user to role
    bind.execute(
        insert(user_roles_table).values(
            user_id=user_id,
            role_id=role_id,
        )
    )

    # Create audit log
    bind.execute(
        insert(audit_logs_table).values(
            id=uuid.uuid4(),
            user_id=None,
            action='CREATE',
            entity_type='user',
            entity_id=user_id,
            description=f"Migration: Initial superuser '{username}' created from environment config",
            new_values={
                'username': username,
                'email': email,
                'full_name': full_name,
                'is_admin': True,
                'is_active': True,
            },
            ip_address=None,
            user_agent='alembic-migration',
            request_id=None,
            created_at=now,
        )
    )

    print(f"✅ Successfully created superuser: {username} ({email})")


def downgrade() -> None:
    """Soft-delete superuser created by this migration."""

    bind = op.get_bind()

    from src.core.config import settings
    username = settings.superadmin_username

    result = bind.execute(
        select(users_table.c.id)
        .where(users_table.c.username == username)
        .where(users_table.c.is_admin == True)
    )
    user = result.first()

    if not user:
        print(f"⏭️  No superuser '{username}' found to remove")
        return

    user_id = user[0]
    now = datetime.now(UTC)

    bind.execute(
        update(users_table)
        .where(users_table.c.id == user_id)
        .values(deleted_at=now)
    )

    print(f"✅ Soft-deleted superuser: {username}")
```

---

## Appendix B: Testing Checklist

Use this checklist during implementation to ensure all scenarios are tested:

### Migration Tests
- [ ] Migration creates superuser when no admin exists
- [ ] Migration is idempotent (skips if admin already exists)
- [ ] Migration raises error if username already exists (non-admin user)
- [ ] Migration raises error if email already exists (non-admin user)
- [ ] Migration creates admin role if it doesn't exist
- [ ] Migration reuses admin role if it already exists
- [ ] Migration links user to admin role correctly
- [ ] Migration creates audit log entry
- [ ] Migration hashes password correctly (verify with `pwd_hasher.verify()`)
- [ ] Migration reads environment variables correctly
- [ ] Migration fails gracefully with missing environment variables
- [ ] Migration fails gracefully with invalid email format
- [ ] Downgrade soft-deletes the superuser
- [ ] Downgrade is idempotent (safe to run multiple times)

### Integration Tests
- [ ] Fresh database: Migration creates superuser
- [ ] Fresh database: Superuser can log in via `/api/v1/auth/login`
- [ ] Fresh database: Superuser has correct permissions
- [ ] Existing database: Migration skips (admin already exists)
- [ ] Existing database: Existing admin can still log in
- [ ] Bootstrap endpoint returns 404
- [ ] Admin list endpoint works (GET `/api/v1/admin/users`)
- [ ] Admin create endpoint works (POST `/api/v1/admin/users`)
- [ ] Admin update endpoint works (PUT `/api/v1/admin/users/{id}`)
- [ ] Admin delete endpoint works (DELETE `/api/v1/admin/users/{id}`)

### End-to-End Tests
- [ ] Complete deployment flow: Set env vars → Run migration → Start app → Login
- [ ] Migration runs successfully in Docker container
- [ ] Migration runs successfully with docker-compose
- [ ] Error handling: Clear error message when env vars missing
- [ ] Error handling: Clear error message when username conflict
- [ ] Error handling: Clear error message when email conflict

---

**End of Implementation Plan**

This plan provides comprehensive guidance for removing the bootstrap endpoint and replacing it with an Alembic data migration. Follow the implementation roadmap, complete all tasks in sequence, and verify all acceptance criteria before deployment.
