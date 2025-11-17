# Implementation Plan: Account Management System

**Date:** November 3, 2025
**Feature:** Phase 2 - Account Management & Sharing
**Estimated Timeline:** 4 weeks
**Priority:** P0 (Critical - Enables Phase 3 Transactions)

---

## Executive Summary

This implementation plan details Phase 2 of the personal finance platform: **Account Management and Sharing**. This feature enables users to create financial accounts (savings, credit cards, loans, investments), track balances, and share accounts with other users using role-based permissions (owner, editor, viewer).

**Primary Objectives:**
- Enable users to manage multiple financial accounts across different types
- Implement balance tracking calculated from transaction history (foundation for Phase 3)
- Provide granular account sharing with three-tier permissions (owner/editor/viewer)
- Ensure comprehensive audit logging of all account operations and permission changes
- Support multi-currency accounts with ISO 4217 compliance
- Implement soft-delete patterns for regulatory compliance and data preservation

**Expected Outcomes:**
- Users can create and manage accounts within 2 minutes
- 60% of users create 3+ accounts within 30 days
- 30% of users share at least one account
- API response time <200ms (p95) for all account operations
- 100% audit coverage for sensitive operations
- 80%+ test coverage for account-related code

**Success Criteria:**
- All 22 acceptance criteria met (see Phase 2 description)
- Performance benchmarks achieved (balance calculation, permission checks)
- Security review passed (permission model, data protection)
- Integration tests passing for all sharing scenarios

---

## 1. Technical Architecture

### 1.1 System Design Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Account   │  │   Account    │  │    Account       │   │
│  │   Routes    │  │   Share      │  │    Balance       │   │
│  │             │  │   Routes     │  │    Routes        │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                │                     │             │
└─────────┼────────────────┼─────────────────────┼─────────────┘
          │                │                     │
┌─────────┼────────────────┼─────────────────────┼─────────────┐
│         │      Service Layer (Business Logic)  │             │
│  ┌──────▼──────┐  ┌──────▼────────┐  ┌────────▼─────────┐  │
│  │  Account    │  │  Permission   │  │   Balance        │  │
│  │  Service    │◄─┤  Service      │  │   Service        │  │
│  │             │  │               │  │                  │  │
│  └──────┬──────┘  └───────────────┘  └──────────────────┘  │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────┼────────────────────────────────────────────────────┐
│         │         Repository Layer (Data Access)             │
│  ┌──────▼──────┐         ┌──────────────┐                   │
│  │  Account    │         │ AccountShare │                   │
│  │  Repository │◄────────┤  Repository  │                   │
│  │             │         │              │                   │
│  └──────┬──────┘         └──────────────┘                   │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│              Database Layer (PostgreSQL)                      │
│                                                               │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────┐    │
│  │ accounts │────│account_shares│────│   audit_logs   │    │
│  │          │    │              │    │                │    │
│  └────┬─────┘    └──────────────┘    └────────────────┘    │
│       │                                                      │
│  ┌────▼─────┐                                               │
│  │  users   │                                               │
│  └──────────┘                                               │
└───────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **Account CRUD:** Create, read, update, soft-delete operations
- **Permission System:** Three-tier access control (owner/editor/viewer)
- **Balance Tracking:** Calculated from opening balance + transactions (Phase 3)
- **Audit Logging:** All operations logged via existing AuditService
- **Multi-Currency:** ISO 4217 currency codes with immutability

**Integration Points:**
- **Phase 1:** Uses existing auth system (JWT), audit logging, user management
- **Phase 3 (Future):** Transaction model will update account balances
- **External Services:** None (self-contained, no external APIs in Phase 2)

**Data Flow:**
1. Client → API Route (authentication, request validation)
2. Route → Service (permission check, business logic)
3. Service → Repository (database operations)
4. Repository → Database (SQLAlchemy async queries)
5. Service → AuditService (log operations)
6. Service → Route → Client (response)

### 1.2 Technology Stack

All technologies are already integrated in Phase 1. No new dependencies required.

#### Backend Framework
**FastAPI 0.115+**
- **Purpose:** RESTful API development with automatic OpenAPI documentation
- **Why:** Already used in Phase 1, excellent async support, auto-validation
- **Version:** Latest stable (already in project)
- **Alternatives considered:**
  - Flask: Rejected (lacks async support, requires more boilerplate)
  - Django REST: Rejected (too heavyweight for API-only backend)

#### Database
**PostgreSQL 17+ with SQLAlchemy 2.0+**
- **Purpose:** Data persistence, relationships, transactions
- **Why:** Already used in Phase 1, JSONB support, excellent async support
- **Version:** PostgreSQL 17 LTS, SQLAlchemy 2.0.35+
- **Alternatives considered:**
  - MySQL: Rejected (less feature-rich, weaker async support)
  - MongoDB: Rejected (relational data model required)

#### Validation
**Pydantic V2**
- **Purpose:** Request/response validation, data serialization
- **Why:** Already integrated, excellent FastAPI integration, type safety
- **Version:** 2.9+ (already in project)
- **Alternatives considered:** None (industry standard for FastAPI)

#### Testing
**Pytest with pytest-asyncio**
- **Purpose:** Unit, integration, and E2E testing
- **Why:** Already used in Phase 1, excellent async support
- **Version:** Latest stable (already in project)
- **Alternatives considered:** None (Python testing standard)

#### Currency Support
**ISO 4217 Standard (No Library Required)**
- **Purpose:** Currency code validation
- **Why:** Simple regex validation, no external dependencies
- **Version:** N/A (standard compliance)
- **Future Enhancement:** Add exchange rate API integration in Phase 3

### 1.3 Database Schema Design

#### Accounts Table

```sql
CREATE TYPE account_type AS ENUM (
    'savings',
    'credit_card',
    'debit_card',
    'loan',
    'investment',
    'other'
);

CREATE TABLE accounts (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Account Details
    account_name VARCHAR(100) NOT NULL,
    account_type account_type NOT NULL,
    currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),

    -- Balance Tracking
    opening_balance NUMERIC(15, 2) NOT NULL,
    current_balance NUMERIC(15, 2) NOT NULL,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Standard Columns (from mixins)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for Performance
CREATE INDEX idx_accounts_user ON accounts(user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_accounts_type ON accounts(account_type)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_accounts_active ON accounts(is_active)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_accounts_currency ON accounts(currency)
    WHERE deleted_at IS NULL;

-- Unique Constraint: Account names must be unique per user (case-insensitive)
CREATE UNIQUE INDEX idx_accounts_user_name_unique
    ON accounts(user_id, LOWER(account_name))
    WHERE deleted_at IS NULL;

-- Constraint: Currency must be valid ISO 4217 code (3 uppercase letters)
-- Already included in column definition above
```

**Design Rationale:**
- **UUID Primary Key:** Consistent with Phase 1, prevents enumeration attacks
- **user_id FK with CASCADE:** Account deleted when owner deleted (rare, soft-delete preferred)
- **account_name VARCHAR(100):** Sufficient for descriptive names
- **Numeric(15,2):** Handles balances up to $999,999,999,999.99 with cent precision
- **Partial Indexes:** Only index active (non-deleted) records for performance
- **Case-Insensitive Uniqueness:** LOWER(account_name) prevents "Savings" and "savings" duplicates

#### Account Shares Table

```sql
CREATE TYPE permission_level AS ENUM (
    'owner',
    'editor',
    'viewer'
);

CREATE TABLE account_shares (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Permission
    permission_level permission_level NOT NULL,

    -- Standard Columns
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete for revocation
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for Performance
CREATE INDEX idx_account_shares_account ON account_shares(account_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_account_shares_user ON account_shares(user_id)
    WHERE deleted_at IS NULL;

-- Composite Index for Permission Lookups
CREATE INDEX idx_account_shares_permission_lookup
    ON account_shares(account_id, user_id, deleted_at);

-- Unique Constraint: One active share per user per account
CREATE UNIQUE INDEX idx_account_shares_unique
    ON account_shares(account_id, user_id)
    WHERE deleted_at IS NULL;
```

**Design Rationale:**
- **Soft Delete for Shares:** Preserves revocation history for audit trail
- **Composite Index:** Optimizes permission checks (most frequent query)
- **Unique Constraint:** Prevents duplicate active shares for same user/account
- **CASCADE on user_id:** Deleted users lose all shared access
- **CASCADE on account_id:** Deleted accounts remove all shares

#### Audit Integration

No new audit table required. Use existing `audit_logs` table with new actions:

```python
# New AuditAction enum values (add to existing enum)
ACCOUNT_CREATE = "account.create"
ACCOUNT_UPDATE = "account.update"
ACCOUNT_DELETE = "account.delete"
ACCOUNT_SHARE_CREATE = "account.share.create"
ACCOUNT_SHARE_UPDATE = "account.share.update"
ACCOUNT_SHARE_DELETE = "account.share.delete"
```

### 1.4 File Structure

```
src/
├── models/
│   ├── account.py                    # Account and AccountShare models
│   └── enums.py                      # AccountType and PermissionLevel enums
├── repositories/
│   ├── account_repository.py         # Account CRUD operations
│   └── account_share_repository.py   # AccountShare CRUD + permission queries
├── services/
│   ├── account_service.py            # Account business logic
│   └── permission_service.py         # Permission checking logic
├── schemas/
│   ├── account.py                    # Account request/response schemas
│   └── account_share.py              # Share request/response schemas
├── api/
│   └── routes/
│       ├── accounts.py               # Account CRUD endpoints
│       └── account_shares.py         # Sharing endpoints
└── exceptions.py                     # Add account-specific exceptions

alembic/
└── versions/
    └── YYYYMMDD_create_accounts_and_shares.py  # Migration

tests/
├── unit/
│   ├── services/
│   │   ├── test_account_service.py
│   │   └── test_permission_service.py
│   └── repositories/
│       ├── test_account_repository.py
│       └── test_account_share_repository.py
├── integration/
│   ├── test_account_routes.py
│   └── test_account_share_routes.py
└── e2e/
    ├── test_account_lifecycle.py
    └── test_sharing_flows.py
```

---

## 2. Implementation Specification

### 2.1 Phase Breakdown

#### Phase 2A: Core Account Management (Week 1-2)
**Goal:** Enable users to create, read, update, and delete their financial accounts.

**Scope:**
- ✅ Include: Account model, CRUD operations, validation, basic tests
- ❌ Exclude: Sharing functionality, complex permission logic

**Components:**
1. **Database Layer**
   - Account model with all fields
   - AccountType enum (savings, credit_card, etc.)
   - Alembic migration for accounts table
   - Indexes and constraints

2. **Repository Layer**
   - AccountRepository extending BaseRepository
   - Custom queries: get_by_user, get_by_name, count_user_accounts

3. **Service Layer**
   - AccountService with CRUD logic
   - Validation: unique names, valid currency, balance precision
   - Audit logging integration

4. **API Layer**
   - POST /api/v1/accounts (create)
   - GET /api/v1/accounts (list with pagination)
   - GET /api/v1/accounts/{id} (retrieve)
   - PUT /api/v1/accounts/{id} (update)
   - DELETE /api/v1/accounts/{id} (soft delete)

5. **Testing**
   - Unit tests for AccountService
   - Unit tests for AccountRepository
   - Integration tests for all endpoints
   - E2E test: Create → Read → Update → Delete flow

**Validation Criteria:**
- [ ] All CRUD endpoints return correct status codes
- [ ] Pagination works correctly (default 20, max 100)
- [ ] Soft delete excludes accounts from normal queries
- [ ] Account name uniqueness enforced per user
- [ ] Currency validation rejects invalid codes
- [ ] Audit logs created for all operations
- [ ] Tests pass with 80%+ coverage

**Estimated Effort:** 10 days (1 developer)

---

#### Phase 2B: Account Sharing & Permissions (Week 2-3)
**Goal:** Enable users to share accounts with granular permission control.

**Scope:**
- ✅ Include: AccountShare model, permission checking, sharing endpoints
- ❌ Exclude: Notification system, share acceptance flow (future enhancement)

**Components:**
1. **Database Layer**
   - AccountShare model with relationships
   - PermissionLevel enum (owner, editor, viewer)
   - Alembic migration for account_shares table
   - Composite indexes for permission lookups

2. **Repository Layer**
   - AccountShareRepository extending BaseRepository
   - Custom queries: get_by_account, get_by_user, get_permission

3. **Service Layer**
   - PermissionService for permission checking
   - AccountService enhanced with permission checks
   - Share creation/update/revocation logic
   - Audit logging for all permission changes

4. **API Layer**
   - POST /api/v1/accounts/{id}/share (create share)
   - GET /api/v1/accounts/{id}/share (list shares)
   - PUT /api/v1/accounts/{id}/share/{share_id} (update permission)
   - DELETE /api/v1/accounts/{id}/share/{share_id} (revoke)
   - Update existing endpoints with permission checks

5. **Testing**
   - Unit tests for PermissionService
   - Unit tests for AccountShareRepository
   - Integration tests for sharing endpoints
   - E2E test: Share → Modify → Revoke flow
   - Concurrent access scenario tests

**Validation Criteria:**
- [ ] Owner can perform all operations
- [ ] Editor can read/write but not delete/share
- [ ] Viewer can only read
- [ ] Permission checks execute in <50ms (p95)
- [ ] Cannot share with non-existent or deleted users
- [ ] Share revocation works correctly
- [ ] Audit logs track all permission changes
- [ ] Tests pass with 80%+ coverage

**Estimated Effort:** 5 days (1 developer)

---

#### Phase 2C: Polish & Documentation (Week 3-4)
**Goal:** Production-ready feature with comprehensive documentation and performance optimization.

**Scope:**
- ✅ Include: OpenAPI docs, error refinement, performance tuning, README updates
- ❌ Exclude: New features, notification system

**Components:**
1. **Documentation**
   - OpenAPI descriptions for all endpoints
   - Permission matrix documentation
   - Balance calculation logic documentation
   - README update with account management section
   - Code examples in docstrings

2. **Error Handling**
   - User-friendly error messages
   - Comprehensive error code documentation
   - Proper HTTP status codes for all scenarios
   - Error response examples in OpenAPI

3. **Performance Optimization**
   - Review and optimize database queries
   - Add missing indexes if needed
   - Implement permission caching strategy
   - Load testing (100 concurrent users)
   - Query profiling with EXPLAIN

4. **Testing**
   - E2E tests for all user scenarios
   - Performance benchmarks
   - Edge case testing
   - Security testing (permission bypass attempts)

**Validation Criteria:**
- [ ] All endpoints documented in OpenAPI
- [ ] Error messages are clear and actionable
- [ ] Performance meets benchmarks (<200ms p95)
- [ ] All acceptance criteria from Phase 2 description met
- [ ] Security review passed
- [ ] Full test suite passes
- [ ] Code coverage ≥80%

**Estimated Effort:** 5 days (1 developer)

---

### 2.2 Detailed Component Specifications

#### Component: Account Model

**Files:** `src/models/account.py`, `src/models/enums.py`

**Purpose:** Define Account and AccountShare database models with relationships.

**Implementation Requirements:**

1. **AccountType Enum (enums.py:1-20)**
   ```python
   class AccountType(str, enum.Enum):
       """Financial account types."""
       SAVINGS = "savings"
       CREDIT_CARD = "credit_card"
       DEBIT_CARD = "debit_card"
       LOAN = "loan"
       INVESTMENT = "investment"
       OTHER = "other"
   ```

2. **PermissionLevel Enum (enums.py:22-40)**
   ```python
   class PermissionLevel(str, enum.Enum):
       """Account sharing permission levels."""
       OWNER = "owner"     # Full access: read, write, delete, share
       EDITOR = "editor"   # Read/write access: read, write
       VIEWER = "viewer"   # Read-only access: read
   ```

3. **Account Model (account.py:1-100)**
   - Inherit from: Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin
   - Columns: id (UUID), user_id (FK), account_name, account_type, currency, opening_balance, current_balance, is_active
   - Relationships: user (User), shares (list[AccountShare])
   - Validation: currency regex (^[A-Z]{3}$), account_name length (1-100)
   - Methods: calculate_balance() (placeholder for Phase 3)

4. **AccountShare Model (account.py:102-150)**
   - Inherit from: Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin
   - Columns: id (UUID), account_id (FK), user_id (FK), permission_level
   - Relationships: account (Account), user (User)
   - Methods: can_read(), can_write(), can_delete(), can_share()

**Data Handling:**
- **Input:** SQLAlchemy creates instances via repository
- **Output:** Pydantic schemas serialize for API responses
- **State Management:** Database-backed, async session management

**Edge Cases & Error Handling:**
- [ ] Currency validation: Only accept ISO 4217 codes (3 uppercase letters)
- [ ] Balance precision: Ensure NUMERIC(15,2) handles all values correctly
- [ ] Relationship loading: Use selectinload to avoid N+1 queries
- [ ] Soft delete: Ensure deleted_at filter applied in all queries

**Testing Requirements:**
- [ ] Test: Account creation with all valid field combinations
- [ ] Test: Currency validation rejects invalid codes (e.g., "usd", "US", "1234")
- [ ] Test: Account name length validation (0, 1, 100, 101 characters)
- [ ] Test: Balance precision handles cents correctly
- [ ] Test: Soft delete sets deleted_at timestamp
- [ ] Test: Relationships load correctly (user, shares)

**Acceptance Criteria:**
- [ ] Account model persists all required fields
- [ ] Currency validation works correctly
- [ ] Account name uniqueness enforced per user
- [ ] Soft delete preserves data
- [ ] Relationships load without N+1 queries

**Implementation Notes:**
- Use existing mixins (TimestampMixin, SoftDeleteMixin, AuditFieldsMixin)
- Follow Phase 1 patterns (see User model for reference)
- Add __repr__ for debugging
- Document all fields in docstrings

---

#### Component: Account Repository

**Files:** `src/repositories/account_repository.py`

**Purpose:** Handle all database operations for Account model.

**Implementation Requirements:**

1. **Core CRUD Operations**
   - Extend BaseRepository[Account]
   - Inherit: get_by_id, create, update, soft_delete, count, exists
   - All queries must filter out soft-deleted records

2. **Custom Query Methods**
   ```python
   async def get_by_user(
       self,
       user_id: UUID,
       skip: int = 0,
       limit: int = 20,
       is_active: bool | None = None,
       sort_by: str = "created_at",
       order: str = "desc"
   ) -> list[Account]:
       """Get all accounts for a user with filters and pagination."""

   async def get_by_name(
       self,
       user_id: UUID,
       account_name: str
   ) -> Account | None:
       """Get account by user and name (case-insensitive)."""

   async def count_user_accounts(
       self,
       user_id: UUID,
       include_deleted: bool = False
   ) -> int:
       """Count accounts for a user."""

   async def exists_by_name(
       self,
       user_id: UUID,
       account_name: str,
       exclude_account_id: UUID | None = None
   ) -> bool:
       """Check if account name exists for user (for uniqueness validation)."""
   ```

3. **Query Optimization**
   - Use selectinload for user relationship
   - Use joinedload for shares relationship when needed
   - Apply indexes for all WHERE clause columns
   - Use pagination for all list queries

**Edge Cases & Error Handling:**
- [ ] Empty results return empty list, not None
- [ ] Invalid UUID raises ValueError (let FastAPI handle)
- [ ] Deleted accounts excluded unless explicitly requested
- [ ] Case-insensitive name lookup uses LOWER()

**Testing Requirements:**
- [ ] Test: get_by_user returns only user's accounts
- [ ] Test: get_by_user excludes soft-deleted accounts
- [ ] Test: get_by_user pagination works correctly
- [ ] Test: get_by_user sorting works (created_at, name)
- [ ] Test: get_by_name is case-insensitive
- [ ] Test: exists_by_name detects duplicates correctly
- [ ] Test: exists_by_name excludes current account during update

**Acceptance Criteria:**
- [ ] All queries execute in <100ms (p95)
- [ ] Soft delete filter applied automatically
- [ ] Pagination returns correct results
- [ ] Sorting works correctly (ASC/DESC)
- [ ] No N+1 query issues

---

#### Component: Permission Service

**Files:** `src/services/permission_service.py`

**Purpose:** Centralized permission checking logic for account access control.

**Implementation Requirements:**

1. **Permission Checking Algorithm**
   ```python
   async def check_permission(
       self,
       user_id: UUID,
       account_id: UUID,
       required_permission: PermissionLevel
   ) -> bool:
       """
       Check if user has required permission for account.

       Permission hierarchy: owner > editor > viewer
       """

   async def get_user_permission(
       self,
       user_id: UUID,
       account_id: UUID
   ) -> PermissionLevel | None:
       """Get user's permission level for account."""

   async def require_permission(
       self,
       user_id: UUID,
       account_id: UUID,
       required_permission: PermissionLevel
   ) -> None:
       """Raise InsufficientPermissionsError if user lacks permission."""
   ```

2. **Permission Hierarchy Logic**
   ```python
   PERMISSION_HIERARCHY = {
       PermissionLevel.viewer: 1,
       PermissionLevel.editor: 2,
       PermissionLevel.owner: 3,
   }

   def has_permission(
       user_permission: PermissionLevel,
       required_permission: PermissionLevel
   ) -> bool:
       return PERMISSION_HIERARCHY[user_permission] >= PERMISSION_HIERARCHY[required_permission]
   ```

3. **Permission Caching Strategy (Future Enhancement)**
   - Phase 2: No caching (database lookup each time)
   - Phase 3: Implement Redis caching with 5-minute TTL
   - Cache key: `permission:{user_id}:{account_id}`
   - Invalidate on share create/update/delete

**Edge Cases & Error Handling:**
- [ ] User with no share returns None (not error)
- [ ] Deleted shares return None (revoked access)
- [ ] Non-existent account raises NotFoundError
- [ ] Non-existent user raises NotFoundError

**Testing Requirements:**
- [ ] Test: Owner has all permissions
- [ ] Test: Editor has read/write permissions
- [ ] Test: Editor lacks delete/share permissions
- [ ] Test: Viewer has read-only permission
- [ ] Test: Viewer lacks write/delete/share permissions
- [ ] Test: Revoked share returns no permission
- [ ] Test: Non-existent share returns no permission

**Acceptance Criteria:**
- [ ] Permission checks execute in <50ms (p95)
- [ ] Permission hierarchy enforced correctly
- [ ] Audit logs permission check failures
- [ ] Raises appropriate exceptions for missing permissions

---

#### Component: Account Service

**Files:** `src/services/account_service.py`

**Purpose:** Business logic for account CRUD operations with permission enforcement.

**Implementation Requirements:**

1. **Account Creation**
   ```python
   async def create_account(
       self,
       user_id: UUID,
       account_name: str,
       account_type: AccountType,
       currency: str,
       opening_balance: Decimal,
       current_user: User,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None
   ) -> Account:
       """
       Create new account for user.

       Validations:
       - Account name unique per user (case-insensitive)
       - Currency valid ISO 4217 code
       - User exists and not deleted

       Creates:
       - Account record
       - Initial AccountShare with owner permission
       - Audit log entry
       """
   ```

2. **Account Retrieval**
   ```python
   async def get_account(
       self,
       account_id: UUID,
       current_user: User,
       request_id: str | None = None
   ) -> Account:
       """
       Get account by ID with permission check.

       Permission: Viewer or higher
       """

   async def list_accounts(
       self,
       current_user: User,
       skip: int = 0,
       limit: int = 20,
       is_active: bool | None = None,
       sort_by: str = "created_at",
       order: str = "desc",
       request_id: str | None = None
   ) -> tuple[list[Account], int]:
       """
       List accounts accessible to user.

       Returns: (accounts, total_count)
       """
   ```

3. **Account Update**
   ```python
   async def update_account(
       self,
       account_id: UUID,
       account_name: str | None = None,
       is_active: bool | None = None,
       current_user: User,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None
   ) -> Account:
       """
       Update account with permission check.

       Permission: Owner only (name, is_active changes)
       Editor: Cannot modify (future: allow name changes)

       Validations:
       - Account name unique per user if changed
       - Cannot modify currency (immutable)
       - Cannot modify balances (calculated field)

       Creates: Audit log entry with old/new values
       """
   ```

4. **Account Deletion**
   ```python
   async def delete_account(
       self,
       account_id: UUID,
       current_user: User,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None
   ) -> None:
       """
       Soft delete account with permission check.

       Permission: Owner only

       Actions:
       - Set deleted_at timestamp
       - Preserve transaction history (Phase 3)
       - Remove from normal queries
       - Audit log deletion
       """
   ```

**Data Handling:**
- **Input Validation:**
  - Account name: 1-100 characters, unique per user (case-insensitive)
  - Currency: ISO 4217 (3 uppercase letters)
  - Balance: Numeric(15,2), can be negative for loans
  - Account type: One of enum values

- **Output Format:**
  - Return Account model instances
  - Service layer returns domain objects
  - Route layer converts to Pydantic schemas

**Edge Cases & Error Handling:**
- [ ] Duplicate account name: AlreadyExistsError("Account name already exists")
- [ ] Invalid currency: ValidationError("Invalid ISO 4217 currency code")
- [ ] Permission denied: InsufficientPermissionsError("You don't have permission...")
- [ ] Account not found: NotFoundError("Account not found")
- [ ] User not found: NotFoundError("User not found")
- [ ] Deleted user: ValidationError("Cannot share with deleted user")

**Testing Requirements:**
- [ ] Unit test: Create account with valid data
- [ ] Unit test: Create account with duplicate name fails
- [ ] Unit test: Create account with invalid currency fails
- [ ] Unit test: Update account name succeeds (owner)
- [ ] Unit test: Update account fails (non-owner)
- [ ] Unit test: Delete account succeeds (owner)
- [ ] Unit test: Delete account fails (non-owner)
- [ ] Integration test: Full CRUD lifecycle
- [ ] Integration test: Permission enforcement

**Acceptance Criteria:**
- [ ] All validations work correctly
- [ ] Permission checks enforced on all operations
- [ ] Audit logs created for all operations
- [ ] Error messages are user-friendly
- [ ] Service methods execute in <200ms (p95)

**Implementation Notes:**
- Follow Phase 1 UserService pattern
- Inject dependencies via __init__ (db session)
- Use type hints for all parameters and returns
- Add comprehensive docstrings (Google style)
- Log all operations at INFO level
- Log errors at ERROR level with exc_info=True

---

#### Component: Account Share Service

**Files:** `src/services/account_service.py` (extend), `src/services/permission_service.py`

**Purpose:** Handle account sharing operations with permission management.

**Implementation Requirements:**

1. **Share Creation**
   ```python
   async def share_account(
       self,
       account_id: UUID,
       target_user_id: UUID,
       permission_level: PermissionLevel,
       current_user: User,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None
   ) -> AccountShare:
       """
       Share account with another user.

       Permission: Owner only

       Validations:
       - Target user exists and not deleted
       - Target user is not current user (cannot share with self)
       - Share does not already exist (check active shares)
       - Cannot grant owner permission (only one owner)

       Creates:
       - AccountShare record
       - Audit log entry

       Future: Send notification to target user
       """
   ```

2. **Share Listing**
   ```python
   async def list_shares(
       self,
       account_id: UUID,
       current_user: User,
       request_id: str | None = None
   ) -> list[AccountShare]:
       """
       List users account is shared with.

       Permission:
       - Owner: See all shares
       - Editor/Viewer: See only own share entry
       """
   ```

3. **Share Update**
   ```python
   async def update_share(
       self,
       account_id: UUID,
       share_id: UUID,
       permission_level: PermissionLevel,
       current_user: User,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None
   ) -> AccountShare:
       """
       Update permission level for shared account.

       Permission: Owner only

       Validations:
       - Cannot change own owner permission
       - Cannot grant owner permission (only one owner)

       Creates: Audit log with old/new permission levels
       """
   ```

4. **Share Revocation**
   ```python
   async def revoke_share(
       self,
       account_id: UUID,
       share_id: UUID,
       current_user: User,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None
   ) -> None:
       """
       Revoke account access from user.

       Permission: Owner only

       Actions:
       - Soft delete share (set deleted_at)
       - Preserve revocation history
       - Audit log revocation

       Validations:
       - Cannot revoke own owner permission
       """
   ```

**Data Handling:**
- **Input Validation:**
  - target_user_id: Must exist, not deleted, not self
  - permission_level: Must be valid enum value
  - Cannot grant owner permission (reserved for account creator)

- **Output Format:**
  - AccountShare with user details (username, email, full_name)
  - Include permission level and timestamps

**Edge Cases & Error Handling:**
- [ ] Share with self: ValidationError("Cannot share account with yourself")
- [ ] Share already exists: AlreadyExistsError("Account already shared with this user")
- [ ] Target user not found: NotFoundError("User not found")
- [ ] Target user deleted: ValidationError("Cannot share with deleted user")
- [ ] Revoke own owner: ValidationError("Cannot revoke own ownership")
- [ ] Grant owner permission: ValidationError("Cannot grant owner permission")
- [ ] Permission denied: InsufficientPermissionsError("Only owner can manage sharing")

**Testing Requirements:**
- [ ] Unit test: Share account with valid user (owner)
- [ ] Unit test: Share account fails (non-owner)
- [ ] Unit test: Share with self fails
- [ ] Unit test: Duplicate share fails
- [ ] Unit test: Update permission succeeds (owner)
- [ ] Unit test: Update own owner permission fails
- [ ] Unit test: Revoke share succeeds (owner)
- [ ] Unit test: Revoke own owner permission fails
- [ ] Integration test: Full sharing lifecycle
- [ ] Integration test: Permission enforcement after share

**Acceptance Criteria:**
- [ ] Sharing works correctly for all scenarios
- [ ] Permission checks enforced on all operations
- [ ] Audit logs created for all share operations
- [ ] Revoked shares no longer grant access
- [ ] Non-owners cannot manage sharing

---

#### Component: Account API Routes

**Files:** `src/api/routes/accounts.py`, `src/api/routes/account_shares.py`

**Purpose:** RESTful API endpoints for account management and sharing.

**Implementation Requirements:**

### Account CRUD Endpoints (accounts.py)

1. **POST /api/v1/accounts** - Create Account
   ```python
   @router.post(
       "/",
       response_model=AccountResponse,
       status_code=status.HTTP_201_CREATED,
       summary="Create new account",
       description="Create a new financial account for the authenticated user"
   )
   async def create_account(
       request: Request,
       account_data: AccountCreate,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> AccountResponse:
       """Create new account."""
   ```

2. **GET /api/v1/accounts** - List Accounts
   ```python
   @router.get(
       "/",
       response_model=PaginatedResponse[AccountListItem],
       summary="List user's accounts",
       description="Get paginated list of accounts accessible to user"
   )
   async def list_accounts(
       request: Request,
       pagination: PaginationParams = Depends(),
       filters: AccountFilterParams = Depends(),
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> PaginatedResponse[AccountListItem]:
       """List user's accounts with pagination and filters."""
   ```

3. **GET /api/v1/accounts/{account_id}** - Get Account
   ```python
   @router.get(
       "/{account_id}",
       response_model=AccountResponse,
       summary="Get account details",
       description="Get detailed information about a specific account"
   )
   async def get_account(
       request: Request,
       account_id: UUID,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> AccountResponse:
       """Get account by ID."""
   ```

4. **PUT /api/v1/accounts/{account_id}** - Update Account
   ```python
   @router.put(
       "/{account_id}",
       response_model=AccountResponse,
       summary="Update account",
       description="Update account details (owner only)"
   )
   async def update_account(
       request: Request,
       account_id: UUID,
       update_data: AccountUpdate,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> AccountResponse:
       """Update account details."""
   ```

5. **DELETE /api/v1/accounts/{account_id}** - Delete Account
   ```python
   @router.delete(
       "/{account_id}",
       status_code=status.HTTP_204_NO_CONTENT,
       summary="Delete account",
       description="Soft delete account (owner only)"
   )
   async def delete_account(
       request: Request,
       account_id: UUID,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> None:
       """Soft delete account."""
   ```

### Account Sharing Endpoints (account_shares.py)

1. **POST /api/v1/accounts/{account_id}/share** - Share Account
   ```python
   @router.post(
       "/{account_id}/share",
       response_model=AccountShareResponse,
       status_code=status.HTTP_201_CREATED,
       summary="Share account with user",
       description="Grant another user access to account (owner only)"
   )
   async def share_account(
       request: Request,
       account_id: UUID,
       share_data: AccountShareCreate,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> AccountShareResponse:
       """Share account with another user."""
   ```

2. **GET /api/v1/accounts/{account_id}/share** - List Shares
   ```python
   @router.get(
       "/{account_id}/share",
       response_model=list[AccountShareResponse],
       summary="List account shares",
       description="Get list of users account is shared with"
   )
   async def list_shares(
       request: Request,
       account_id: UUID,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> list[AccountShareResponse]:
       """List users account is shared with."""
   ```

3. **PUT /api/v1/accounts/{account_id}/share/{share_id}** - Update Share
   ```python
   @router.put(
       "/{account_id}/share/{share_id}",
       response_model=AccountShareResponse,
       summary="Update share permission",
       description="Update permission level for shared user (owner only)"
   )
   async def update_share(
       request: Request,
       account_id: UUID,
       share_id: UUID,
       update_data: AccountShareUpdate,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> AccountShareResponse:
       """Update share permission level."""
   ```

4. **DELETE /api/v1/accounts/{account_id}/share/{share_id}** - Revoke Share
   ```python
   @router.delete(
       "/{account_id}/share/{share_id}",
       status_code=status.HTTP_204_NO_CONTENT,
       summary="Revoke account access",
       description="Revoke user's access to account (owner only)"
   )
   async def revoke_share(
       request: Request,
       account_id: UUID,
       share_id: UUID,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service)
   ) -> None:
       """Revoke account access from user."""
   ```

**Implementation Notes:**
- Follow Phase 1 route patterns (see users.py)
- Use dependency injection for services
- Extract request_id from request.state
- Extract IP address from request.client.host
- Extract user agent from request.headers
- Add OpenAPI descriptions to all endpoints
- Include example requests/responses in schemas
- Use appropriate HTTP status codes
- Return consistent error responses

**Edge Cases & Error Handling:**
- [ ] Invalid UUID: FastAPI returns 422 automatically
- [ ] Not found: Return 404 with error message
- [ ] Permission denied: Return 403 with error message
- [ ] Validation error: Return 400 with details
- [ ] Duplicate resource: Return 409 with error message

**Testing Requirements:**
- [ ] Integration test: Create account returns 201
- [ ] Integration test: List accounts returns paginated results
- [ ] Integration test: Get account returns 200 with data
- [ ] Integration test: Get non-existent account returns 404
- [ ] Integration test: Update account returns 200 (owner)
- [ ] Integration test: Update account returns 403 (non-owner)
- [ ] Integration test: Delete account returns 204 (owner)
- [ ] Integration test: Delete account returns 403 (non-owner)
- [ ] Integration test: Share account returns 201 (owner)
- [ ] Integration test: Share account returns 403 (non-owner)
- [ ] Integration test: List shares filters correctly (owner vs non-owner)
- [ ] Integration test: Update share returns 200 (owner)
- [ ] Integration test: Revoke share returns 204 (owner)

**Acceptance Criteria:**
- [ ] All endpoints return correct status codes
- [ ] Response format consistent with Phase 1
- [ ] OpenAPI documentation complete
- [ ] Error responses follow standard format
- [ ] Request validation works correctly

---

#### Component: Pydantic Schemas

**Files:** `src/schemas/account.py`, `src/schemas/account_share.py`

**Purpose:** Request/response validation and serialization for account operations.

**Implementation Requirements:**

### Account Schemas (account.py)

1. **AccountCreate** - Account creation request
   ```python
   class AccountCreate(BaseModel):
       account_name: str = Field(
           min_length=1,
           max_length=100,
           description="Account name (must be unique per user)",
           examples=["Chase Checking", "Amex Credit Card"]
       )
       account_type: AccountType = Field(
           description="Type of account",
           examples=[AccountType.SAVINGS]
       )
       currency: str = Field(
           pattern="^[A-Z]{3}$",
           description="ISO 4217 currency code (3 uppercase letters)",
           examples=["USD", "EUR", "GBP"]
       )
       opening_balance: Decimal = Field(
           max_digits=15,
           decimal_places=2,
           description="Initial account balance (can be negative for loans)",
           examples=["1000.00", "-5000.00"]
       )
   ```

2. **AccountUpdate** - Account update request
   ```python
   class AccountUpdate(BaseModel):
       account_name: str | None = Field(
           None,
           min_length=1,
           max_length=100,
           description="New account name"
       )
       is_active: bool | None = Field(
           None,
           description="Whether account is active"
       )
   ```

3. **AccountResponse** - Full account details response
   ```python
   class AccountResponse(BaseModel):
       id: UUID
       user_id: UUID
       account_name: str
       account_type: AccountType
       currency: str
       opening_balance: Decimal
       current_balance: Decimal
       is_active: bool
       created_at: datetime
       updated_at: datetime

       model_config = ConfigDict(from_attributes=True)
   ```

4. **AccountListItem** - Account in list response
   ```python
   class AccountListItem(BaseModel):
       id: UUID
       account_name: str
       account_type: AccountType
       currency: str
       current_balance: Decimal
       is_active: bool

       model_config = ConfigDict(from_attributes=True)
   ```

5. **AccountFilterParams** - Query parameters for filtering
   ```python
   class AccountFilterParams(BaseModel):
       is_active: bool | None = Field(None, description="Filter by active status")
       account_type: AccountType | None = Field(None, description="Filter by account type")
       sort_by: str = Field("created_at", description="Sort field")
       order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")
   ```

### Account Share Schemas (account_share.py)

1. **AccountShareCreate** - Share creation request
   ```python
   class AccountShareCreate(BaseModel):
       user_id: UUID = Field(description="User ID to share with")
       permission_level: PermissionLevel = Field(
           description="Permission level to grant",
           examples=[PermissionLevel.viewer]
       )
   ```

2. **AccountShareUpdate** - Share update request
   ```python
   class AccountShareUpdate(BaseModel):
       permission_level: PermissionLevel = Field(
           description="New permission level"
       )
   ```

3. **AccountShareResponse** - Share details response
   ```python
   class AccountShareResponse(BaseModel):
       id: UUID
       account_id: UUID
       user_id: UUID
       permission_level: PermissionLevel
       created_at: datetime
       user: UserMinimal  # Nested user details

       model_config = ConfigDict(from_attributes=True)
   ```

4. **UserMinimal** - Minimal user info for share response
   ```python
   class UserMinimal(BaseModel):
       id: UUID
       username: str
       email: str
       full_name: str | None

       model_config = ConfigDict(from_attributes=True)
   ```

**Implementation Notes:**
- Use Pydantic V2 syntax (Field, ConfigDict)
- Add examples for OpenAPI documentation
- Use descriptive field descriptions
- Validate at schema level (pattern, min_length, etc.)
- Use from_attributes=True for ORM model conversion
- Follow Phase 1 schema patterns (see user.py)

---

### 2.3 Database Migration

**File:** `alembic/versions/YYYYMMDD_create_accounts_and_shares.py`

**Migration Script:**

```python
"""Create accounts and account_shares tables

Revision ID: XXXXXXXX
Revises: <previous_migration_id>
Create Date: 2025-11-03 XX:XX:XX
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'XXXXXXXX'
down_revision: Union[str, None] = '<previous_migration_id>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create accounts and account_shares tables with indexes and constraints."""

    # Create AccountType enum
    account_type_enum = postgresql.ENUM(
        'savings',
        'credit_card',
        'debit_card',
        'loan',
        'investment',
        'other',
        name='account_type',
        create_type=False
    )
    account_type_enum.create(op.get_bind(), checkfirst=True)

    # Create PermissionLevel enum
    permission_level_enum = postgresql.ENUM(
        'owner',
        'editor',
        'viewer',
        name='permission_level',
        create_type=False
    )
    permission_level_enum.create(op.get_bind(), checkfirst=True)

    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_name', sa.String(100), nullable=False),
        sa.Column('account_type', account_type_enum, nullable=False),
        sa.Column('currency', sa.CHAR(3), nullable=False),
        sa.Column('opening_balance', sa.Numeric(15, 2), nullable=False),
        sa.Column('current_balance', sa.Numeric(15, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_accounts_currency_format'),
    )

    # Create indexes for accounts
    op.create_index('idx_accounts_user', 'accounts', ['user_id'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_accounts_type', 'accounts', ['account_type'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_accounts_active', 'accounts', ['is_active'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_accounts_currency', 'accounts', ['currency'], postgresql_where=sa.text('deleted_at IS NULL'))

    # Create unique index for account names per user (case-insensitive)
    op.execute("""
        CREATE UNIQUE INDEX idx_accounts_user_name_unique
        ON accounts(user_id, LOWER(account_name))
        WHERE deleted_at IS NULL
    """)

    # Create account_shares table
    op.create_table(
        'account_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_level', permission_level_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for account_shares
    op.create_index('idx_account_shares_account', 'account_shares', ['account_id'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_account_shares_user', 'account_shares', ['user_id'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_account_shares_permission_lookup', 'account_shares', ['account_id', 'user_id', 'deleted_at'])

    # Create unique constraint for one active share per user per account
    op.create_index(
        'idx_account_shares_unique',
        'account_shares',
        ['account_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade() -> None:
    """Drop accounts and account_shares tables."""

    # Drop tables
    op.drop_table('account_shares')
    op.drop_table('accounts')

    # Drop enums
    op.execute('DROP TYPE permission_level')
    op.execute('DROP TYPE account_type')
```

**Migration Testing:**
1. Test upgrade in dev environment
2. Test downgrade in dev environment
3. Verify indexes created correctly
4. Verify constraints work (currency format, unique names)
5. Test with sample data
6. Run in staging before production

---

## 3. Testing Strategy

### 3.1 Unit Tests

**Directory:** `tests/unit/`

#### Repository Tests (test_account_repository.py)

```python
"""Unit tests for AccountRepository."""

@pytest.mark.asyncio
class TestAccountRepository:
    """Test AccountRepository methods."""

    async def test_create_account(self, db_session, test_user):
        """Test account creation."""
        repo = AccountRepository(db_session)
        account = await repo.create(
            user_id=test_user.id,
            account_name="Test Account",
            account_type=AccountType.SAVINGS,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            created_by=test_user.id,
            updated_by=test_user.id
        )
        assert account.id is not None
        assert account.account_name == "Test Account"

    async def test_get_by_user(self, db_session, test_user):
        """Test getting accounts by user."""
        # Create test accounts
        # Query accounts
        # Assert correct results

    async def test_get_by_name_case_insensitive(self, db_session, test_user):
        """Test case-insensitive name lookup."""
        # Create account with name "Savings"
        # Query with "savings"
        # Assert found

    async def test_soft_delete_excludes_from_queries(self, db_session, test_user):
        """Test soft-deleted accounts excluded from normal queries."""
        # Create account
        # Soft delete
        # Query accounts
        # Assert not in results
```

#### Service Tests (test_account_service.py)

```python
"""Unit tests for AccountService."""

@pytest.mark.asyncio
class TestAccountService:
    """Test AccountService methods."""

    async def test_create_account_success(self, db_session, test_user):
        """Test successful account creation."""
        service = AccountService(db_session)
        account = await service.create_account(
            user_id=test_user.id,
            account_name="Test Account",
            account_type=AccountType.SAVINGS,
            currency="USD",
            opening_balance=Decimal("1000.00"),
            current_user=test_user
        )
        assert account is not None
        # Verify audit log created

    async def test_create_account_duplicate_name(self, db_session, test_user):
        """Test account creation with duplicate name fails."""
        service = AccountService(db_session)
        # Create first account
        # Attempt to create second with same name
        # Assert AlreadyExistsError raised

    async def test_create_account_invalid_currency(self, db_session, test_user):
        """Test account creation with invalid currency fails."""
        # Assert ValidationError raised

    async def test_update_account_as_owner(self, db_session, test_user, test_account):
        """Test account update by owner succeeds."""
        # Update account
        # Assert success
        # Verify audit log

    async def test_update_account_as_non_owner(self, db_session, test_user, test_account):
        """Test account update by non-owner fails."""
        # Assert InsufficientPermissionsError raised
```

#### Permission Service Tests (test_permission_service.py)

```python
"""Unit tests for PermissionService."""

@pytest.mark.asyncio
class TestPermissionService:
    """Test PermissionService methods."""

    async def test_owner_has_all_permissions(self, db_session, test_account, test_user):
        """Test owner has all permission levels."""
        service = PermissionService(db_session)
        # Assert has viewer, editor, owner permissions

    async def test_editor_has_read_write(self, db_session, test_account, test_editor):
        """Test editor has read/write but not delete/share."""
        # Assert has viewer, editor permissions
        # Assert lacks owner permission

    async def test_viewer_has_read_only(self, db_session, test_account, test_viewer):
        """Test viewer has read-only permission."""
        # Assert has viewer permission
        # Assert lacks editor, owner permissions

    async def test_revoked_share_has_no_permission(self, db_session, test_account, test_user):
        """Test revoked share returns no permission."""
        # Create share
        # Revoke share
        # Assert no permission
```

**Unit Test Coverage Target:** 80%+

---

### 3.2 Integration Tests

**Directory:** `tests/integration/`

#### Account Routes Tests (test_account_routes.py)

```python
"""Integration tests for account routes."""

@pytest.mark.asyncio
class TestAccountRoutes:
    """Test account CRUD endpoints."""

    async def test_create_account_returns_201(self, client, auth_headers):
        """Test POST /api/v1/accounts returns 201."""
        response = await client.post(
            "/api/v1/accounts",
            json={
                "account_name": "Test Account",
                "account_type": "savings",
                "currency": "USD",
                "opening_balance": "1000.00"
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["account_name"] == "Test Account"

    async def test_list_accounts_pagination(self, client, auth_headers, test_accounts):
        """Test GET /api/v1/accounts pagination."""
        response = await client.get(
            "/api/v1/accounts?page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert data["meta"]["total"] == len(test_accounts)

    async def test_get_account_returns_200(self, client, auth_headers, test_account):
        """Test GET /api/v1/accounts/{id} returns 200."""
        response = await client.get(
            f"/api/v1/accounts/{test_account.id}",
            headers=auth_headers
        )
        assert response.status_code == 200

    async def test_get_account_not_found(self, client, auth_headers):
        """Test GET /api/v1/accounts/{id} returns 404 for non-existent account."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/accounts/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_update_account_as_owner(self, client, auth_headers, test_account):
        """Test PUT /api/v1/accounts/{id} succeeds for owner."""
        response = await client.put(
            f"/api/v1/accounts/{test_account.id}",
            json={"account_name": "Updated Name"},
            headers=auth_headers
        )
        assert response.status_code == 200

    async def test_update_account_as_non_owner(self, client, other_user_headers, test_account):
        """Test PUT /api/v1/accounts/{id} returns 403 for non-owner."""
        response = await client.put(
            f"/api/v1/accounts/{test_account.id}",
            json={"account_name": "Updated Name"},
            headers=other_user_headers
        )
        assert response.status_code == 403

    async def test_delete_account_as_owner(self, client, auth_headers, test_account):
        """Test DELETE /api/v1/accounts/{id} succeeds for owner."""
        response = await client.delete(
            f"/api/v1/accounts/{test_account.id}",
            headers=auth_headers
        )
        assert response.status_code == 204
```

#### Account Share Routes Tests (test_account_share_routes.py)

```python
"""Integration tests for account sharing routes."""

@pytest.mark.asyncio
class TestAccountShareRoutes:
    """Test account sharing endpoints."""

    async def test_share_account_returns_201(self, client, auth_headers, test_account, other_user):
        """Test POST /api/v1/accounts/{id}/share returns 201."""
        response = await client.post(
            f"/api/v1/accounts/{test_account.id}/share",
            json={
                "user_id": str(other_user.id),
                "permission_level": "viewer"
            },
            headers=auth_headers
        )
        assert response.status_code == 201

    async def test_share_account_as_non_owner(self, client, editor_headers, test_account, other_user):
        """Test POST /api/v1/accounts/{id}/share returns 403 for non-owner."""
        response = await client.post(
            f"/api/v1/accounts/{test_account.id}/share",
            json={
                "user_id": str(other_user.id),
                "permission_level": "viewer"
            },
            headers=editor_headers
        )
        assert response.status_code == 403

    async def test_list_shares_as_owner(self, client, auth_headers, test_account_with_shares):
        """Test GET /api/v1/accounts/{id}/share returns all shares for owner."""
        response = await client.get(
            f"/api/v1/accounts/{test_account_with_shares.id}/share",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # Owner + at least one share

    async def test_list_shares_as_non_owner(self, client, viewer_headers, test_account_with_shares):
        """Test GET /api/v1/accounts/{id}/share returns only own share for non-owner."""
        response = await client.get(
            f"/api/v1/accounts/{test_account_with_shares.id}/share",
            headers=viewer_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only own share

    async def test_update_share_permission(self, client, auth_headers, test_share):
        """Test PUT /api/v1/accounts/{id}/share/{share_id} updates permission."""
        response = await client.put(
            f"/api/v1/accounts/{test_share.account_id}/share/{test_share.id}",
            json={"permission_level": "editor"},
            headers=auth_headers
        )
        assert response.status_code == 200

    async def test_revoke_share(self, client, auth_headers, test_share):
        """Test DELETE /api/v1/accounts/{id}/share/{share_id} revokes access."""
        response = await client.delete(
            f"/api/v1/accounts/{test_share.account_id}/share/{test_share.id}",
            headers=auth_headers
        )
        assert response.status_code == 204
```

**Integration Test Coverage Target:** All endpoints tested with success and failure cases

---

### 3.3 End-to-End Tests

**Directory:** `tests/e2e/`

#### Account Lifecycle Test (test_account_lifecycle.py)

```python
"""E2E test for complete account lifecycle."""

@pytest.mark.asyncio
async def test_account_lifecycle(client, test_user):
    """Test complete account lifecycle: create → read → update → delete."""

    # 1. Login and get auth token
    login_response = await client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "testpassword123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create account
    create_response = await client.post(
        "/api/v1/accounts",
        json={
            "account_name": "E2E Test Account",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "5000.00"
        },
        headers=headers
    )
    assert create_response.status_code == 201
    account_id = create_response.json()["id"]

    # 3. Retrieve account
    get_response = await client.get(
        f"/api/v1/accounts/{account_id}",
        headers=headers
    )
    assert get_response.status_code == 200
    assert get_response.json()["account_name"] == "E2E Test Account"

    # 4. Update account
    update_response = await client.put(
        f"/api/v1/accounts/{account_id}",
        json={"account_name": "Updated E2E Account"},
        headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["account_name"] == "Updated E2E Account"

    # 5. List accounts (verify appears)
    list_response = await client.get("/api/v1/accounts", headers=headers)
    assert list_response.status_code == 200
    account_ids = [acc["id"] for acc in list_response.json()["data"]]
    assert account_id in account_ids

    # 6. Delete account
    delete_response = await client.delete(
        f"/api/v1/accounts/{account_id}",
        headers=headers
    )
    assert delete_response.status_code == 204

    # 7. Verify account no longer appears in list
    list_after_delete = await client.get("/api/v1/accounts", headers=headers)
    account_ids_after = [acc["id"] for acc in list_after_delete.json()["data"]]
    assert account_id not in account_ids_after
```

#### Sharing Flow Test (test_sharing_flows.py)

```python
"""E2E test for account sharing flows."""

@pytest.mark.asyncio
async def test_sharing_flow(client, test_user, other_user):
    """Test complete sharing flow: create → share → access → revoke."""

    # 1. User A creates account
    user_a_token = await login(client, test_user)
    user_a_headers = {"Authorization": f"Bearer {user_a_token}"}

    create_response = await client.post(
        "/api/v1/accounts",
        json={
            "account_name": "Shared Account",
            "account_type": "savings",
            "currency": "USD",
            "opening_balance": "10000.00"
        },
        headers=user_a_headers
    )
    account_id = create_response.json()["id"]

    # 2. User A shares account with User B (viewer permission)
    share_response = await client.post(
        f"/api/v1/accounts/{account_id}/share",
        json={
            "user_id": str(other_user.id),
            "permission_level": "viewer"
        },
        headers=user_a_headers
    )
    assert share_response.status_code == 201
    share_id = share_response.json()["id"]

    # 3. User B can read account
    user_b_token = await login(client, other_user)
    user_b_headers = {"Authorization": f"Bearer {user_b_token}"}

    read_response = await client.get(
        f"/api/v1/accounts/{account_id}",
        headers=user_b_headers
    )
    assert read_response.status_code == 200

    # 4. User B cannot update account (viewer permission)
    update_response = await client.put(
        f"/api/v1/accounts/{account_id}",
        json={"account_name": "Hacked Name"},
        headers=user_b_headers
    )
    assert update_response.status_code == 403

    # 5. User A upgrades User B to editor
    upgrade_response = await client.put(
        f"/api/v1/accounts/{account_id}/share/{share_id}",
        json={"permission_level": "editor"},
        headers=user_a_headers
    )
    assert upgrade_response.status_code == 200

    # 6. User B can now update account
    update_response_2 = await client.put(
        f"/api/v1/accounts/{account_id}",
        json={"account_name": "Legitimately Updated Name"},
        headers=user_b_headers
    )
    assert update_response_2.status_code == 200

    # 7. User A revokes access
    revoke_response = await client.delete(
        f"/api/v1/accounts/{account_id}/share/{share_id}",
        headers=user_a_headers
    )
    assert revoke_response.status_code == 204

    # 8. User B can no longer access account
    read_after_revoke = await client.get(
        f"/api/v1/accounts/{account_id}",
        headers=user_b_headers
    )
    assert read_after_revoke.status_code == 404  # Account not found (no access)
```

**E2E Test Coverage:** All critical user flows tested end-to-end

---

### 3.4 Performance Tests

**Directory:** `tests/performance/`

#### Load Test (test_account_performance.py)

```python
"""Performance tests for account operations."""

@pytest.mark.asyncio
@pytest.mark.performance
async def test_account_list_performance(client, auth_headers, create_test_accounts):
    """Test account list performance with large dataset."""

    # Create 1000 test accounts
    await create_test_accounts(count=1000)

    # Measure list endpoint performance
    start_time = time.time()
    response = await client.get(
        "/api/v1/accounts?page=1&page_size=20",
        headers=auth_headers
    )
    duration = time.time() - start_time

    assert response.status_code == 200
    assert duration < 0.1  # Less than 100ms
```

**Performance Benchmarks:**
- Account list: <100ms (p95)
- Account retrieval: <50ms (p95)
- Permission check: <50ms (p95)
- Account creation: <200ms (p95)
- Share creation: <300ms (includes audit log)

---

## 4. Implementation Roadmap

### 4.1 Timeline Summary

```
Week 1-2: Phase 2A - Core Account Management
├── Days 1-2: Database models and migration
├── Days 3-4: Repository layer
├── Days 5-6: Service layer
├── Days 7-8: API routes and schemas
├── Days 9-10: Unit and integration tests

Week 2-3: Phase 2B - Account Sharing & Permissions
├── Days 11-12: AccountShare model and migration update
├── Days 13: Permission service
├── Days 14-15: Sharing endpoints
├── Day 16: Testing (unit, integration, E2E)

Week 3-4: Phase 2C - Polish & Documentation
├── Days 17-18: OpenAPI documentation and error refinement
├── Days 19: Performance optimization and load testing
├── Day 20: Final testing and security review
```

### 4.2 Detailed Task Breakdown

#### Week 1: Core Account Management - Part 1

**Day 1-2: Database Layer**
- [ ] Create `src/models/enums.py` with AccountType and PermissionLevel
- [ ] Create `src/models/account.py` with Account model
- [ ] Create Alembic migration for accounts table
- [ ] Test migration upgrade/downgrade
- [ ] Verify indexes created correctly
- [ ] Test unique constraints (account name per user)
- [ ] Test currency validation constraint

**Day 3-4: Repository Layer**
- [ ] Create `src/repositories/account_repository.py`
- [ ] Implement AccountRepository extending BaseRepository
- [ ] Add custom methods: get_by_user, get_by_name, exists_by_name, count_user_accounts
- [ ] Write unit tests for all repository methods
- [ ] Verify soft delete filtering works correctly
- [ ] Test pagination and sorting

**Day 5-6: Service Layer**
- [ ] Create `src/services/account_service.py`
- [ ] Implement AccountService with dependency injection
- [ ] Add methods: create_account, get_account, list_accounts, update_account, delete_account
- [ ] Integrate AuditService for logging
- [ ] Implement validation logic (unique names, valid currency)
- [ ] Write unit tests for all service methods
- [ ] Test error handling (duplicates, invalid data)

**Day 7-8: API Layer**
- [ ] Create `src/schemas/account.py` with Pydantic schemas
- [ ] Create `src/api/routes/accounts.py`
- [ ] Implement POST /api/v1/accounts
- [ ] Implement GET /api/v1/accounts (list with pagination)
- [ ] Implement GET /api/v1/accounts/{id}
- [ ] Implement PUT /api/v1/accounts/{id}
- [ ] Implement DELETE /api/v1/accounts/{id}
- [ ] Add OpenAPI descriptions and examples
- [ ] Create dependency injection functions

**Day 9-10: Testing**
- [ ] Write integration tests for all endpoints
- [ ] Test success cases (200, 201, 204)
- [ ] Test error cases (400, 403, 404, 409, 422)
- [ ] Test pagination edge cases (empty, single page, multiple pages)
- [ ] Test soft delete behavior
- [ ] Verify audit logs created correctly
- [ ] Run coverage report (target: 80%+)

#### Week 2: Account Sharing - Part 1

**Day 11-12: Sharing Database Layer**
- [ ] Create AccountShare model in `src/models/account.py`
- [ ] Update Alembic migration to add account_shares table
- [ ] Create `src/repositories/account_share_repository.py`
- [ ] Implement AccountShareRepository with custom queries
- [ ] Write unit tests for repository methods
- [ ] Test composite indexes for permission lookups

**Day 13: Permission Service**
- [ ] Create `src/services/permission_service.py`
- [ ] Implement PermissionService with permission checking logic
- [ ] Add methods: check_permission, get_user_permission, require_permission
- [ ] Write unit tests for permission hierarchy
- [ ] Test permission checking for all levels (owner, editor, viewer)

**Day 14-15: Sharing API Layer**
- [ ] Create `src/schemas/account_share.py` with Pydantic schemas
- [ ] Create `src/api/routes/account_shares.py`
- [ ] Implement POST /api/v1/accounts/{id}/share
- [ ] Implement GET /api/v1/accounts/{id}/share
- [ ] Implement PUT /api/v1/accounts/{id}/share/{share_id}
- [ ] Implement DELETE /api/v1/accounts/{id}/share/{share_id}
- [ ] Update AccountService with permission checks
- [ ] Add share-related methods to AccountService

**Day 16: Testing**
- [ ] Write integration tests for sharing endpoints
- [ ] Test sharing success cases
- [ ] Test permission enforcement (403 errors)
- [ ] Test share revocation
- [ ] Test concurrent access scenarios
- [ ] Write E2E test for sharing flow
- [ ] Run full test suite

#### Week 3: Polish & Documentation

**Day 17-18: Documentation & Error Refinement**
- [ ] Complete OpenAPI descriptions for all endpoints
- [ ] Add request/response examples to schemas
- [ ] Document permission matrix in docstrings
- [ ] Create error code reference (ACCOUNT_NOT_FOUND, etc.)
- [ ] Refine error messages (user-friendly)
- [ ] Update README with account management section
- [ ] Add code examples to docstrings

**Day 19: Performance Optimization**
- [ ] Review and optimize database queries with EXPLAIN
- [ ] Add missing indexes if needed
- [ ] Implement permission caching strategy (if needed)
- [ ] Run load tests (100 concurrent users)
- [ ] Profile slow queries and optimize
- [ ] Verify performance benchmarks met (<200ms p95)

**Day 20: Final Testing & Security Review**
- [ ] Run full test suite (unit, integration, E2E)
- [ ] Verify all 22 acceptance criteria met
- [ ] Security review: permission bypass attempts
- [ ] Test error handling comprehensively
- [ ] Code coverage report (target: 80%+)
- [ ] Final code review
- [ ] Deploy to staging for QA

### 4.3 Dependencies & Blockers

**Critical Dependencies:**
- Phase 1 must be complete and deployed ✅
- Database migration must succeed in staging before production
- All tests must pass before deployment

**Potential Blockers:**
1. **Migration Failure:** If migration fails in production
   - Mitigation: Test extensively in staging, have rollback plan ready
   - Rollback: Run downgrade migration, revert code deploy

2. **Performance Issues:** If permission checks are too slow
   - Mitigation: Implement Redis caching for permissions
   - Fallback: Optimize database queries, add composite indexes

3. **Concurrent Access Issues:** If balance updates cause race conditions
   - Mitigation: Use FOR UPDATE locking in Phase 3 (not critical in Phase 2)
   - Note: Phase 2 has no transaction updates yet

**Risk Mitigation:**
- Daily standups to identify blockers early
- Code reviews after each major component
- Continuous integration runs tests on every commit
- Staging deployment for QA before production

---

## 5. Security & Compliance

### 5.1 Permission Model Security

**Threats:**
- Permission bypass through API manipulation
- Privilege escalation (viewer → editor → owner)
- Share enumeration (discovering other users' shares)

**Mitigations:**
- [ ] All service methods check permissions before operations
- [ ] Permission checks happen in service layer (defense in depth)
- [ ] Non-owners can only see their own share entry
- [ ] Audit logs track all permission changes with context
- [ ] Cannot grant owner permission (reserved for creator)
- [ ] Cannot modify own owner permission (prevents lockout)

### 5.2 Data Protection

**Sensitive Data:**
- Account balances (financial information)
- Account names (may contain personal info)
- Sharing relationships (privacy concern)

**Protections:**
- [ ] TLS/HTTPS only in production
- [ ] Field-level access control (permission checks)
- [ ] Audit logging of all data access
- [ ] Soft delete preserves data for compliance
- [ ] No sensitive data in logs or error messages

### 5.3 Audit & Compliance

**Regulatory Requirements:**
- GDPR: Data subject access, right to deletion
- SOX: 7-year transaction history retention
- PCI DSS: If integrating with payment systems (future)

**Compliance Measures:**
- [ ] Comprehensive audit logging (who, what, when, where)
- [ ] Soft delete for regulatory retention
- [ ] User data export capability (GDPR right to access)
- [ ] Data deletion process (GDPR right to be forgotten)
- [ ] Audit log immutability (cannot be modified/deleted)

---

## 6. Performance & Monitoring

### 6.1 Performance Targets

| Operation | Target (p95) | Measurement |
|-----------|--------------|-------------|
| Account List | <100ms | API response time |
| Account Retrieval | <50ms | API response time |
| Account Creation | <200ms | API response time (includes audit log) |
| Permission Check | <50ms | Service method duration |
| Share Creation | <300ms | API response time (includes audit log) |
| Database Query | <50ms | Query execution time |

### 6.2 Monitoring Plan

**Metrics to Track:**
- Account creation rate (per hour, per day)
- Account sharing adoption rate (% of users who share)
- API response times (p50, p95, p99)
- Error rate by endpoint
- Permission check latency
- Database connection pool usage
- Audit log volume

**Alerting:**
- [ ] Alert if error rate >5% for any endpoint
- [ ] Alert if p95 response time exceeds targets
- [ ] Alert if database connections saturated
- [ ] Alert if permission checks >100ms (p95)

### 6.3 Load Testing

**Scenarios:**
1. 100 concurrent users creating accounts
2. 1000 concurrent permission checks
3. 500 concurrent account list queries
4. Mixed load (70% read, 30% write)

**Acceptance Criteria:**
- No errors under load
- Response times within targets
- Database connections stable
- Memory usage stable

---

## 7. Documentation Standards

### 7.1 Code Documentation

**Required Documentation:**
- [ ] Docstrings (Google style) for all public classes and methods
- [ ] Type hints for all function parameters and returns
- [ ] Inline comments for complex business logic
- [ ] README section on account management
- [ ] OpenAPI descriptions for all endpoints

**Example Docstring:**
```python
async def create_account(
    self,
    user_id: UUID,
    account_name: str,
    account_type: AccountType,
    currency: str,
    opening_balance: Decimal,
    current_user: User,
    request_id: str | None = None
) -> Account:
    """
    Create new financial account for user.

    Creates an account with the specified details and initializes an owner
    share for the user. The account name must be unique per user (case-insensitive).
    Currency is immutable after creation.

    Args:
        user_id: ID of user who will own the account
        account_name: Descriptive account name (1-100 characters, unique per user)
        account_type: Type of account (savings, credit_card, etc.)
        currency: ISO 4217 currency code (3 uppercase letters)
        opening_balance: Initial account balance (can be negative for loans)
        current_user: Currently authenticated user (for audit logging)
        request_id: Optional request ID for correlation

    Returns:
        Created Account instance with all fields populated

    Raises:
        AlreadyExistsError: If account name already exists for user
        ValidationError: If currency invalid or data validation fails
        NotFoundError: If user_id does not exist

    Example:
        >>> account = await account_service.create_account(
        ...     user_id=user.id,
        ...     account_name="Chase Checking",
        ...     account_type=AccountType.SAVINGS,
        ...     currency="USD",
        ...     opening_balance=Decimal("1000.00"),
        ...     current_user=user
        ... )
    """
```

### 7.2 API Documentation

**OpenAPI Requirements:**
- [ ] Summary and description for all endpoints
- [ ] Request body examples
- [ ] Response examples (success and error)
- [ ] Security requirements (OAuth2)
- [ ] Error response documentation

**Example OpenAPI Documentation:**
```python
@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new account",
    description="""
    Create a new financial account for the authenticated user.

    The account name must be unique per user (case-insensitive). Currency is
    immutable after creation. An owner share is automatically created for the user.

    **Permission:** Authenticated user

    **Audit:** Creates audit log entry with account details

    **Rate Limit:** 10 requests per minute per user
    """,
    responses={
        201: {
            "description": "Account created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                        "account_name": "Chase Checking",
                        "account_type": "savings",
                        "currency": "USD",
                        "opening_balance": "1000.00",
                        "current_balance": "1000.00",
                        "is_active": True,
                        "created_at": "2025-11-03T10:00:00Z",
                        "updated_at": "2025-11-03T10:00:00Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request data (duplicate name, invalid currency)"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"}
    }
)
```

### 7.3 README Update

**Section to Add:**
```markdown
## Account Management

### Overview
Users can create and manage multiple financial accounts (savings, credit cards,
loans, investments) and share them with other users using granular permissions.

### Account Types
- **Savings:** Standard savings or checking accounts
- **Credit Card:** Credit card accounts
- **Debit Card:** Prepaid or debit card accounts
- **Loan:** Loan accounts (mortgage, personal, auto)
- **Investment:** Investment or brokerage accounts
- **Other:** User-defined account types

### Permission Levels
- **Owner:** Full access (read, write, delete, manage sharing)
- **Editor:** Read/write access (cannot delete or change sharing)
- **Viewer:** Read-only access

### API Endpoints

#### Account CRUD
- `POST /api/v1/accounts` - Create account
- `GET /api/v1/accounts` - List accounts (paginated)
- `GET /api/v1/accounts/{id}` - Get account details
- `PUT /api/v1/accounts/{id}` - Update account (owner only)
- `DELETE /api/v1/accounts/{id}` - Soft delete account (owner only)

#### Account Sharing
- `POST /api/v1/accounts/{id}/share` - Share account with user
- `GET /api/v1/accounts/{id}/share` - List shares
- `PUT /api/v1/accounts/{id}/share/{share_id}` - Update permission
- `DELETE /api/v1/accounts/{id}/share/{share_id}` - Revoke access

### Example Usage

#### Create Account
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "Chase Checking",
    "account_type": "savings",
    "currency": "USD",
    "opening_balance": "1000.00"
  }'
\`\`\`

#### Share Account
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/accounts/$ACCOUNT_ID/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "$OTHER_USER_ID",
    "permission_level": "viewer"
  }'
\`\`\`

### Multi-Currency Support
Accounts support all ISO 4217 currency codes (USD, EUR, GBP, etc.). Currency is
immutable after account creation to prevent accidental conversions.
```

---

## 8. Deployment Plan

### 8.1 Pre-Deployment Checklist

- [ ] All tests pass (unit, integration, E2E)
- [ ] Code coverage ≥80%
- [ ] Security review completed
- [ ] Performance benchmarks met
- [ ] OpenAPI documentation complete
- [ ] Migration tested in staging
- [ ] Rollback plan documented

### 8.2 Deployment Steps

1. **Staging Deployment (Day 19)**
   - Deploy code to staging environment
   - Run migration: `uv run alembic upgrade head`
   - Run smoke tests
   - QA testing (2 days)
   - Fix any bugs found

2. **Production Deployment (Day 22)**
   - Schedule deployment during low-traffic window
   - Create database backup
   - Deploy code to production
   - Run migration: `uv run alembic upgrade head`
   - Verify migration success
   - Run smoke tests
   - Monitor error rates and performance
   - Enable feature for 10% of users (feature flag)

3. **Gradual Rollout (Week 4)**
   - Day 23: 10% of users (monitor closely)
   - Day 24: 25% of users (if stable)
   - Day 25: 50% of users (if stable)
   - Day 26: 100% of users (full rollout)

### 8.3 Rollback Plan

**If critical issues found:**
1. Disable feature via feature flag (immediate)
2. Revert code deployment
3. Run downgrade migration: `uv run alembic downgrade -1`
4. Verify rollback successful
5. Investigate and fix issue
6. Redeploy after fix

**Rollback Triggers:**
- Error rate >10% for any endpoint
- Critical security vulnerability discovered
- Data corruption detected
- Performance degradation >2x targets

### 8.4 Post-Deployment Monitoring

**Day 1 (First 24 hours):**
- Monitor error rates every hour
- Review audit logs for suspicious activity
- Check database connection pool usage
- Verify performance metrics within targets

**Week 1:**
- Daily metrics review
- User feedback collection
- Bug triage and fixes
- Performance optimization if needed

**Week 2-4:**
- Weekly metrics review
- Feature adoption analysis
- User surveys (optional)
- Plan Phase 3 (transactions)

---

## 9. Success Metrics & KPIs

### 9.1 Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Uptime | 99.9% | Uptime monitoring |
| Error Rate | <1% | Error logs |
| p95 Response Time | <200ms | API monitoring |
| Test Coverage | ≥80% | pytest-cov |
| Code Quality | A+ | SonarQube/Ruff |

### 9.2 Business Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Account Creation Rate | 60% of users create ≥1 account | 30 days |
| Average Accounts per User | 3-5 accounts | 30 days |
| Sharing Adoption | 30% of users share ≥1 account | 90 days |
| Active Account Usage | 70% of accounts accessed monthly | 90 days |
| Feature Engagement | 80% of users interact with accounts weekly | 90 days |

### 9.3 User Satisfaction Metrics

- User feedback surveys (post-launch)
- Support ticket volume (target: <5 tickets per 1000 users)
- Feature usage analytics
- Error rate from user perspective

---

## 10. Future Enhancements (Out of Scope for Phase 2)

### Phase 3 Dependencies
- Transaction model integration (updates current_balance)
- Balance calculation from transaction history
- Historical balance queries (as of date)

### Potential Future Features
- **Notification System:** Email/in-app notifications for share events
- **Share Acceptance Flow:** Recipient must accept before access granted
- **Time-Limited Shares:** Shares expire after specified duration
- **Permission Templates:** Predefined permission sets (e.g., "View Only", "Full Access")
- **Account Categories:** User-defined categories for organization
- **Account Tags:** Tagging system for flexible filtering
- **Account Notes:** Private notes on accounts
- **Export Functionality:** Export account data to CSV/PDF
- **Currency Conversion:** Display balances in user's preferred currency
- **Account Archiving:** Alternative to soft delete with restore capability
- **Multi-Owner Accounts:** Support for joint ownership (multiple owners)
- **Permission Inheritance:** Folder-like structure with inherited permissions
- **Activity Feed:** Timeline of account changes and transactions

---

## 11. References & Resources

### 11.1 Internal Documentation
- Phase 1 Implementation (authentication, audit logging, user management)
- Backend Standards: `.claude/standards/backend.md`
- Database Standards: `.claude/standards/database.md`
- API Standards: `.claude/standards/api.md`
- Security Standards: `.claude/standards/security.md`

### 11.2 Research Documents
- Research File: `.features/research/20251103_account-management-system.md`
- Feature Description: `.features/descriptions/phase-2.md`

### 11.3 External Resources
- **ISO 4217 Currency Codes:** https://www.iso.org/iso-4217-currency-codes.html
- **PostgreSQL Partial Indexes:** https://www.postgresql.org/docs/current/indexes-partial.html
- **SQLAlchemy 2.0 Async:** https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **FastAPI Best Practices:** https://fastapi.tiangolo.com/tutorial/
- **Pydantic V2 Documentation:** https://docs.pydantic.dev/latest/
- **Soft Deletion Patterns:** https://brandur.org/soft-deletion
- **Permission Models (RBAC):** https://en.wikipedia.org/wiki/Role-based_access_control

### 11.4 Competitive Analysis
- Monarch Money: https://www.monarch.com/
- YNAB: https://www.ynab.com/
- Honeydue: https://www.honeydue.com/

---

## 12. Approval & Sign-off

### 12.1 Stakeholder Review

**Product Team:**
- [ ] Feature scope approved
- [ ] User stories validated
- [ ] Success metrics agreed

**Engineering Team:**
- [ ] Technical architecture reviewed
- [ ] Implementation plan approved
- [ ] Timeline realistic

**QA Team:**
- [ ] Test strategy approved
- [ ] Acceptance criteria clear

**Security Team:**
- [ ] Security model reviewed
- [ ] Audit logging adequate

### 12.2 Go/No-Go Decision

**Proceed with Implementation:** ✅ YES

**Rationale:**
- Solid technical foundation (Phase 1 complete)
- Clear market demand (200M+ users by 2026)
- Proven architecture patterns
- Manageable scope (4 weeks)
- Natural progression to Phase 3

**Next Steps:**
1. Schedule kick-off meeting (all stakeholders)
2. Assign development resources
3. Set up project tracking (Jira/Linear)
4. Begin Phase 2A implementation (Day 1)

---

**Plan Version:** 1.0
**Created By:** Claude Code
**Last Updated:** November 3, 2025
**Status:** Ready for Implementation

---

## Appendix A: Error Code Reference

| Error Code | HTTP Status | Message | Resolution |
|------------|-------------|---------|------------|
| ACCOUNT_NOT_FOUND | 404 | Account not found or you don't have access | Verify account ID, check permissions |
| ACCOUNT_NAME_EXISTS | 400 | Account name already exists for this user | Choose a different account name |
| INVALID_CURRENCY | 400 | Invalid ISO 4217 currency code | Use 3-letter uppercase code (USD, EUR, etc.) |
| INVALID_ACCOUNT_TYPE | 400 | Invalid account type | Use: savings, credit_card, debit_card, loan, investment, other |
| PERMISSION_DENIED | 403 | You don't have permission to perform this action | Request access from account owner |
| USER_NOT_FOUND | 404 | User to share with not found | Verify user email/ID |
| SHARE_ALREADY_EXISTS | 400 | Account already shared with this user | Update existing share instead |
| CANNOT_SHARE_WITH_SELF | 400 | Cannot share account with yourself | Share with a different user |
| CANNOT_MODIFY_CURRENCY | 400 | Account currency is immutable | Create new account with desired currency |
| CANNOT_REVOKE_OWN_OWNERSHIP | 400 | Cannot revoke your own ownership | Transfer ownership first |
| CANNOT_GRANT_OWNER_PERMISSION | 400 | Cannot grant owner permission | Only account creator can be owner |

---

## Appendix B: Database Indexes Summary

| Index Name | Table | Columns | Type | Purpose |
|------------|-------|---------|------|---------|
| idx_accounts_user | accounts | user_id | Partial (WHERE deleted_at IS NULL) | Filter accounts by user |
| idx_accounts_type | accounts | account_type | Partial | Filter by account type |
| idx_accounts_active | accounts | is_active | Partial | Filter active accounts |
| idx_accounts_currency | accounts | currency | Partial | Filter by currency |
| idx_accounts_user_name_unique | accounts | user_id, LOWER(account_name) | Unique Partial | Enforce name uniqueness |
| idx_account_shares_account | account_shares | account_id | Partial | Find shares for account |
| idx_account_shares_user | account_shares | user_id | Partial | Find user's shares |
| idx_account_shares_permission_lookup | account_shares | account_id, user_id, deleted_at | Composite | Permission checks |
| idx_account_shares_unique | account_shares | account_id, user_id | Unique Partial | Prevent duplicate shares |

---

## Appendix C: Permission Matrix

| Action | Owner | Editor | Viewer | None |
|--------|-------|--------|--------|------|
| View account details | ✅ | ✅ | ✅ | ❌ |
| View balance | ✅ | ✅ | ✅ | ❌ |
| View transaction history | ✅ | ✅ | ✅ | ❌ |
| Update account name | ✅ | ❌* | ❌ | ❌ |
| Update is_active | ✅ | ❌ | ❌ | ❌ |
| Delete account | ✅ | ❌ | ❌ | ❌ |
| Share account | ✅ | ❌ | ❌ | ❌ |
| Update permissions | ✅ | ❌ | ❌ | ❌ |
| Revoke access | ✅ | ❌ | ❌ | ❌ |
| View all shares | ✅ | ❌ | ❌ | ❌ |
| View own share entry | ✅ | ✅ | ✅ | ❌ |
| Create transactions | ✅ | ✅ | ❌ | ❌ |
| Update transactions | ✅ | ✅ | ❌ | ❌ |
| Delete transactions | ✅ | ✅ | ❌ | ❌ |

*Future enhancement: Allow editors to update account name

---

**End of Implementation Plan**
