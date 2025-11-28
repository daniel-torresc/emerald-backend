# Implementation Plan: Account Types Master Data

**Feature ID**: feat-02-account-types
**Phase**: 1 - Foundation
**Priority**: High
**Estimated Effort**: 3-4 developer days
**Dependencies**: None

---

## 1. Executive Summary

### Overview

This feature converts account types from a hardcoded Python enum with 4 fixed values (`checking`, `savings`, `investment`, `other`) to a flexible, database-backed master data table managed by administrators. This architectural change enables administrators to add specialized account types (HSA, 529 Plans, Crypto Wallets, IRA, 401k, etc.) without requiring code deployments, providing the flexibility needed for a modern personal finance platform.

### Primary Objectives

1. **Flexibility**: Enable administrators to create custom account types without code changes
2. **Scalability**: Support unlimited account types to accommodate diverse user needs
3. **Maintainability**: Centralize account type management in the database instead of code
4. **User Experience**: Allow users to select from a rich set of specialized account types
5. **Backward Compatibility**: Maintain existing 4 account types during transition

### Expected Outcomes

- **Administrators** can create, update, and deactivate account types through the API
- **All users** can view and select from available active account types
- **System** maintains the existing 4 account types (checking, savings, investment, other) as default options
- **Compliance**: All changes to account types are logged in the audit trail
- **No breaking changes** to existing functionality (accounts table remains unchanged in this phase)

### Success Criteria

✅ `account_types` table created with proper constraints and indexes
✅ 4 default account types seeded during migration
✅ Complete CRUD API for account types
✅ Only admins can create/update/delete account types
✅ All users can list and view account types
✅ Cannot delete account types in use (when integrated with accounts)
✅ All operations audited
✅ 80%+ test coverage
✅ Zero breaking changes to existing endpoints

---

## 2. Technical Architecture

### 2.1 System Design Overview

This feature introduces a new **master data table** pattern to the Emerald platform. Master data tables are globally accessible reference data managed by administrators and consumed by all users.

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (src/api/routes/account_types.py)               │
│  - List account types (authenticated users)                │
│  - Get account type by ID (authenticated users)            │
│  - Create/Update/Delete account types (admin only)         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer (src/services/account_type_service.py)      │
│  - Business logic for account type management              │
│  - Uniqueness validation (key must be unique)              │
│  - Usage checks (prevent deletion if in use)               │
│  - Audit logging for all state changes                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Repository Layer (src/repositories/account_type_repo.py)  │
│  - Database operations (CRUD)                               │
│  - Filtering by is_active                                   │
│  - Ordered by sort_order                                    │
│  - Key uniqueness checks                                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Database (PostgreSQL)                                      │
│  - account_types table (master data)                        │
│  - Unique constraint on key                                 │
│  - Index on is_active for filtering                         │
└─────────────────────────────────────────────────────────────┘
```

**Key Characteristics**:
- **Globally accessible**: All users can read account types
- **Admin-managed**: Only administrators can create/update/deactivate
- **No soft delete**: Uses `is_active` flag instead (like financial_institutions)
- **Immutable keys**: Account type keys cannot be changed after creation
- **Ordered presentation**: sort_order controls display order in UI

### 2.2 Technology Decisions

#### **PostgreSQL Native Features**

**Purpose**: Leverage database constraints for data integrity
**Why this choice**:
- UNIQUE constraint on `key` ensures global uniqueness at database level
- CHECK constraint validates key format (lowercase, alphanumeric, underscore)
- Prevents race conditions and duplicate data
- Better performance than application-level validation

**Version**: PostgreSQL 16+
**Alternatives considered**:
- Application-level validation only: Rejected due to race condition risks
- Enum migration: Rejected because enums are hard to modify in PostgreSQL

#### **No Soft Delete Pattern**

**Purpose**: Simplify data model for master data
**Why this choice**:
- Master data should be deactivated, not deleted
- `is_active` flag is clearer for global reference data
- Matches the `financial_institutions` pattern already in codebase
- Simpler queries (no need for `WHERE deleted_at IS NULL`)

**Alternatives considered**:
- SoftDeleteMixin: Rejected because master data shouldn't be "deleted"
- Hard delete: Rejected because we need historical reference

#### **Generic Repository Pattern**

**Purpose**: Reuse common CRUD operations
**Why this choice**:
- Extends `BaseRepository[AccountType]` for consistency
- Reduces boilerplate code
- Inherits common operations (get_by_id, get_all, create, update)
- Custom methods only for domain-specific queries

**Version**: Existing pattern in codebase
**Alternatives considered**:
- Custom repository from scratch: Rejected for code duplication

#### **Pydantic for Validation**

**Purpose**: Request/response validation and serialization
**Why this choice**:
- Built into FastAPI, zero-friction integration
- Automatic API documentation generation
- Type safety with Python type hints
- Clear validation errors

**Version**: Pydantic 2.x (already in project)
**Alternatives considered**: None - FastAPI standard

### 2.3 File Structure

```
src/
├── models/
│   └── account_type.py                 # NEW: SQLAlchemy model
│
├── schemas/
│   └── account_type.py                 # NEW: Pydantic schemas
│
├── repositories/
│   └── account_type_repository.py      # NEW: Database operations
│
├── services/
│   └── account_type_service.py         # NEW: Business logic
│
├── api/
│   ├── routes/
│   │   └── account_types.py            # NEW: API endpoints
│   └── dependencies.py                 # MODIFIED: Add service factory
│
├── exceptions.py                        # EXISTING: Use existing exceptions
│
└── main.py                             # MODIFIED: Register new router

alembic/
└── versions/
    └── XXXX_add_account_types_table.py # NEW: Database migration

tests/
├── integration/
│   └── test_account_type_routes.py     # NEW: API integration tests
└── unit/
    └── test_account_type_service.py    # NEW: Business logic tests
```

**Directory Purpose**:
- `models/`: Database table definitions (SQLAlchemy ORM)
- `schemas/`: API request/response validation (Pydantic)
- `repositories/`: Data access layer (database queries)
- `services/`: Business logic layer (orchestration, validation, audit)
- `api/routes/`: HTTP endpoints (request handling, status codes)
- `alembic/versions/`: Database migrations (schema changes)
- `tests/`: Automated test suite (unit and integration)

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Account Type Model

**Files Involved**:
- `src/models/account_type.py`

**Purpose**: Define the database table structure for account types using SQLAlchemy ORM.

**Implementation Requirements**:

1. **Core Logic**:
   - Create `AccountType` class inheriting from `Base` and `TimestampMixin`
   - Do NOT use `SoftDeleteMixin` (uses `is_active` flag instead)
   - Do NOT use `AuditFieldsMixin` (master data managed by system)
   - Table name: `account_types`
   - All columns mapped with proper types and constraints

2. **Data Handling**:
   - **Input validation requirements**:
     - `key`: 1-50 characters, lowercase letters/numbers/underscores only
     - `name`: 1-100 characters, required
     - `description`: 0-500 characters, optional
     - `icon_url`: 0-500 characters, optional URL
     - `sort_order`: integer, default 0
     - `is_active`: boolean, default True

   - **Column definitions**:
     ```python
     id: UUID primary key (from Base)
     key: VARCHAR(50) NOT NULL UNIQUE
     name: VARCHAR(100) NOT NULL
     description: VARCHAR(500) NULL
     icon_url: VARCHAR(500) NULL
     is_active: BOOLEAN NOT NULL DEFAULT TRUE
     sort_order: INTEGER NOT NULL DEFAULT 0
     created_at: TIMESTAMP NOT NULL (from TimestampMixin)
     updated_at: TIMESTAMP NOT NULL (from TimestampMixin)
     ```

3. **Edge Cases & Error Handling**:
   - [ ] Validate key format at database level: CHECK constraint `key ~ '^[a-z0-9_]+$'`
   - [ ] Prevent empty strings in required fields
   - [ ] Handle NULL vs empty string in optional fields
   - [ ] Ensure sort_order accepts negative integers

4. **Dependencies**:
   - Internal: `src.models.base.Base`, `src.models.mixins.TimestampMixin`
   - External: SQLAlchemy 2.0

5. **Testing Requirements**:
   - [ ] Unit test: Model instantiation with valid data
   - [ ] Unit test: Key format validation (constraint enforcement)
   - [ ] Unit test: String repr returns readable format
   - [ ] Integration test: Create record in database
   - [ ] Integration test: Unique key constraint enforcement

**Acceptance Criteria**:
- [ ] Model follows existing patterns (Base, TimestampMixin)
- [ ] All constraints properly defined
- [ ] Table name follows snake_case convention
- [ ] __repr__ provides meaningful string representation

**Implementation Notes**:
- Follow the `FinancialInstitution` model pattern (uses `is_active`, not soft delete)
- Do NOT add `deleted_at` column
- Indexes will be created in migration, not model

---

#### Component: Account Type Repository

**Files Involved**:
- `src/repositories/account_type_repository.py`

**Purpose**: Provide database operations for account types with filtering and uniqueness checks.

**Implementation Requirements**:

1. **Core Logic**:
   - Extend `BaseRepository[AccountType]` for common CRUD operations
   - Override `_apply_soft_delete_filter()` to be no-op (no soft delete)
   - Implement custom query methods:
     - `get_by_key(key: str) -> AccountType | None`
     - `exists_by_key(key: str) -> bool`
     - `get_all_active() -> list[AccountType]`
     - `get_all_ordered(is_active: bool | None = True) -> list[AccountType]`

2. **Data Handling**:
   - **Query patterns**:
     ```python
     # Get by key (case-sensitive, exact match)
     SELECT * FROM account_types WHERE key = :key

     # Check existence
     SELECT id FROM account_types WHERE key = :key

     # Get all active, sorted by sort_order
     SELECT * FROM account_types
     WHERE is_active = true
     ORDER BY sort_order ASC, name ASC
     ```

   - **Return types**: AccountType instances or None
   - **Ordering**: Always by `sort_order` ASC, then `name` ASC

3. **Edge Cases & Error Handling**:
   - [ ] Handle case sensitivity in key lookups (keys are already lowercase)
   - [ ] Return None when not found (not exceptions)
   - [ ] Handle NULL is_active (treat as False)
   - [ ] Empty list when no results

4. **Dependencies**:
   - Internal: `src.repositories.base.BaseRepository`, `src.models.account_type.AccountType`
   - External: SQLAlchemy async session

5. **Testing Requirements**:
   - [ ] Unit test: get_by_key returns correct record
   - [ ] Unit test: get_by_key returns None when not found
   - [ ] Unit test: exists_by_key returns True/False correctly
   - [ ] Unit test: get_all_active filters inactive types
   - [ ] Unit test: get_all_ordered respects sort_order
   - [ ] Integration test: Query performance with indexes

**Acceptance Criteria**:
- [ ] Extends BaseRepository correctly
- [ ] All queries use async/await
- [ ] No N+1 query issues
- [ ] Returns correct types (AccountType | None, list[AccountType], bool)

**Implementation Notes**:
- Follow `FinancialInstitutionRepository` pattern
- Use `select()` from SQLAlchemy 2.0 (not legacy Query API)
- Always use scalar_one_or_none() for single results

---

#### Component: Account Type Service

**Files Involved**:
- `src/services/account_type_service.py`

**Purpose**: Implement business logic for account type management with validation and audit logging.

**Implementation Requirements**:

1. **Core Logic**:
   - Initialize with AsyncSession
   - Create AccountTypeRepository and AuditService instances
   - Implement CRUD operations:
     - `create_account_type()` - admin only
     - `get_account_type()` - authenticated users
     - `list_account_types()` - authenticated users
     - `update_account_type()` - admin only
     - `delete_account_type()` - admin only (future: check usage)

2. **Data Handling**:
   - **Validation rules**:
     ```python
     # Key uniqueness (before create/update)
     if await repo.exists_by_key(data.key):
         raise AlreadyExistsError(f"Account type with key '{data.key}' already exists")

     # Key immutability (on update)
     if update_data.key is not None:
         raise ValidationError("Account type key cannot be changed")

     # Delete validation (future: check if in use)
     # if await repo.is_in_use(type_id):
     #     raise ConflictError("Cannot delete account type in use")
     ```

   - **Audit logging**: Log all CREATE, UPDATE, DELETE operations
   - **Error handling**: Raise domain-specific exceptions (NotFoundError, AlreadyExistsError)

3. **Edge Cases & Error Handling**:
   - [ ] Handle duplicate key on create (catch and raise AlreadyExistsError)
   - [ ] Handle update of non-existent account type (raise NotFoundError)
   - [ ] Handle delete of non-existent account type (raise NotFoundError)
   - [ ] Prevent key modification on update (immutability check)
   - [ ] Handle concurrent creates with same key (database handles uniqueness)

4. **Dependencies**:
   - Internal: `AccountTypeRepository`, `AuditService`, schemas, exceptions
   - External: None (all internal to application)

5. **Testing Requirements**:
   - [ ] Unit test: Create account type with valid data succeeds
   - [ ] Unit test: Create duplicate key raises AlreadyExistsError
   - [ ] Unit test: Update account type succeeds
   - [ ] Unit test: Update non-existent raises NotFoundError
   - [ ] Unit test: Delete account type succeeds
   - [ ] Unit test: Delete non-existent raises NotFoundError
   - [ ] Integration test: Audit logs created for all operations
   - [ ] Integration test: Key immutability enforced

**Acceptance Criteria**:
- [ ] All business rules enforced
- [ ] Proper exception handling
- [ ] All state changes audited
- [ ] Transaction management (commit on success, rollback on error)

**Implementation Notes**:
- Follow `FinancialInstitutionService` pattern closely
- Use descriptive audit log metadata
- Return Pydantic response schemas, not ORM models
- Always refresh after commit to get updated timestamps

---

#### Component: Account Type Schemas

**Files Involved**:
- `src/schemas/account_type.py`

**Purpose**: Define Pydantic models for API request/response validation and serialization.

**Implementation Requirements**:

1. **Core Logic**:
   - Create schema classes:
     - `AccountTypeBase` - common fields
     - `AccountTypeCreate` - for POST requests
     - `AccountTypeUpdate` - for PATCH requests
     - `AccountTypeResponse` - for GET responses
     - `AccountTypeListItem` - for list endpoints (compact)

2. **Schema Definitions**:
   ```python
   class AccountTypeBase(BaseModel):
       key: str = Field(min_length=1, max_length=50, pattern=r'^[a-z0-9_]+$')
       name: str = Field(min_length=1, max_length=100)
       description: str | None = Field(default=None, max_length=500)
       icon_url: str | None = Field(default=None, max_length=500)
       is_active: bool = Field(default=True)
       sort_order: int = Field(default=0)

   class AccountTypeCreate(AccountTypeBase):
       # All fields required (except optional ones with defaults)
       pass

   class AccountTypeUpdate(BaseModel):
       # All fields optional (partial update)
       # BUT key is NOT included (immutable)
       name: str | None = Field(default=None, min_length=1, max_length=100)
       description: str | None = None
       icon_url: str | None = None
       is_active: bool | None = None
       sort_order: int | None = None

   class AccountTypeResponse(AccountTypeBase):
       id: uuid.UUID
       created_at: datetime
       updated_at: datetime
       model_config = {"from_attributes": True}

   class AccountTypeListItem(BaseModel):
       id: uuid.UUID
       key: str
       name: str
       icon_url: str | None
       is_active: bool
       sort_order: int
       model_config = {"from_attributes": True}
   ```

3. **Validation Logic**:
   ```python
   @field_validator("key")
   @classmethod
   def validate_key_format(cls, value: str) -> str:
       """Validate key format: lowercase, alphanumeric, underscore only."""
       value = value.strip().lower()
       if not value:
           raise ValueError("Key cannot be empty")
       if not re.match(r'^[a-z0-9_]+$', value):
           raise ValueError("Key must contain only lowercase letters, numbers, and underscores")
       return value

   @field_validator("name", "description")
   @classmethod
   def strip_whitespace(cls, value: str | None) -> str | None:
       """Strip whitespace from string fields."""
       if value is None:
           return None
       value = value.strip()
       return value if value else None
   ```

4. **Edge Cases & Error Handling**:
   - [ ] Key validation: reject uppercase, spaces, special chars
   - [ ] String trimming: remove leading/trailing whitespace
   - [ ] Empty string handling: convert to None for optional fields
   - [ ] URL validation: basic format check for icon_url

5. **Dependencies**:
   - External: Pydantic 2.x

6. **Testing Requirements**:
   - [ ] Unit test: Valid data passes validation
   - [ ] Unit test: Invalid key format rejected (uppercase, spaces, special chars)
   - [ ] Unit test: Key auto-converts to lowercase
   - [ ] Unit test: Whitespace stripped from strings
   - [ ] Unit test: Empty description becomes None
   - [ ] Unit test: Negative sort_order accepted
   - [ ] Integration test: Schemas serialize/deserialize correctly

**Acceptance Criteria**:
- [ ] All validation rules enforced
- [ ] Clear error messages for validation failures
- [ ] Proper type hints for all fields
- [ ] Examples provided in Field() descriptions

**Implementation Notes**:
- Follow `FinancialInstitutionCreate/Update/Response` pattern
- Use Pydantic v2 syntax (`model_config` not `Config`)
- Provide clear field descriptions for API documentation

---

#### Component: Account Type API Routes

**Files Involved**:
- `src/api/routes/account_types.py`
- `src/api/dependencies.py` (add service factory)
- `src/main.py` (register router)

**Purpose**: Expose HTTP endpoints for account type management with proper authentication and authorization.

**Implementation Requirements**:

1. **Endpoint Definitions**:
   ```python
   # Public (authenticated users)
   GET  /api/v1/account-types              # List all account types
   GET  /api/v1/account-types/{id}         # Get account type by ID

   # Admin only
   POST   /api/v1/account-types            # Create account type
   PATCH  /api/v1/account-types/{id}       # Update account type
   DELETE /api/v1/account-types/{id}       # Delete account type
   POST   /api/v1/account-types/{id}/deactivate  # Deactivate (set is_active=False)
   ```

2. **Authentication & Authorization**:
   ```python
   # List and Get: Require active user
   current_user: User = Depends(require_active_user)

   # Create, Update, Delete: Require admin
   current_user: User = Depends(require_admin)
   ```

3. **Query Parameters**:
   ```python
   # GET /api/v1/account-types
   # Query params:
   # - is_active: bool | None = True  # Filter by active status
   ```

4. **Response Codes**:
   - `200 OK` - Successful GET, PATCH
   - `201 Created` - Successful POST
   - `204 No Content` - Successful DELETE
   - `400 Bad Request` - Validation error
   - `401 Unauthorized` - Missing/invalid token
   - `403 Forbidden` - Non-admin trying admin operation
   - `404 Not Found` - Account type not found
   - `409 Conflict` - Duplicate key
   - `422 Unprocessable Entity` - Pydantic validation error

5. **Edge Cases & Error Handling**:
   - [ ] Handle invalid UUID in path parameter
   - [ ] Handle missing authorization header
   - [ ] Handle non-admin user attempting admin operation
   - [ ] Handle Pydantic validation errors
   - [ ] Handle service exceptions (convert to HTTP responses)

6. **Dependencies**:
   - Internal: Service, schemas, dependencies, exceptions
   - FastAPI: APIRouter, Depends, Request, status

7. **Testing Requirements**:
   - [ ] Integration test: List account types as authenticated user
   - [ ] Integration test: Get account type by ID
   - [ ] Integration test: Create account type as admin (201)
   - [ ] Integration test: Create account type as regular user (403)
   - [ ] Integration test: Create duplicate key (409)
   - [ ] Integration test: Update account type as admin (200)
   - [ ] Integration test: Update non-existent type (404)
   - [ ] Integration test: Delete account type as admin (204)
   - [ ] Integration test: Deactivate account type
   - [ ] Integration test: Filter by is_active

**Acceptance Criteria**:
- [ ] All endpoints properly documented (docstrings)
- [ ] Proper HTTP status codes
- [ ] Authentication enforced on all endpoints
- [ ] Authorization enforced (admin vs regular user)
- [ ] Audit logging for all state changes

**Implementation Notes**:
- Follow `financial_institutions.py` route pattern
- Use `require_active_user` and `require_admin` from dependencies
- Extract request_id from request.state for audit logging
- Pass IP address and user agent to service methods

---

#### Component: Database Migration

**Files Involved**:
- `alembic/versions/XXXX_add_account_types_table.py`

**Purpose**: Create the account_types table with constraints, indexes, and seed data.

**Implementation Requirements**:

1. **Table Creation**:
   ```sql
   CREATE TABLE account_types (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       key VARCHAR(50) NOT NULL,
       name VARCHAR(100) NOT NULL,
       description VARCHAR(500),
       icon_url VARCHAR(500),
       is_active BOOLEAN NOT NULL DEFAULT TRUE,
       sort_order INTEGER NOT NULL DEFAULT 0,
       created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
   );
   ```

2. **Constraints**:
   ```sql
   -- Unique constraint on key
   ALTER TABLE account_types
   ADD CONSTRAINT uq_account_types_key UNIQUE (key);

   -- Check constraint for key format
   ALTER TABLE account_types
   ADD CONSTRAINT ck_account_types_key_format
   CHECK (key ~ '^[a-z0-9_]+$');
   ```

3. **Indexes**:
   ```sql
   -- Primary key index (automatic)
   -- Unique index on key (automatic from constraint)

   -- Index on is_active for filtering
   CREATE INDEX ix_account_types_is_active
   ON account_types(is_active);

   -- Index on sort_order for ordering
   CREATE INDEX ix_account_types_sort_order
   ON account_types(sort_order);
   ```

4. **Seed Data** (in migration):
   ```python
   # Insert 4 default account types
   op.execute("""
       INSERT INTO account_types (id, key, name, description, is_active, sort_order, created_at, updated_at)
       VALUES
           (gen_random_uuid(), 'checking', 'Checking Account',
            'Standard checking account for daily transactions and bill payments',
            true, 1, NOW(), NOW()),
           (gen_random_uuid(), 'savings', 'Savings Account',
            'Savings account for building emergency funds and long-term savings',
            true, 2, NOW(), NOW()),
           (gen_random_uuid(), 'investment', 'Investment Account',
            'Investment and brokerage accounts for stocks, bonds, and mutual funds',
            true, 3, NOW(), NOW()),
           (gen_random_uuid(), 'other', 'Other',
            'Other financial accounts not covered by standard types',
            true, 99, NOW(), NOW())
   """)
   ```

5. **Downgrade**:
   ```python
   def downgrade():
       op.drop_table('account_types')
   ```

6. **Edge Cases & Error Handling**:
   - [ ] Handle migration failure (rollback)
   - [ ] Verify seed data created successfully
   - [ ] Check constraint validates existing data
   - [ ] Idempotent seed (skip if types already exist)

7. **Testing Requirements**:
   - [ ] Test: Migration runs successfully
   - [ ] Test: Downgrade removes table
   - [ ] Test: All 4 seed types exist after migration
   - [ ] Test: Unique constraint enforced
   - [ ] Test: Check constraint enforced (invalid keys rejected)
   - [ ] Test: Indexes created

**Acceptance Criteria**:
- [ ] Migration is idempotent (can run multiple times safely)
- [ ] All constraints properly named following convention
- [ ] Seed data matches specification exactly
- [ ] Downgrade fully reverses migration

**Implementation Notes**:
- Use Alembic's `op.execute()` for seed data
- Add `ON CONFLICT DO NOTHING` to seed inserts for idempotency
- Name constraints following project convention (ck_, uq_, ix_)
- Use `gen_random_uuid()` for UUID generation in SQL

---

#### Component: API Dependencies

**Files Involved**:
- `src/api/dependencies.py`

**Purpose**: Add service factory function for dependency injection.

**Implementation Requirements**:

1. **Service Factory**:
   ```python
   async def get_account_type_service(
       session: AsyncSession = Depends(get_db),
   ) -> AccountTypeService:
       """Dependency to get AccountTypeService instance."""
       return AccountTypeService(session)
   ```

2. **Edge Cases & Error Handling**:
   - [ ] Handle database session errors (propagate to caller)

3. **Testing Requirements**:
   - [ ] Integration test: Factory returns valid service instance

**Acceptance Criteria**:
- [ ] Follows existing pattern (get_financial_institution_service)
- [ ] Properly typed

**Implementation Notes**:
- Add near other service factories
- Use same pattern as existing factories

---

#### Component: Router Registration

**Files Involved**:
- `src/main.py`

**Purpose**: Register the account types router with the FastAPI application.

**Implementation Requirements**:

1. **Router Registration**:
   ```python
   from src.api.routes import account_types

   app.include_router(
       account_types.router,
       prefix="/api/v1",
       tags=["Account Types"],
   )
   ```

2. **Edge Cases & Error Handling**:
   - [ ] Ensure router registered before app starts

3. **Testing Requirements**:
   - [ ] Integration test: All endpoints accessible

**Acceptance Criteria**:
- [ ] Router registered in correct order (after auth, before custom routes)
- [ ] Prefix and tags match existing routers

**Implementation Notes**:
- Add near other router registrations
- Maintain alphabetical order if possible

---

### 3.2 Audit Actions

**Files Involved**:
- `src/models/audit_log.py`

**Purpose**: Add audit action enums for account type operations.

**Implementation Requirements**:

Add to `AuditAction` enum:
```python
# Account type management
CREATE_ACCOUNT_TYPE = "CREATE_ACCOUNT_TYPE"
UPDATE_ACCOUNT_TYPE = "UPDATE_ACCOUNT_TYPE"
DELETE_ACCOUNT_TYPE = "DELETE_ACCOUNT_TYPE"
DEACTIVATE_ACCOUNT_TYPE = "DEACTIVATE_ACCOUNT_TYPE"
```

**Usage in Service**:
```python
await self.audit_service.log_event(
    user_id=current_user.id,
    action=AuditAction.CREATE_ACCOUNT_TYPE,
    entity_type="account_type",
    entity_id=account_type.id,
    new_values={
        "key": account_type.key,
        "name": account_type.name,
    },
    request_id=request_id,
    ip_address=ip_address,
    user_agent=user_agent,
)
```

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

This is a small, focused feature that can be implemented in a **single phase**. Breaking it into sub-phases would add unnecessary overhead.

#### Phase 1: Complete Account Types Master Data (Size: M, Priority: P0)

**Goal**: Deliver a complete, production-ready account types master data system that enables administrators to manage account types without code changes and provides all users with access to view and select from available account types.

**Scope**:
- ✅ Include: Complete CRUD operations, authentication/authorization, audit logging, seed data, comprehensive tests
- ❌ Exclude: Integration with accounts table (happens in future feature), usage tracking, bulk operations

**Components to Implement**:
1. Database schema (model + migration)
2. Repository layer (data access)
3. Service layer (business logic)
4. API routes (HTTP endpoints)
5. Pydantic schemas (validation)
6. Integration tests (API testing)
7. Unit tests (service/repository)

**Detailed Tasks**:

1. **Database & Model Setup** (4 hours)
   - [ ] Create `src/models/account_type.py` with SQLAlchemy model
   - [ ] Add `AccountType` to `src/models/__init__.py`
   - [ ] Create Alembic migration `XXXX_add_account_types_table.py`
   - [ ] Add table creation SQL
   - [ ] Add unique constraint on key
   - [ ] Add check constraint for key format
   - [ ] Add indexes (is_active, sort_order)
   - [ ] Add seed data for 4 default types
   - [ ] Test migration upgrade/downgrade
   - [ ] Verify seed data created

2. **Repository Layer** (3 hours)
   - [ ] Create `src/repositories/account_type_repository.py`
   - [ ] Extend BaseRepository[AccountType]
   - [ ] Implement `get_by_key()`
   - [ ] Implement `exists_by_key()`
   - [ ] Implement `get_all_active()`
   - [ ] Implement `get_all_ordered()`
   - [ ] Override `_apply_soft_delete_filter()` (no-op)
   - [ ] Add to `src/repositories/__init__.py`
   - [ ] Write unit tests for each method

3. **Pydantic Schemas** (2 hours)
   - [ ] Create `src/schemas/account_type.py`
   - [ ] Implement `AccountTypeBase`
   - [ ] Implement `AccountTypeCreate`
   - [ ] Implement `AccountTypeUpdate` (no key field)
   - [ ] Implement `AccountTypeResponse`
   - [ ] Implement `AccountTypeListItem`
   - [ ] Add field validators (key format, whitespace stripping)
   - [ ] Add to `src/schemas/__init__.py`
   - [ ] Write validation tests

4. **Service Layer** (6 hours)
   - [ ] Create `src/services/account_type_service.py`
   - [ ] Implement `create_account_type()` with uniqueness check
   - [ ] Implement `get_account_type()` with NotFoundError
   - [ ] Implement `list_account_types()` with filtering
   - [ ] Implement `update_account_type()` with key immutability
   - [ ] Implement `delete_account_type()` (future: usage check)
   - [ ] Add audit logging to all state-changing methods
   - [ ] Add to `src/services/__init__.py`
   - [ ] Write unit tests for each method
   - [ ] Write integration tests with database

5. **API Routes** (5 hours)
   - [ ] Create `src/api/routes/account_types.py`
   - [ ] Implement POST / (create, admin only)
   - [ ] Implement GET / (list, authenticated)
   - [ ] Implement GET /{id} (get by ID, authenticated)
   - [ ] Implement PATCH /{id} (update, admin only)
   - [ ] Implement DELETE /{id} (delete, admin only)
   - [ ] Implement POST /{id}/deactivate (deactivate, admin only)
   - [ ] Add comprehensive docstrings
   - [ ] Add service factory to `src/api/dependencies.py`
   - [ ] Register router in `src/main.py`

6. **Integration Tests** (6 hours)
   - [ ] Create `tests/integration/test_account_type_routes.py`
   - [ ] Test: List account types as authenticated user (200)
   - [ ] Test: List account types without auth (401)
   - [ ] Test: List with is_active filter
   - [ ] Test: Get account type by ID (200)
   - [ ] Test: Get non-existent type (404)
   - [ ] Test: Create account type as admin (201)
   - [ ] Test: Create account type as regular user (403)
   - [ ] Test: Create duplicate key (409)
   - [ ] Test: Create with invalid key format (422)
   - [ ] Test: Update account type as admin (200)
   - [ ] Test: Update with key change attempt (400)
   - [ ] Test: Update non-existent type (404)
   - [ ] Test: Delete account type (204)
   - [ ] Test: Deactivate account type (200)
   - [ ] Test: Verify audit logs created
   - [ ] Test: Verify seed data exists

7. **Audit Actions** (1 hour)
   - [ ] Add enums to `src/models/audit_log.py`:
     - CREATE_ACCOUNT_TYPE
     - UPDATE_ACCOUNT_TYPE
     - DELETE_ACCOUNT_TYPE
     - DEACTIVATE_ACCOUNT_TYPE
   - [ ] Test audit logging in integration tests

8. **Code Quality & Documentation** (3 hours)
   - [ ] Run `uv run ruff format .`
   - [ ] Run `uv run ruff check --fix .`
   - [ ] Run `uv run mypy src/`
   - [ ] Fix all linting/typing issues
   - [ ] Run `uv run pytest tests/ --cov=src --cov-report=term-missing`
   - [ ] Ensure 80%+ coverage
   - [ ] Update API documentation (verify Swagger UI)
   - [ ] Add inline code comments where needed

**Dependencies**:
- None (foundational feature)

**Blocks**:
- Feature 3 (Link accounts to account types) - requires this foundation

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (100% pass rate)
- [ ] Test coverage ≥ 80% for new code
- [ ] Migration runs successfully on clean database
- [ ] All 4 seed types exist after migration
- [ ] Admin can create/update/delete account types via API
- [ ] Regular users can list/view account types
- [ ] Regular users cannot create/update/delete (403 Forbidden)
- [ ] Duplicate key returns 409 Conflict
- [ ] Invalid key format returns 422 Unprocessable Entity
- [ ] All state changes logged to audit trail
- [ ] Code passes ruff format/check and mypy
- [ ] API documented in Swagger UI
- [ ] No breaking changes to existing endpoints

**Risk Factors**:
- **Risk**: Migration seed data uses wrong format for keys
  - **Mitigation**: Add validation test that checks seed data keys against format constraint

- **Risk**: Key immutability not enforced properly
  - **Mitigation**: Integration test that attempts key change and verifies rejection

- **Risk**: Audit actions conflict with existing enums
  - **Mitigation**: Review existing audit actions before adding new ones

**Estimated Effort**:
- **Total**: 30 hours (3-4 developer days at 8 hours/day)
- **Breakdown**:
  - Database/Model: 4 hours
  - Repository: 3 hours
  - Schemas: 2 hours
  - Service: 6 hours
  - API Routes: 5 hours
  - Integration Tests: 6 hours
  - Audit Actions: 1 hour
  - Code Quality: 3 hours

### 4.2 Implementation Sequence

```
┌─────────────────────────────────────────────┐
│ Phase 1: Complete Implementation (P0)      │
│ 3-4 developer days                          │
└─────────────────────────────────────────────┘
         │
         ├── Step 1: Database (4h)
         │   ├── Model
         │   ├── Migration
         │   └── Seed data
         │
         ├── Step 2: Data Access (3h)
         │   └── Repository
         │
         ├── Step 3: Validation (2h)
         │   └── Pydantic schemas
         │
         ├── Step 4: Business Logic (6h)
         │   └── Service layer
         │
         ├── Step 5: API (5h)
         │   ├── Routes
         │   ├── Dependencies
         │   └── Router registration
         │
         ├── Step 6: Testing (6h)
         │   ├── Integration tests
         │   └── Unit tests
         │
         ├── Step 7: Audit (1h)
         │   └── Audit actions
         │
         └── Step 8: Quality (3h)
             ├── Linting
             ├── Type checking
             ├── Coverage
             └── Documentation
```

**Rationale for ordering**:
- Database first: Foundation for all other layers
- Repository second: Data access needed for service layer
- Schemas third: Validation needed before API routes
- Service fourth: Business logic needed for routes
- API fifth: HTTP layer depends on service
- Testing sixth: Verify all components work together
- Audit seventh: Add logging to existing operations
- Quality last: Ensure production-ready code

**Quick Wins**: None - this is a cohesive feature that delivers value when complete.

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. A single database table with CRUD operations is the simplest approach for master data. Considered more complex alternatives like hierarchical types, categories, or versioning - all rejected as premature.

- [x] **Have we avoided premature optimization?**
  - Yes. No caching, no complex query optimization, no denormalization. Relying on PostgreSQL indexes for performance, which is sufficient for a master data table with <1000 rows.

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. Follows the exact same pattern as `financial_institutions`:
    - Uses `is_active` flag instead of soft delete
    - Extends `BaseRepository`
    - Uses `TimestampMixin` but not `AuditFieldsMixin` or `SoftDeleteMixin`
    - Service/Repository/Routes structure identical

- [x] **Can we deliver value in smaller increments?**
  - No. This is already minimal. The feature only delivers value when complete (users need to be able to select account types). Breaking it down further would create incomplete, unusable functionality.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. The actual problem is: "Users cannot create HSA, 401k, or crypto accounts because types are hardcoded." This solution directly addresses that by making types configurable.

### Alternatives Considered

**Alternative 1: Keep enum, add "custom" type with user-defined labels**
- **Description**: Keep `AccountType` enum, add `CUSTOM` value, allow users to provide custom label
- **Why NOT chosen**:
  - Doesn't solve the core problem (standardization across platform)
  - Every user would have different labels for same concept (HSA, 401k)
  - No admin control over available types
  - Complicates reporting and analytics

**Alternative 2: Hierarchical account types (categories + types)**
- **Description**: Create parent/child relationship (e.g., "Investment" → "401k", "IRA", "Brokerage")
- **Why NOT chosen**:
  - Over-engineered for current requirements
  - No business need for hierarchies identified
  - Significantly increases complexity (recursive queries, tree structures)
  - Can add later if needed (YAGNI principle)

**Alternative 3: PostgreSQL enum migration**
- **Description**: Keep using PostgreSQL enum, but migrate values
- **Why NOT chosen**:
  - PostgreSQL enums are difficult to modify (requires migrations for every change)
  - Cannot add metadata (description, icon, sort order)
  - No way to deactivate values
  - Defeats the purpose of making types configurable

**Alternative 4: User-owned account types (multi-tenant)**
- **Description**: Each user can create their own account types
- **Why NOT chosen**:
  - Creates data fragmentation
  - Complicates aggregation and reporting
  - Defeats standardization purpose
  - Current requirement is admin-managed global types

**Rationale**: The proposed approach (single master data table, admin-managed, global) is the simplest solution that:
1. Solves the immediate problem (enable specialized account types)
2. Follows existing patterns (financial_institutions)
3. Provides flexibility without over-engineering
4. Can be extended later if needed (hierarchies, categories, user types)

---

## 6. References & Related Documents

### Internal Documentation

- **Project Standards**: `.claude/standards/backend.md` - Backend development standards
- **Database Standards**: `.claude/standards/database.md` - Database design patterns
- **API Standards**: `.claude/standards/api.md` - API endpoint conventions
- **Testing Standards**: `.claude/standards/testing.md` - Test coverage requirements
- **Feature Description**: `.features/descriptions/feat-02-account-types.md` - Original requirements

### Related Code References

- **Similar Pattern**: `src/models/financial_institution.py` - Master data model with is_active
- **Repository Pattern**: `src/repositories/financial_institution_repository.py` - Reference implementation
- **Service Pattern**: `src/services/financial_institution_service.py` - Business logic reference
- **API Routes Pattern**: `src/api/routes/financial_institutions.py` - HTTP endpoint reference
- **Schema Pattern**: `src/schemas/financial_institution.py` - Pydantic validation reference
- **Migration Pattern**: Previous migrations in `alembic/versions/` - Migration structure
- **Test Pattern**: `tests/integration/test_financial_institution_routes.py` - Integration test reference

### External Resources

**FastAPI Best Practices**:
- [FastAPI Best Practices (GitHub)](https://github.com/zhanymkanov/fastapi-best-practices) - Comprehensive guide
- [FastAPI Best Practices Guide with Examples](https://developer-service.blog/fastapi-best-practices-a-condensed-guide-with-examples/) - Condensed guide
- [FastAPI Design Patterns (Medium)](https://medium.com/@lautisuarez081/fastapi-best-practices-and-design-patterns-building-quality-python-apis-31774ff3c28a) - Design patterns

**SQLAlchemy 2.0**:
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) - Official docs
- [SQLAlchemy Async Tutorial](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Async patterns

**Pydantic**:
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/) - Validation and serialization
- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/) - Custom validation

**Database Design**:
- [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) - CHECK, UNIQUE constraints
- [PostgreSQL Indexes](https://www.postgresql.org/docs/current/indexes.html) - Index types and usage

**Master Data Management**:
- [Master Data Management Patterns](https://www.oreilly.com/library/view/master-data-management/9780123742254/) - MDM concepts
- [Reference Data Management](https://www.dataversity.net/reference-data-management-best-practices/) - Best practices

**Testing**:
- [Pytest Documentation](https://docs.pytest.org/) - Testing framework
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Async testing
- [HTTPX AsyncClient](https://www.python-httpx.org/async/) - API testing

**Code Quality**:
- [Ruff](https://docs.astral.sh/ruff/) - Fast Python linter
- [MyPy](https://mypy.readthedocs.io/) - Static type checking

---

## 7. Security Considerations

### Authentication & Authorization

- **Authentication**: All endpoints require valid JWT access token
- **Authorization**:
  - List/Get: Any authenticated user (`require_active_user`)
  - Create/Update/Delete: Admin only (`require_admin`)
- **Token Validation**: Handled by existing middleware (no changes needed)

### Input Validation

- **Key Format**: Regex validation prevents SQL injection via key field
- **String Length**: Max lengths prevent buffer overflow attacks
- **SQL Injection**: SQLAlchemy parameterized queries prevent SQL injection
- **XSS Prevention**: No HTML rendering in API (frontend responsibility)

### Audit Trail

- **Immutable Logs**: All CREATE/UPDATE/DELETE operations logged to audit_log
- **Who/What/When**: User ID, action type, timestamp recorded
- **Compliance**: GDPR and SOX compliant audit trail

### Data Integrity

- **Unique Constraints**: Prevent duplicate keys at database level
- **Check Constraints**: Validate key format at database level
- **Transactions**: All mutations wrapped in database transactions
- **Rollback**: Failed operations automatically rolled back

### Rate Limiting

- **Existing Middleware**: Redis-backed rate limiting already in place
- **No Special Handling**: Master data operations use default rate limits

---

## 8. Performance Considerations

### Query Performance

- **Indexes**:
  - Primary key index on `id` (automatic)
  - Unique index on `key` (automatic from constraint)
  - Index on `is_active` (manual, for filtering)
  - Index on `sort_order` (manual, for ordering)
- **Expected Query Patterns**:
  - List all active types: Uses `is_active` index
  - Get by key: Uses unique key index
  - Get by ID: Uses primary key index

### Data Volume

- **Expected Rows**: <1,000 account types (likely <100)
- **Growth Rate**: Minimal (admin-managed, infrequent additions)
- **Table Size**: <1MB (small master data table)
- **Cache Strategy**: None needed (PostgreSQL handles small tables efficiently)

### API Performance

- **Response Time Target**: <100ms for list/get operations
- **N+1 Queries**: None (single query per operation)
- **Pagination**: Not needed (small dataset, always return all)
- **Lazy Loading**: Not applicable (no relationships yet)

### Scalability

- **Concurrent Requests**: Database handles concurrency via transactions
- **Write Conflicts**: Unique constraint at database level prevents duplicates
- **Read Scalability**: Minimal concern (small table, heavy indexes)

---

## 9. Future Enhancements (Out of Scope)

The following enhancements are explicitly **out of scope** for this implementation but may be considered in future iterations:

### 1. Account Type Categories/Grouping
- **Description**: Group account types into categories (e.g., "Retirement" → 401k, IRA, Roth IRA)
- **Why Later**: No current requirement, adds complexity, YAGNI principle

### 2. Icon Picker UI Component
- **Description**: Admin UI for selecting icons from predefined set
- **Why Later**: Backend-focused feature, frontend out of scope

### 3. Usage Statistics
- **Description**: Track how many accounts use each account type
- **Why Later**: Requires integration with accounts table (future feature)

### 4. Bulk Operations
- **Description**: Bulk create/update/delete account types via CSV import
- **Why Later**: Not needed for MVP, can add if demand exists

### 5. Account Type Templates
- **Description**: Pre-defined templates for common account types (HSA, 401k, etc.)
- **Why Later**: Can seed via migration if needed, templates add complexity

### 6. Localization/i18n
- **Description**: Multi-language support for account type names/descriptions
- **Why Later**: No current requirement for internationalization

### 7. Account Type Versioning
- **Description**: Track historical changes to account type definitions
- **Why Later**: Audit log provides sufficient history, versioning adds complexity

### 8. User-Specific Account Types
- **Description**: Allow users to create personal account types
- **Why Later**: Conflicts with standardization goal, may revisit based on feedback

---

## 10. Acceptance Testing Checklist

Before marking this feature as complete, verify the following:

### Database

- [ ] Migration runs successfully on clean database
- [ ] Migration is reversible (downgrade works)
- [ ] All 4 seed types exist after migration
- [ ] Unique constraint on key enforced
- [ ] Check constraint on key format enforced
- [ ] Indexes created (is_active, sort_order)

### Repository

- [ ] `get_by_key()` returns correct account type
- [ ] `get_by_key()` returns None for non-existent key
- [ ] `exists_by_key()` returns True/False correctly
- [ ] `get_all_active()` filters inactive types
- [ ] `get_all_ordered()` respects sort_order

### Service

- [ ] Create account type with valid data succeeds
- [ ] Create duplicate key raises AlreadyExistsError
- [ ] Update account type succeeds
- [ ] Update with key change raises ValidationError
- [ ] Delete account type succeeds
- [ ] Audit logs created for all operations

### API (Authenticated User)

- [ ] GET /api/v1/account-types returns 200 with list
- [ ] GET /api/v1/account-types?is_active=false includes inactive
- [ ] GET /api/v1/account-types/{id} returns 200 with details
- [ ] GET /api/v1/account-types/{id} returns 404 for non-existent
- [ ] POST /api/v1/account-types returns 403 (Forbidden)
- [ ] PATCH /api/v1/account-types/{id} returns 403 (Forbidden)
- [ ] DELETE /api/v1/account-types/{id} returns 403 (Forbidden)

### API (Admin User)

- [ ] POST /api/v1/account-types returns 201 with created type
- [ ] POST duplicate key returns 409 (Conflict)
- [ ] POST invalid key format returns 422 (Unprocessable Entity)
- [ ] PATCH /api/v1/account-types/{id} returns 200 with updated type
- [ ] PATCH with key change returns 400 (Bad Request)
- [ ] PATCH non-existent returns 404 (Not Found)
- [ ] DELETE /api/v1/account-types/{id} returns 204 (No Content)
- [ ] POST /api/v1/account-types/{id}/deactivate returns 200

### API (Unauthenticated)

- [ ] All endpoints return 401 (Unauthorized) without token

### Audit Trail

- [ ] CREATE_ACCOUNT_TYPE logged on create
- [ ] UPDATE_ACCOUNT_TYPE logged on update
- [ ] DELETE_ACCOUNT_TYPE logged on delete
- [ ] DEACTIVATE_ACCOUNT_TYPE logged on deactivate
- [ ] Audit logs include user_id, entity_id, timestamp
- [ ] Audit logs include IP address and user agent

### Code Quality

- [ ] All tests pass (100% pass rate)
- [ ] Test coverage ≥ 80% for new code
- [ ] Ruff format passes (no formatting issues)
- [ ] Ruff check passes (no linting errors)
- [ ] MyPy passes (no type errors)
- [ ] All functions have type hints
- [ ] All public methods have docstrings

### Documentation

- [ ] API endpoints documented in Swagger UI
- [ ] All schemas have field descriptions
- [ ] README updated if needed
- [ ] Inline comments where logic is complex

### Non-Functional

- [ ] No breaking changes to existing endpoints
- [ ] List endpoint responds in <100ms
- [ ] Create endpoint responds in <200ms
- [ ] No N+1 query issues
- [ ] Database indexes used in queries

---

## Appendix A: SQL Schema Definition

**Complete SQL for account_types table**:

```sql
-- Create account_types table
CREATE TABLE account_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    icon_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Add unique constraint on key
ALTER TABLE account_types
ADD CONSTRAINT uq_account_types_key UNIQUE (key);

-- Add check constraint for key format (lowercase, alphanumeric, underscore only)
ALTER TABLE account_types
ADD CONSTRAINT ck_account_types_key_format
CHECK (key ~ '^[a-z0-9_]+$');

-- Create index on is_active for filtering
CREATE INDEX ix_account_types_is_active
ON account_types(is_active);

-- Create index on sort_order for ordering
CREATE INDEX ix_account_types_sort_order
ON account_types(sort_order);

-- Seed default account types
INSERT INTO account_types (key, name, description, is_active, sort_order, created_at, updated_at)
VALUES
    ('checking', 'Checking Account',
     'Standard checking account for daily transactions and bill payments',
     true, 1, NOW(), NOW()),
    ('savings', 'Savings Account',
     'Savings account for building emergency funds and long-term savings',
     true, 2, NOW(), NOW()),
    ('investment', 'Investment Account',
     'Investment and brokerage accounts for stocks, bonds, and mutual funds',
     true, 3, NOW(), NOW()),
    ('other', 'Other',
     'Other financial accounts not covered by standard types',
     true, 99, NOW(), NOW())
ON CONFLICT (key) DO NOTHING;  -- Idempotent insert
```

---

## Appendix B: API Examples

### Create Account Type (Admin)

```bash
POST /api/v1/account-types
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
  "key": "hsa",
  "name": "Health Savings Account",
  "description": "Tax-advantaged medical savings account for qualified health expenses",
  "icon_url": "https://example.com/icons/hsa.svg",
  "is_active": true,
  "sort_order": 10
}

# Response: 201 Created
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "key": "hsa",
  "name": "Health Savings Account",
  "description": "Tax-advantaged medical savings account for qualified health expenses",
  "icon_url": "https://example.com/icons/hsa.svg",
  "is_active": true,
  "sort_order": 10,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### List Account Types (Any User)

```bash
GET /api/v1/account-types?is_active=true
Authorization: Bearer <access_token>

# Response: 200 OK
[
  {
    "id": "...",
    "key": "checking",
    "name": "Checking Account",
    "icon_url": null,
    "is_active": true,
    "sort_order": 1
  },
  {
    "id": "...",
    "key": "savings",
    "name": "Savings Account",
    "icon_url": null,
    "is_active": true,
    "sort_order": 2
  },
  {
    "id": "...",
    "key": "investment",
    "name": "Investment Account",
    "icon_url": null,
    "is_active": true,
    "sort_order": 3
  },
  {
    "id": "...",
    "key": "hsa",
    "name": "Health Savings Account",
    "icon_url": "https://example.com/icons/hsa.svg",
    "is_active": true,
    "sort_order": 10
  }
]
```

### Update Account Type (Admin)

```bash
PATCH /api/v1/account-types/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
  "name": "HSA - Health Savings",
  "sort_order": 5
}

# Response: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "key": "hsa",
  "name": "HSA - Health Savings",
  "description": "Tax-advantaged medical savings account for qualified health expenses",
  "icon_url": "https://example.com/icons/hsa.svg",
  "is_active": true,
  "sort_order": 5,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

### Deactivate Account Type (Admin)

```bash
POST /api/v1/account-types/550e8400-e29b-41d4-a716-446655440000/deactivate
Authorization: Bearer <admin_access_token>

# Response: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "key": "hsa",
  "name": "HSA - Health Savings",
  "description": "Tax-advantaged medical savings account for qualified health expenses",
  "icon_url": "https://example.com/icons/hsa.svg",
  "is_active": false,
  "sort_order": 5,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:40:00Z"
}
```

---

**End of Implementation Plan**
