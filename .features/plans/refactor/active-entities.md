# Implementation Plan: Soft Delete Consistency Refactoring

## Executive Summary

This refactoring establishes a single, consistent soft delete pattern across the Emerald Finance Platform backend by eliminating the redundant `is_active` boolean field and relying exclusively on the `deleted_at` timestamp field for entity status management.

### Primary Objectives

1. **Eliminate Redundancy**: Remove all `is_active` fields from models, as they duplicate the functionality of `deleted_at`
2. **Establish Clear Patterns**: Define which models use soft delete (via `deleted_at`) and which use hard delete
3. **Maintain Data Integrity**: Ensure all business logic, queries, and APIs correctly reflect the new pattern
4. **Preserve Compliance**: Maintain 7-year retention requirements for financial data through consistent soft delete implementation

### Expected Outcomes

- **Simplified Model Architecture**: Single source of truth for entity status (`deleted_at`)
- **Clearer Business Logic**: Elimination of dual-flag confusion (`is_active` vs `deleted_at`)
- **Consistent Querying**: All repository queries use the same soft delete filtering mechanism
- **Reduced Cognitive Load**: Developers no longer need to manage two separate status fields

### Success Criteria

- All five specified models (User, Account, Card, FinancialInstitution, Transaction) correctly implement soft delete via `deleted_at`
- Zero models in the codebase have an `is_active` field
- All tests pass with 80%+ coverage maintained
- All API endpoints continue to function with updated schemas
- Database schema matches model definitions exactly

---

## Technical Architecture

### 2.1 System Design Overview

**Current State:**
```
Models use BOTH is_active and deleted_at
├── is_active = True/False (active/inactive)
└── deleted_at = NULL/<timestamp> (active/deleted)

Problem: Two fields for same concept creates confusion
Example: What does is_active=False + deleted_at=NULL mean?
```

**Target State:**
```
Repository Layer (ONLY layer aware of deleted_at):
├── deleted_at = NULL → Entity is active (returned by queries)
└── deleted_at = <timestamp> → Entity is soft-deleted (filtered out)

Service Layer (status-agnostic):
├── Entity returned from repository → Guaranteed active, proceed with business logic
└── Repository returns None → Entity not found (deleted OR never existed = same)

Clear semantics: Single field, single responsibility, clear layer separation
```

**Model Classification:**

| Model | Pattern | Rationale |
|-------|---------|-----------|
| **Soft Delete (5 models)** |
| User | `deleted_at` | Regulatory compliance, audit trail, authentication history |
| Account | `deleted_at` | Financial data retention, transaction history preservation |
| Card | `deleted_at` | Payment history, spending analysis, compliance |
| FinancialInstitution | ~~`is_active`~~ → `deleted_at` | Master data, historical references, institution lifecycle |
| Transaction | `deleted_at` | 7-year SOX/GDPR retention, immutable audit trail |
| **Hard Delete (all others)** |
| AccountType | Hard delete | Master data that can be permanently removed |
| AccountShare | Hard delete | Junction table, no compliance requirements |
| RefreshToken | Hard delete | Security tokens, no retention needed |
| AuditLog | Hard delete | Immutable by nature, never deleted in practice |
| RefreshToken | Hard delete | Expired tokens cleaned up permanently |

**Critical Architecture Principle:**

```
┌─────────────────────────────────────────────────────────┐
│ Repository Layer                                        │
│ - ONLY layer aware of deleted_at field                 │
│ - Automatically filters deleted_at IS NULL             │
│ - Returns only active entities                          │
│ - Returns None for deleted/non-existent entities        │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼ Returns entity OR None
┌─────────────────────────────────────────────────────────┐
│ Service Layer                                           │
│ - NEVER checks is_active or deleted_at                 │
│ - If entity received: Guaranteed active, proceed       │
│ - If None received: Not found (doesn't matter why)     │
│ - Treats "deleted" and "never existed" as equivalent   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼ Business logic result
┌─────────────────────────────────────────────────────────┐
│ API/Route Layer                                         │
│ - NEVER checks entity status                           │
│ - Receives results from service layer                  │
│ - Returns 404 if service raises NotFoundError          │
└─────────────────────────────────────────────────────────┘
```

**Key Architectural Changes:**

1. **FinancialInstitution Migration**: Currently uses `is_active` for deactivation. Will be migrated to use `deleted_at` for consistency with soft delete pattern.

2. **AccountType Clarification**: Currently uses `is_active`. Will REMOVE `is_active` and use hard delete only, as account types are master data without compliance requirements.

3. **Repository Layer**: `BaseRepository._apply_soft_delete_filter()` already handles `deleted_at` filtering automatically for all models with the field. This is the ONLY layer that knows about or checks `deleted_at`.

4. **Service Layer**: Business logic that references `is_active` must be removed. Services NEVER check entity status - they trust repository filtering. If a repository returns an entity, it's active. If it returns `None`, the entity doesn't exist (or is deleted, which is equivalent).

5. **API Layer**: Schemas with `is_active` fields must be updated to remove them. No explicit filtering by status - repositories handle this automatically.

### 2.2 Technology Decisions

**Database Migration Strategy**

**Technology**: Alembic 1.13+
- **Purpose**: Schema migrations for column removal and data migration
- **Why this choice**: Already used throughout project, native SQLAlchemy integration
- **Version**: Current project version (1.13+)
- **Alternatives considered**:
  - Raw SQL scripts (rejected: no version control, no rollback)
  - Manual migrations (rejected: error-prone, not reproducible)

**Data Migration Approach**: Multi-step migration
1. Add `deleted_at` where missing (FinancialInstitution already has it via SoftDeleteMixin... NO, it doesn't!)
2. Migrate `is_active=False` → `deleted_at=NOW()`
3. Remove `is_active` columns
4. Update indexes and constraints

**Testing Strategy**

**Technology**: pytest + pytest-asyncio
- **Purpose**: Comprehensive test coverage for refactored code
- **Why this choice**: Already project standard, async support required
- **Approach**: Update existing tests, add regression tests for status checking

### 2.3 File Structure

```
src/
├── models/                          # [MODIFIED] Remove is_active from 5 models
│   ├── user.py                      # Remove is_active (line 90-95)
│   ├── account.py                   # Remove is_active (line 177-181)
│   ├── financial_institution.py     # Add SoftDeleteMixin, remove is_active
│   ├── account_type.py              # Remove is_active (line 97-102)
│   └── mixins.py                    # [NO CHANGE] SoftDeleteMixin already correct
│
├── repositories/                    # [MODIFIED] Update queries removing is_active filters
│   ├── base.py                      # [NO CHANGE] Already handles deleted_at correctly
│   ├── user_repository.py           # Remove is_active filtering
│   ├── account_repository.py        # Remove is_active filtering
│   ├── financial_institution_repository.py  # Remove is_active filtering
│   ├── account_type_repository.py   # Remove is_active filtering
│   └── card_repository.py           # [VERIFY] Check for is_active usage
│
├── services/                        # [MODIFIED] Update business logic
│   ├── user_service.py              # Replace is_active checks with deleted_at checks
│   ├── account_service.py           # Replace is_active checks with deleted_at checks
│   ├── card_service.py              # Replace is_active checks with deleted_at checks
│   ├── financial_institution_service.py  # Replace is_active checks with deleted_at checks
│   ├── account_type_service.py      # Replace is_active checks with deleted_at checks
│   └── auth_service.py              # Update login logic (is_active check)
│
├── schemas/                         # [MODIFIED] Update Pydantic schemas
│   ├── user.py                      # Remove is_active from all schemas
│   ├── account.py                   # Remove is_active from all schemas
│   ├── financial_institution.py     # Remove is_active from all schemas
│   └── account_type.py              # Remove is_active from all schemas
│
├── api/routes/                      # [MODIFIED] Update endpoint logic
│   ├── users.py                     # Remove is_active filtering from list endpoints
│   ├── accounts.py                  # Remove is_active filtering from list endpoints
│   ├── financial_institutions.py    # Remove is_active filtering from list endpoints
│   ├── account_types.py             # Remove is_active filtering from list endpoints
│   └── auth.py                      # Update authentication checks
│
└── api/dependencies.py              # [MODIFIED] Update get_current_user logic

alembic/versions/
└── [NEW]_remove_is_active_fields.py  # Migration to remove is_active columns

tests/                               # [MODIFIED] Update all test assertions
├── conftest.py                      # Update fixtures (remove is_active)
├── unit/
│   ├── services/                    # Update service tests
│   └── repositories/                # Update repository tests
├── integration/                     # Update API tests
└── e2e/                            # Update end-to-end tests
```

---

## Implementation Specification

### 3.1 Component Breakdown

#### Component 1: Model Layer Refactoring

**Files Involved**:
- `src/models/user.py`
- `src/models/account.py`
- `src/models/card.py` (verify - likely no changes needed)
- `src/models/transaction.py` (verify - likely no changes needed)
- `src/models/financial_institution.py`
- `src/models/account_type.py`

**Purpose**: Remove `is_active` field from all models and ensure proper soft delete implementation

**Implementation Requirements**:

1. **User Model** (`src/models/user.py:90-95`):
   ```python
   # REMOVE these lines:
   is_active: Mapped[bool] = mapped_column(
       Boolean,
       nullable=False,
       default=True,
       index=True,
   )
   ```
   - Already has `SoftDeleteMixin` (line 31) ✓
   - Authentication logic must check `deleted_at IS NULL` instead of `is_active=True`

2. **Account Model** (`src/models/account.py:177-181`):
   ```python
   # REMOVE these lines:
   is_active: Mapped[bool] = mapped_column(
       nullable=False,
       default=True,
       index=True,
   )
   ```
   - Already has `SoftDeleteMixin` (line 45) ✓
   - Replace "inactive accounts" concept with "deleted accounts"

3. **Card Model** (`src/models/card.py`):
   - Already has `SoftDeleteMixin` (line 36) ✓
   - Does NOT have `is_active` field ✓
   - **No changes needed** - verify only

4. **Transaction Model** (`src/models/transaction.py`):
   - Already has `SoftDeleteMixin` (line 58) ✓
   - Does NOT have `is_active` field ✓
   - **No changes needed** - verify only

5. **FinancialInstitution Model** (`src/models/financial_institution.py:24,132-138`):
   ```python
   # ADD SoftDeleteMixin to class inheritance (line 24):
   class FinancialInstitution(Base, TimestampMixin, SoftDeleteMixin):

   # REMOVE these lines (line 132-138):
   is_active: Mapped[bool] = mapped_column(
       Boolean,
       nullable=False,
       default=True,
       index=True,
       comment="Whether the institution is operational",
   )
   ```
   - Currently uses `is_active` for deactivation
   - Migrate to `deleted_at` pattern for consistency
   - Update docstring (line 63-65) to reflect soft delete instead of `is_active`

6. **AccountType Model** (`src/models/account_type.py:97-102`):
   ```python
   # REMOVE these lines:
   is_active: Mapped[bool] = mapped_column(
       Boolean,
       nullable=False,
       default=True,
       index=True,
       comment="Whether the type is available for selection",
   )
   ```
   - Does NOT have `SoftDeleteMixin` (line 23) ✓
   - Will use hard delete only (no replacement needed)
   - Update docstring (line 60-64) to remove mention of `is_active`

**Data Handling**:

- **User**: Active users have `deleted_at IS NULL`. Deleted users have `deleted_at` set.
- **Account**: Active accounts have `deleted_at IS NULL`. Deleted accounts have `deleted_at` set.
- **FinancialInstitution**: Active institutions have `deleted_at IS NULL`. Defunct institutions have `deleted_at` set.
- **AccountType**: Types that should be removed are hard-deleted (row removed from DB).

**Edge Cases & Error Handling**:

- [ ] Handle case: User with `is_active=False` during migration → migrate to `deleted_at=NOW()`
- [ ] Handle case: Account with `is_active=False` during migration → migrate to `deleted_at=NOW()`
- [ ] Handle case: FinancialInstitution with `is_active=False` during migration → migrate to `deleted_at=NOW()`
- [ ] Handle case: AccountType with `is_active=False` during migration → **HARD DELETE** (master data cleanup)
- [ ] Validate: All foreign key relationships remain intact after migration
- [ ] Validate: Unique constraints still work with `deleted_at` (partial unique indexes)

**Dependencies**:
- Internal: `SoftDeleteMixin` from `src/models/mixins.py`
- External: SQLAlchemy 2.0, PostgreSQL 16+

**Testing Requirements**:

- [ ] Unit test: User with `deleted_at=NULL` is considered active
- [ ] Unit test: User with `deleted_at` set is considered deleted
- [ ] Unit test: Account soft delete works correctly via `BaseRepository.soft_delete()`
- [ ] Unit test: FinancialInstitution soft delete works correctly
- [ ] Unit test: AccountType hard delete removes row completely
- [ ] Integration test: Soft-deleted users cannot authenticate
- [ ] Integration test: Soft-deleted accounts are excluded from listing
- [ ] Integration test: Foreign key constraints work with soft-deleted entities

**Acceptance Criteria**:
- [ ] No model has an `is_active` field
- [ ] Five models (User, Account, Card, Transaction, FinancialInstitution) have `deleted_at` via `SoftDeleteMixin`
- [ ] All other models use hard delete (no `SoftDeleteMixin`)
- [ ] Model docstrings accurately reflect the new pattern
- [ ] All model files pass mypy type checking

**Implementation Notes**:
- Be careful with FinancialInstitution - it's referenced by Account and Card with `ondelete="RESTRICT"` (Account) and `ondelete="SET NULL"` (Card). Soft delete is appropriate here to preserve references.
- AccountType is referenced by Account with `ondelete="RESTRICT"`. Since we're removing soft delete from AccountType, ensure no active accounts reference deleted types before hard deletion.

---

#### Component 2: Repository Layer Updates

**Files Involved**:
- `src/repositories/base.py` (verify - likely no changes)
- `src/repositories/user_repository.py`
- `src/repositories/account_repository.py`
- `src/repositories/financial_institution_repository.py`
- `src/repositories/account_type_repository.py`

**Purpose**: Remove `is_active` filtering logic and rely on `BaseRepository._apply_soft_delete_filter()`

**Implementation Requirements**:

1. **BaseRepository** (`src/repositories/base.py`):
   - **Verify** `_apply_soft_delete_filter()` (line 54-66) is correct ✓
   - Already automatically filters `deleted_at IS NULL` for models with `deleted_at` ✓
   - **No changes needed** - already implements correct pattern

2. **UserRepository** (`src/repositories/user_repository.py`):
   - Search for `is_active` filtering in custom methods
   - Remove any `where(User.is_active == True)` filters
   - Rely on `_apply_soft_delete_filter()` from base class
   - Update `get_by_email()`, `get_by_username()` if they filter by `is_active`

3. **AccountRepository** (`src/repositories/account_repository.py`):
   - Remove `is_active` filtering from custom query methods
   - Check methods like `get_user_accounts()`, `get_active_accounts()`
   - Update filter parameters - remove `is_active` from method signatures if present
   - Filtering for "active accounts" = filtering for `deleted_at IS NULL` (automatic)

4. **FinancialInstitutionRepository** (`src/repositories/financial_institution_repository.py`):
   - Remove `is_active` filtering from list/search methods
   - After adding `SoftDeleteMixin` to model, base class will handle filtering
   - Search methods should no longer filter by `is_active`

5. **AccountTypeRepository** (`src/repositories/account_type_repository.py`):
   - Remove `is_active` filtering entirely
   - AccountType uses hard delete - no soft delete filtering needed
   - Methods like `get_active_types()` should be removed or renamed to `get_all_types()`

**Data Handling**:

- **Input**: All repository methods that previously accepted `is_active` parameter
- **Output**: Remove `is_active` parameters from method signatures
- **Filtering**: Rely on `BaseRepository._apply_soft_delete_filter()` for models with `deleted_at`

**Edge Cases & Error Handling**:

- [ ] Handle case: Query for "all users including deleted" → use `include_deleted` pattern if needed
- [ ] Handle case: Repository method needs to bypass soft delete filter → add explicit `include_deleted=True` parameter
- [ ] Validate: All existing queries return same results (active entities only)
- [ ] Error: Method tries to filter by non-existent `is_active` → compilation error (good!)

**Dependencies**:
- Internal: `BaseRepository` class, updated models
- External: SQLAlchemy 2.0 async

**Testing Requirements**:

- [ ] Unit test: UserRepository queries only return users with `deleted_at IS NULL`
- [ ] Unit test: AccountRepository queries only return accounts with `deleted_at IS NULL`
- [ ] Unit test: Soft-deleted entities excluded from `get_all()` by default
- [ ] Unit test: `count()` method excludes soft-deleted by default
- [ ] Unit test: `count(include_deleted=True)` includes soft-deleted
- [ ] Integration test: Repository filtering works end-to-end with database

**Acceptance Criteria**:
- [ ] No repository method filters by `is_active`
- [ ] All soft delete models rely on `_apply_soft_delete_filter()` from base class
- [ ] Hard delete models have no soft delete filtering
- [ ] Repository tests pass with updated assertions

**Implementation Notes**:
- The `BaseRepository` already has the correct implementation. Most work is **removing** code, not adding it.
- Check for any custom WHERE clauses that reference `is_active` - these need to be removed.

---

#### Component 3: Service Layer Business Logic

**Files Involved**:
- `src/services/user_service.py`
- `src/services/account_service.py`
- `src/services/card_service.py`
- `src/services/financial_institution_service.py`
- `src/services/account_type_service.py`
- `src/services/auth_service.py`

**Purpose**: Remove all `is_active` references from business logic. Services should NEVER check entity status.

**Implementation Requirements**:

1. **Core Architecture Principle**:
   ```python
   # WRONG - Service checks entity status:
   user = await user_repo.get_by_id(user_id)
   if not user.is_active:  # ❌ NEVER DO THIS
       raise InactiveUserError("User account is inactive")

   # WRONG - Service checks deleted_at:
   user = await user_repo.get_by_id(user_id)
   if user.deleted_at is not None:  # ❌ NEVER DO THIS EITHER
       raise DeletedUserError("User account has been deleted")

   # CORRECT - Trust repository filtering:
   user = await user_repo.get_by_id(user_id)
   if user is None:  # ✓ Repository returns None for deleted/non-existent
       raise NotFoundError("User")
   # If we reach here, user is guaranteed to be active

   # Key insight: Repository layer is the ONLY layer that knows about deleted_at
   # Service layer treats "deleted" and "non-existent" as equivalent: both = None
   ```

2. **AuthService** (`src/services/auth_service.py`):
   - Remove ALL references to `is_active` or `deleted_at`
   - `authenticate_user()`: Repository's `get_by_email()` automatically excludes deleted users
   - If `get_by_email()` returns `None`, authentication fails (user not found OR deleted - equivalent)
   - No explicit status checks needed - repository handles it
   - **Critical**: Password validation should only happen AFTER confirming user exists (repository returned non-None)

3. **UserService** (`src/services/user_service.py`):
   - Remove methods: `activate_user()`, `deactivate_user()` if present
   - Keep/add: `soft_delete_user()` (calls `repository.soft_delete()`)
   - Remove ALL `is_active` filtering - repository does this automatically
   - Remove ALL `deleted_at` checks - repository handles this
   - List methods: No filtering parameters needed, repository returns only active users

4. **AccountService** (`src/services/account_service.py`):
   - Remove methods: `activate_account()`, `deactivate_account()` if present
   - Update docstrings: "Inactive accounts" → "Deleted accounts"
   - Remove `is_active` parameters from method signatures
   - Remove ALL `deleted_at` checks - trust repository
   - If account lookup returns `None`, entity not found (deleted OR never existed)

5. **CardService** (`src/services/card_service.py`):
   - **Verify** - likely already correct since Card model has no `is_active`
   - Remove any validation checking parent account's `is_active`
   - No need to check `account.deleted_at` - if repository returned the account, it's active

6. **FinancialInstitutionService** (`src/services/financial_institution_service.py`):
   - Remove methods: `activate_institution()`, `deactivate_institution()` if present
   - Keep/add: `soft_delete_institution()` (calls `repository.soft_delete()`)
   - Remove ALL `is_active` filtering
   - Remove ALL `deleted_at` checks
   - Repository automatically returns only non-deleted institutions

7. **AccountTypeService** (`src/services/account_type_service.py`):
   - Remove methods: `activate_type()`, `deactivate_type()` entirely
   - Keep/add: `delete_type()` for hard delete (calls `repository.delete()`)
   - Remove `list_active_types()` - just use `list_types()` (no filtering needed)
   - Validation before delete: Check no accounts reference this type (FK constraint will enforce this too)

**Data Handling**:

- **Input validation**: Methods that accepted `is_active` parameter should remove it
- **Output formatting**: Remove `is_active` from service return values
- **State transitions**: "Activate/Deactivate" → "Delete/Restore" (if restore needed)

**Edge Cases & Error Handling**:

- [ ] Handle case: Attempt to delete already-deleted entity → Repository returns None, treat as NotFoundError
- [ ] Handle case: Attempt to restore deleted entity → new `restore()` method if needed (requires bypassing repository filter)
- [ ] Handle case: Delete entity with active foreign key references → RESTRICT constraint handles (database level)
- [ ] Handle case: User tries to access deleted entity → Repository returns None, service raises NotFoundError
- [ ] Validate: Authentication fails for deleted users (repository filter prevents lookup)
- [ ] Validate: Services never check `is_active` or `deleted_at` - rely on repository filtering exclusively

**Dependencies**:
- Internal: Updated repositories, updated models
- External: FastAPI dependencies, Pydantic validation

**Testing Requirements**:

- [ ] Unit test: Authentication fails for deleted user (repository returns None)
- [ ] Unit test: Soft delete sets `deleted_at` timestamp correctly (test repository, not service)
- [ ] Unit test: Service methods receive only active entities from repository
- [ ] Unit test: Service raises NotFoundError when repository returns None
- [ ] Unit test: Hard delete (AccountType) removes row completely
- [ ] Unit test: Services never check entity status - no `is_active` or `deleted_at` checks
- [ ] Integration test: Deleted user cannot login (repository filter prevents lookup)
- [ ] E2E test: Full entity lifecycle without status checks in service layer

**Acceptance Criteria**:
- [ ] No service method references `is_active`
- [ ] No service method checks `deleted_at` - repository handles all filtering
- [ ] Services treat repository returning None as "not found" (don't distinguish deleted vs non-existent)
- [ ] Error messages updated: no "inactive" terminology
- [ ] Service layer tests pass with updated logic

**Implementation Notes**:
- Authentication flow is automatically secure - repository won't return deleted users to services.
- If "restore deleted entity" functionality needed, requires special repository method that bypasses soft delete filter.
- For AccountType hard delete, FK constraints prevent deleting types in use (database-level enforcement).

---

#### Component 4: API Schema Updates

**Files Involved**:
- `src/schemas/user.py`
- `src/schemas/account.py`
- `src/schemas/financial_institution.py`
- `src/schemas/account_type.py`

**Purpose**: Remove `is_active` fields from all Pydantic request/response schemas

**Implementation Requirements**:

1. **UserSchema** (`src/schemas/user.py`):
   ```python
   # REMOVE from UserResponse (line 166):
   is_active: bool = Field(description="Whether user account is active")

   # REMOVE from UserListItem (line 195):
   is_active: bool = Field(description="Whether user account is active")

   # REMOVE from UserFilterParams (line 211):
   is_active: bool | None = Field(default=None, description="Filter by active status")
   ```
   - Update docstrings to remove references to "active/inactive"
   - Filter params: Remove `is_active` from filter schemas

2. **AccountSchema** (`src/schemas/account.py`):
   ```python
   # REMOVE from AccountUpdate (line 222-224):
   is_active: bool | None = Field(
       default=None,
       description="Active status (inactive accounts hidden by default)",
   )

   # REMOVE from AccountResponse (line 358-360):
   is_active: bool = Field(
       description="Whether account is active (inactive accounts hidden by default)"
   )

   # REMOVE from AccountListItem (line 403):
   is_active: bool

   # REMOVE from AccountFilterParams (line 425-427):
   is_active: bool | None = Field(
       default=None,
       description="Filter by active status (true=active, false=inactive, null=all)",
   )
   ```
   - Update related docstrings in `AccountCreate`, `AccountUpdate`
   - Remove "inactive accounts" language from comments

3. **FinancialInstitutionSchema** (`src/schemas/financial_institution.py`):
   ```python
   # REMOVE from FinancialInstitutionCreate (line 89-91):
   is_active: bool = Field(
       default=True,
       description="Whether the institution is operational",
   )

   # REMOVE from FinancialInstitutionUpdate (line 264-266):
   is_active: bool | None = Field(
       default=None,
       description="Whether the institution is operational",
   )

   # REMOVE from FinancialInstitutionListItem (line 367):
   is_active: bool = Field(description="Active status")

   # REMOVE from FinancialInstitutionFilterParams (line 395-397):
   is_active: bool | None = Field(
       default=True,
       description="Filter by active status (default: True - active only)",
   )
   ```

4. **AccountTypeSchema** (`src/schemas/account_type.py`):
   ```python
   # REMOVE from AccountTypeCreate (line 60-62):
   is_active: bool = Field(
       default=True,
       description="Whether the type is available for selection",
   )

   # REMOVE from AccountTypeUpdate (line 189-191):
   is_active: bool | None = Field(
       default=None,
       description="Whether the type is available for selection",
   )

   # REMOVE from AccountTypeListItem (line 253):
   is_active: bool = Field(description="Active status")
   ```

**Data Handling**:

- **API Request Bodies**: Remove `is_active` from all create/update schemas
- **API Response Bodies**: Remove `is_active` from all response schemas
- **API Query Parameters**: Remove `is_active` from all filter parameter schemas
- **Validation**: Remove Pydantic validators that reference `is_active`

**Edge Cases & Error Handling**:

- [ ] Handle case: API client sends `is_active` in request → Pydantic ignores extra field (no error if `extra="ignore"`)
- [ ] Handle case: API client expects `is_active` in response → Breaking change, document in changelog
- [ ] Validate: All schema examples in docstrings updated
- [ ] Validate: OpenAPI spec (Swagger docs) reflects changes

**Dependencies**:
- Internal: Updated models, updated services
- External: Pydantic v2, FastAPI

**Testing Requirements**:

- [ ] Unit test: Schemas do not have `is_active` fields
- [ ] Unit test: Schema validation passes without `is_active`
- [ ] Unit test: Old requests with `is_active` are handled gracefully (ignored)
- [ ] Integration test: API endpoints return correct responses without `is_active`
- [ ] Integration test: Filter endpoints work without `is_active` parameter

**Acceptance Criteria**:
- [ ] No Pydantic schema has `is_active` field
- [ ] All API documentation (docstrings) updated
- [ ] Schema validation tests pass
- [ ] OpenAPI spec does not include `is_active` in any endpoint

**Implementation Notes**:
- This is a **breaking API change**. Clients expecting `is_active` in responses will need updates.
- Consider API versioning if backward compatibility is required (unlikely for internal project).
- Update API documentation to explain the change: "Entity status is now derived from existence (deleted entities are not returned)."

---

#### Component 5: API Route/Endpoint Updates

**Files Involved**:
- `src/api/routes/users.py`
- `src/api/routes/accounts.py`
- `src/api/routes/financial_institutions.py`
- `src/api/routes/account_types.py`
- `src/api/routes/auth.py`
- `src/api/dependencies.py`

**Purpose**: Update endpoint logic to work without `is_active` field

**Implementation Requirements**:

1. **Authentication Endpoints** (`src/api/routes/auth.py`):
   - Login endpoint: Relies on `AuthService.authenticate_user()`
   - Ensure authentication fails for deleted users (service layer handles this)
   - Update error messages: "Inactive user" → "User account deleted"

2. **User Management Endpoints** (`src/api/routes/users.py`):
   - `GET /users` (list): Remove `is_active` from query parameters
   - `GET /users/{id}`: No changes (deleted users automatically excluded)
   - `PATCH /users/{id}`: Remove `is_active` from updateable fields
   - Remove any "activate/deactivate" endpoints if they exist
   - Consider adding: `DELETE /users/{id}` (soft delete) if not present

3. **Account Endpoints** (`src/api/routes/accounts.py`):
   - `GET /accounts` (list): Remove `is_active` filter parameter
   - `POST /accounts`: Remove `is_active` from request body (default to active = `deleted_at=NULL`)
   - `PATCH /accounts/{id}`: Remove `is_active` from updateable fields
   - `DELETE /accounts/{id}`: Should call `service.soft_delete_account()` (soft delete)

4. **Financial Institution Endpoints** (`src/api/routes/financial_institutions.py`):
   - `GET /institutions` (list): Remove `is_active` filter parameter
   - `POST /institutions`: Remove `is_active` from request body
   - `PATCH /institutions/{id}`: Remove `is_active` from updateable fields
   - `DELETE /institutions/{id}`: Should call `service.soft_delete_institution()` (soft delete)

5. **Account Type Endpoints** (`src/api/routes/account_types.py`):
   - `GET /account-types` (list): Remove `is_active` filter parameter
   - `POST /account-types`: Remove `is_active` from request body
   - `PATCH /account-types/{id}`: Remove `is_active` from updateable fields
   - `DELETE /account-types/{id}`: Hard delete (permanent removal)
   - Add validation: Prevent deletion if accounts reference this type

6. **Dependencies** (`src/api/dependencies.py`):
   - `get_current_user()`: Ensure deleted users are not returned
   - Repository call already filters by `deleted_at` automatically
   - Update error handling if needed

**Data Handling**:

- **Request handling**: Remove `is_active` from all request body processing
- **Response formatting**: Remove `is_active` from all response bodies (handled by schemas)
- **Query parameter filtering**: Remove `is_active` from filter parameters

**Edge Cases & Error Handling**:

- [ ] Handle case: Client sends `is_active` in request body → Ignored (Pydantic validation)
- [ ] Handle case: Client tries to access deleted entity by ID → 404 Not Found
- [ ] Handle case: Client tries to delete AccountType in use → 400 Bad Request with validation message
- [ ] Handle case: Client expects `is_active` in response → Breaking change, document
- [ ] Error: Soft delete fails → 500 Internal Server Error with proper logging

**Dependencies**:
- Internal: Updated services, updated schemas
- External: FastAPI, Pydantic

**Testing Requirements**:

- [ ] Integration test: List endpoints do not accept `is_active` filter
- [ ] Integration test: Create endpoints do not accept `is_active` in body
- [ ] Integration test: Update endpoints do not accept `is_active` in body
- [ ] Integration test: Deleted entities return 404 on GET by ID
- [ ] Integration test: Soft delete endpoint sets `deleted_at` correctly
- [ ] Integration test: Hard delete (AccountType) removes entity completely
- [ ] Integration test: Authentication fails for deleted user
- [ ] E2E test: Full entity lifecycle without `is_active` field

**Acceptance Criteria**:
- [ ] No endpoint accepts `is_active` in request
- [ ] No endpoint returns `is_active` in response
- [ ] Deleted entities properly excluded from list endpoints
- [ ] Delete endpoints work correctly (soft delete vs hard delete)
- [ ] All integration tests pass

**Implementation Notes**:
- Carefully test authentication flow - this is critical for security.
- Document API changes in changelog/release notes.
- Consider rate limiting for delete operations to prevent abuse.

---

#### Component 6: Database Migration

**Files Involved**:
- `alembic/versions/[NEW]_remove_is_active_fields.py` (to be created)

**Purpose**: Remove `is_active` columns from database and migrate data to `deleted_at` pattern

**Implementation Requirements**:

1. **Migration File Structure**:
   ```python
   """remove is_active fields

   Revision ID: [generated]
   Revises: 2daac3b155e4
   Create Date: [generated]
   """

   # This migration:
   # 1. Adds deleted_at to financial_institutions (via SoftDeleteMixin)
   # 2. Migrates is_active=False → deleted_at=NOW() for relevant models
   # 3. Drops is_active columns
   # 4. Drops indexes on is_active
   ```

2. **Step 1: Add `deleted_at` to FinancialInstitution**:
   ```python
   # Add column (nullable initially for migration)
   op.add_column('financial_institutions',
       sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
   )

   # Add index on deleted_at
   op.create_index(
       'ix_financial_institutions_deleted_at',
       'financial_institutions',
       ['deleted_at']
   )
   ```

3. **Step 2: Migrate `is_active=False` to `deleted_at`**:
   ```python
   # Users: is_active=False → deleted_at=NOW()
   op.execute("""
       UPDATE users
       SET deleted_at = NOW()
       WHERE is_active = FALSE
       AND deleted_at IS NULL
   """)

   # Accounts: is_active=False → deleted_at=NOW()
   op.execute("""
       UPDATE accounts
       SET deleted_at = NOW()
       WHERE is_active = FALSE
       AND deleted_at IS NULL
   """)

   # FinancialInstitutions: is_active=False → deleted_at=NOW()
   op.execute("""
       UPDATE financial_institutions
       SET deleted_at = NOW()
       WHERE is_active = FALSE
   """)

   # AccountTypes: is_active=False → HARD DELETE
   op.execute("""
       DELETE FROM account_types
       WHERE is_active = FALSE
   """)
   ```

4. **Step 3: Drop `is_active` columns**:
   ```python
   # Drop indexes first
   op.drop_index('ix_users_is_active', table_name='users')
   op.drop_index('ix_accounts_is_active', table_name='accounts')
   op.drop_index('ix_financial_institutions_is_active', table_name='financial_institutions')
   op.drop_index('ix_account_types_is_active', table_name='account_types')

   # Drop columns
   op.drop_column('users', 'is_active')
   op.drop_column('accounts', 'is_active')
   op.drop_column('financial_institutions', 'is_active')
   op.drop_column('account_types', 'is_active')
   ```

5. **Step 4: Downgrade (Rollback)**:
   ```python
   def downgrade() -> None:
       # Re-add is_active columns
       op.add_column('users',
           sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
       )
       # ... (repeat for all models)

       # Recreate indexes
       op.create_index('ix_users_is_active', 'users', ['is_active'])
       # ... (repeat for all models)

       # Migrate data back: deleted_at IS NOT NULL → is_active=False
       op.execute("""
           UPDATE users
           SET is_active = FALSE
           WHERE deleted_at IS NOT NULL
       """)
       # ... (repeat for all models)

       # Drop deleted_at from financial_institutions
       op.drop_index('ix_financial_institutions_deleted_at', table_name='financial_institutions')
       op.drop_column('financial_institutions', 'deleted_at')
   ```

**Data Handling**:

- **Data migration**: Preserve all existing data
- **NULL handling**: `is_active=NULL` should not exist (column is NOT NULL), but handle defensively
- **Timestamp**: Use `NOW()` for `deleted_at` to record migration time
- **Foreign keys**: No impact - columns are on the same tables, not changing relationships

**Edge Cases & Error Handling**:

- [ ] Handle case: User has both `is_active=False` AND `deleted_at` set → Keep existing `deleted_at`, don't overwrite
- [ ] Handle case: Account references inactive AccountType → Migration deletes type, Account now has invalid FK → **RESTRICT constraint prevents this**
- [ ] Handle case: Migration fails mid-way → Alembic transaction rollback handles this
- [ ] Validate: No data loss during migration
- [ ] Validate: All constraints remain valid after migration

**Dependencies**:
- Internal: Updated models (must be deployed before migration runs)
- External: Alembic, PostgreSQL 16+

**Testing Requirements**:

- [ ] Test: Migration applies cleanly on empty database
- [ ] Test: Migration applies cleanly on database with data
- [ ] Test: `is_active=False` users become soft-deleted users
- [ ] Test: `is_active=True` users remain active
- [ ] Test: AccountType with `is_active=False` is hard-deleted
- [ ] Test: Downgrade migration restores original state
- [ ] Test: Foreign key constraints remain intact
- [ ] Test: Indexes are created/dropped correctly

**Acceptance Criteria**:
- [ ] Migration runs without errors
- [ ] All `is_active` columns removed from database
- [ ] FinancialInstitution has `deleted_at` column
- [ ] Data migrated correctly (`is_active=False` → `deleted_at` set)
- [ ] Migration is reversible (downgrade works)
- [ ] No data loss during migration

**Implementation Notes**:
- **Test migration on a copy of production data before deploying!**
- Consider dry-run mode: log what would happen without actually changing data.
- Monitor migration performance - large tables (users, accounts, transactions) may take time.
- Schedule migration during maintenance window if possible.

---

#### Component 7: Test Suite Updates

**Files Involved**:
- `tests/conftest.py` (fixtures)
- `tests/unit/services/test_user_service.py`
- `tests/unit/services/test_account_service.py`
- `tests/unit/services/test_auth_service.py`
- `tests/unit/repositories/test_account_repository.py`
- `tests/integration/test_auth_routes.py`
- `tests/integration/test_account_routes.py`
- `tests/integration/test_account_type_routes.py`
- `tests/integration/test_financial_institution_routes.py`
- All other test files with `is_active` assertions

**Purpose**: Update all tests to work with new `deleted_at` pattern

**Implementation Requirements**:

1. **Test Fixtures** (`tests/conftest.py`):
   ```python
   # UPDATE all user/account/institution fixtures:
   # REMOVE:
   is_active=True

   # Ensure deleted_at=None is default (or just omit, it's the default)
   ```

2. **Unit Tests - User Service**:
   ```python
   # OLD:
   async def test_deactivate_user():
       user = await user_service.deactivate_user(user_id)
       assert user.is_active == False

   # NEW:
   async def test_soft_delete_user():
       user = await user_service.soft_delete_user(user_id)
       assert user.deleted_at is not None
   ```

3. **Unit Tests - Authentication**:
   ```python
   # OLD:
   async def test_inactive_user_cannot_login():
       user.is_active = False
       with pytest.raises(InactiveUserError):
           await auth_service.authenticate(...)

   # NEW - Service layer doesn't check status:
   async def test_deleted_user_cannot_login():
       # Soft delete user (sets deleted_at)
       await user_repo.soft_delete(user)

       # Repository won't return deleted user
       # authenticate() gets None from repository, raises NotFoundError
       with pytest.raises(NotFoundError):  # or InvalidCredentialsError
           await auth_service.authenticate(email, password)

       # Key: Service doesn't check deleted_at - repository filter handles it
   ```

4. **Integration Tests - API Routes**:
   ```python
   # OLD:
   response = await client.get("/accounts?is_active=true")

   # NEW:
   response = await client.get("/accounts")  # Only active by default

   # OLD assertion:
   assert account["is_active"] == True

   # NEW assertion:
   # is_active not in response anymore
   assert "is_active" not in account
   ```

5. **Repository Tests**:
   ```python
   # Test soft delete filtering
   async def test_get_all_excludes_deleted():
       # Create user
       user = await user_repo.create(username="test", ...)

       # Soft delete
       await user_repo.soft_delete(user)

       # Query all
       users = await user_repo.get_all()

       # Assert deleted user not in results
       assert user.id not in [u.id for u in users]
   ```

**Data Handling**:

- **Test data setup**: All fixtures create entities with `deleted_at=NULL` (active)
- **Soft delete testing**: Set `deleted_at` to test deleted entity behavior
- **Assertions**: Check `deleted_at` instead of `is_active`

**Edge Cases & Error Handling**:

- [ ] Test: Soft-deleted entity excluded from queries
- [ ] Test: Soft-deleted entity can be retrieved if explicitly included
- [ ] Test: Hard-deleted entity (AccountType) not found at all
- [ ] Test: Authentication fails for soft-deleted user
- [ ] Test: Foreign key constraints work with soft-deleted entities
- [ ] Test: Count method excludes/includes deleted based on parameter

**Dependencies**:
- Internal: All updated components (models, services, repositories, routes)
- External: pytest, pytest-asyncio, httpx

**Testing Requirements**:

This component IS the testing - meta-requirement is that all tests pass!

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Test coverage remains ≥80%
- [ ] No tests reference `is_active`

**Acceptance Criteria**:
- [ ] Zero test failures
- [ ] Zero references to `is_active` in test code
- [ ] All soft delete behavior tested
- [ ] All hard delete behavior tested (AccountType)
- [ ] Coverage report shows ≥80% coverage

**Implementation Notes**:
- Run tests frequently during refactoring to catch regressions early.
- Use `pytest -x` (stop on first failure) to debug issues quickly.
- Consider running tests in parallel with `pytest -n auto` for speed.

---

## Implementation Roadmap

### 4.1 Phase Breakdown

Given the scope of this refactoring, a **single-phase approach** is most appropriate. This refactoring is tightly coupled - changes to models must be accompanied by changes to repositories, services, and APIs simultaneously. Breaking it into multiple phases would leave the codebase in an inconsistent state.

#### Phase 1: Complete Soft Delete Refactoring (Size: L, Priority: P0)

**Goal**: Remove all `is_active` fields and establish consistent soft delete pattern across the entire codebase

**Scope**:
- ✅ Include: All model updates, repository updates, service updates, schema updates, API updates, database migration, test updates
- ❌ Exclude: Any new features, performance optimizations unrelated to this refactoring

**Components to Implement**:
- [x] Component 1: Model layer refactoring
- [x] Component 2: Repository layer updates
- [x] Component 3: Service layer business logic
- [x] Component 4: API schema updates
- [x] Component 5: API route/endpoint updates
- [x] Component 6: Database migration
- [x] Component 7: Test suite updates

**Detailed Tasks**:

**Step 1: Update Models** (Foundation)
1. [ ] Remove `is_active` from `User` model (line 90-95)
2. [ ] Remove `is_active` from `Account` model (line 177-181)
3. [ ] Add `SoftDeleteMixin` to `FinancialInstitution` model (line 24)
4. [ ] Remove `is_active` from `FinancialInstitution` model (line 132-138)
5. [ ] Remove `is_active` from `AccountType` model (line 97-102)
6. [ ] Update model docstrings to reflect changes
7. [ ] Run mypy type checking: `uv run mypy src/models/`

**Step 2: Update Schemas** (API Contract)
8. [ ] Remove `is_active` from all User schemas (`src/schemas/user.py`)
9. [ ] Remove `is_active` from all Account schemas (`src/schemas/account.py`)
10. [ ] Remove `is_active` from all FinancialInstitution schemas (`src/schemas/financial_institution.py`)
11. [ ] Remove `is_active` from all AccountType schemas (`src/schemas/account_type.py`)
12. [ ] Update schema docstrings and examples
13. [ ] Run mypy type checking: `uv run mypy src/schemas/`

**Step 3: Update Repositories** (Data Access)
14. [ ] Search for `is_active` references: `grep -r "is_active" src/repositories/`
15. [ ] Remove `is_active` filters from `UserRepository`
16. [ ] Remove `is_active` filters from `AccountRepository`
17. [ ] Remove `is_active` filters from `FinancialInstitutionRepository`
18. [ ] Remove `is_active` filters from `AccountTypeRepository`
19. [ ] Verify `BaseRepository` is unchanged (correct pattern already)
20. [ ] Run mypy type checking: `uv run mypy src/repositories/`

**Step 4: Update Services** (Business Logic)
21. [ ] Update `AuthService` - remove ALL `is_active` checks, trust repository filtering
22. [ ] Update `UserService` - remove activate/deactivate methods, ensure no `deleted_at` checks
23. [ ] Update `AccountService` - remove activate/deactivate logic, no status checks
24. [ ] Update `CardService` - remove any `is_active` checks, trust repository
25. [ ] Update `FinancialInstitutionService` - remove activate/deactivate, no status checks
26. [ ] Update `AccountTypeService` - use hard delete, add FK validation
27. [ ] Verify NO service checks `is_active` or `deleted_at`: `grep -r "deleted_at" src/services/` should only find soft_delete() calls
28. [ ] Search for remaining `is_active`: `grep -r "is_active" src/services/` should return nothing
29. [ ] Run mypy type checking: `uv run mypy src/services/`

**Step 5: Update API Routes** (Endpoints)
30. [ ] Update `auth.py` - remove `is_active` references
31. [ ] Update `users.py` - remove `is_active` from endpoints
32. [ ] Update `accounts.py` - remove `is_active` from endpoints
33. [ ] Update `financial_institutions.py` - remove `is_active` from endpoints
34. [ ] Update `account_types.py` - remove `is_active`, add delete validation
35. [ ] Update `dependencies.py` - verify `get_current_user()` works correctly (should already be correct)
36. [ ] Search for remaining `is_active` references: `grep -r "is_active" src/api/`
37. [ ] Run mypy type checking: `uv run mypy src/api/`

**Step 6: Create Database Migration**
38. [ ] Generate migration: `uv run alembic revision -m "remove is_active fields"`
39. [ ] Implement upgrade: Add `deleted_at` to FinancialInstitution
40. [ ] Implement upgrade: Migrate `is_active=False` → `deleted_at=NOW()`
41. [ ] Implement upgrade: Drop `is_active` columns and indexes
42. [ ] Implement downgrade: Reverse all changes (for rollback)
43. [ ] Test migration on clean database: `dropdb test_db && createdb test_db && uv run alembic upgrade head`
44. [ ] Test migration on database with data (use test fixtures)
45. [ ] Test downgrade: `uv run alembic downgrade -1`

**Step 7: Update Tests**
46. [ ] Update `conftest.py` fixtures - remove `is_active` from test data
47. [ ] Update unit tests: `tests/unit/services/test_auth_service.py` - no deleted_at checks
48. [ ] Update unit tests: `tests/unit/services/test_user_service.py` - verify no status checks
49. [ ] Update unit tests: `tests/unit/services/test_account_service.py` - verify no status checks
50. [ ] Update unit tests: `tests/unit/repositories/test_account_repository.py`
51. [ ] Update integration tests: `tests/integration/test_auth_routes.py`
52. [ ] Update integration tests: `tests/integration/test_account_routes.py`
53. [ ] Update integration tests: `tests/integration/test_account_type_routes.py`
54. [ ] Update integration tests: `tests/integration/test_financial_institution_routes.py`
55. [ ] Search for remaining `is_active` in tests: `grep -r "is_active" tests/`
56. [ ] Run full test suite: `uv run pytest tests/ -v`
57. [ ] Run test coverage: `uv run pytest tests/ --cov=src --cov-report=term-missing`

**Step 8: Code Quality & Verification**
58. [ ] Run Ruff format: `uv run ruff format .`
59. [ ] Run Ruff lint: `uv run ruff check --fix .`
60. [ ] Run MyPy: `uv run mypy src/`
61. [ ] Final grep check: `grep -r "is_active" src/` (should return no results)
62. [ ] Final grep check: `grep -r "is_active" tests/` (should return no results)
63. [ ] Verify no service checks deleted_at: `grep -r "deleted_at" src/services/` (should only show soft_delete() method calls)

**Dependencies**:
- Requires: Development environment set up, database running
- Blocks: None (this is a foundational refactoring)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass (minimum 80% coverage for new code)
- [ ] Zero references to `is_active` in `src/` directory
- [ ] Zero references to `is_active` in `tests/` directory
- [ ] Database migration runs successfully on test database
- [ ] All code quality checks pass (Ruff, MyPy)
- [ ] Code reviewed and approved
- [ ] Documentation updated (if any external docs reference `is_active`)

**Risk Factors**:
- **Risk**: Migration fails on production data with edge cases not covered in tests
  - **Mitigation**: Test migration on copy of production data before deploying
  - **Mitigation**: Create database backup before running migration
  - **Mitigation**: Schedule migration during maintenance window

- **Risk**: Breaking API change impacts API clients
  - **Mitigation**: This appears to be an internal project (no external clients mentioned)
  - **Mitigation**: Document API changes in changelog
  - **Mitigation**: If external clients exist, consider API versioning

- **Risk**: Tests pass but subtle bugs in production
  - **Mitigation**: High test coverage (80%+)
  - **Mitigation**: Manual testing of critical flows (authentication, account management)
  - **Mitigation**: Staged rollout (test env → staging → production)

**Estimated Effort**: 2-3 days for 1 experienced developer

**Breakdown**:
- Day 1: Steps 1-6 (Models, Schemas, Repositories, Services, Routes, Migration)
- Day 2: Steps 7-8 (Tests, Code Quality, Verification)
- Day 3: Buffer for unexpected issues, code review, documentation

---

### 4.2 Implementation Sequence

```
Single Phase: Complete Refactoring
├── Step 1: Update Models (Foundation)
├── Step 2: Update Schemas (API Contract)
├── Step 3: Update Repositories (Data Access)
├── Step 4: Update Services (Business Logic)
├── Step 5: Update API Routes (Endpoints)
├── Step 6: Create Database Migration
├── Step 7: Update Tests
└── Step 8: Code Quality & Verification
```

**Rationale for ordering**:

1. **Models First**: Foundation of the application. All other layers depend on models.
2. **Schemas Second**: API contract. Services and routes will reference these.
3. **Repositories Third**: Data access layer. Services depend on repositories.
4. **Services Fourth**: Business logic. Routes depend on services.
5. **Routes Fifth**: API endpoints. Final layer that ties everything together.
6. **Migration Sixth**: Database changes. Applied after code is ready.
7. **Tests Seventh**: Validation. Updated after all code changes complete.
8. **Quality Checks Last**: Final verification before commit.

**Why not multiple phases?**

This refactoring is **atomic** - it must be completed in one shot:
- Models and repositories must change together
- Services depend on both models and repositories
- APIs depend on services and schemas
- Tests depend on all layers

Breaking this into phases would leave the codebase in a broken state between phases. For example, if we remove `is_active` from models but leave it in services, services will immediately break.

**Critical Path**: Model changes → Repository changes → Service changes → Migration

All steps depend on previous steps. No parallelization possible for a single developer.

---

## Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. We're removing code, not adding it. Using a single `deleted_at` field is simpler than managing both `is_active` and `deleted_at`.

- [x] **Have we avoided premature optimization?**
  - Yes. No performance optimizations added. Using existing `BaseRepository` filtering mechanism.

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. The `SoftDeleteMixin` and `BaseRepository._apply_soft_delete_filter()` already exist. We're just applying them consistently.

- [x] **Can we deliver value in smaller increments?**
  - No. This refactoring must be atomic. Cannot have some models with `is_active` and others without.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. The problem is real: having both `is_active` and `deleted_at` creates confusion and inconsistency.

### Alternatives Considered

**Alternative 1: Keep both `is_active` and `deleted_at`**
- **Description**: Continue with current approach, use `is_active` for "deactivation" and `deleted_at` for "deletion"
- **Pros**: No breaking changes, no migration needed
- **Cons**:
  - Confusing semantics (what's the difference between deactivated and deleted?)
  - Two fields doing essentially the same thing
  - Duplicate filtering logic in queries
  - More complex state management
- **Why rejected**: Violates DRY principle, creates unnecessary complexity

**Alternative 2: Use `is_active` only, remove `deleted_at`**
- **Description**: Keep `is_active` boolean, remove soft delete pattern entirely
- **Pros**: Simple boolean logic, no timestamps
- **Cons**:
  - Loses when entity was deleted (audit trail)
  - Doesn't support compliance requirements (7-year retention)
  - Boolean doesn't capture deletion semantics as well as timestamp
  - Harder to implement "restore" functionality
- **Why rejected**: Doesn't meet compliance requirements, loses valuable audit information

**Alternative 3: Use a `status` enum (active, inactive, deleted)**
- **Description**: Replace both fields with a single `status` enum
- **Pros**: Clear states, explicit transitions
- **Cons**:
  - More complex than timestamp
  - Still doesn't capture when deletion occurred
  - Requires migration to enum column
  - Adds new concept not currently in codebase
- **Why rejected**: More complex than necessary, doesn't leverage existing patterns

### Rationale for Chosen Approach

The `deleted_at` timestamp pattern is chosen because:

1. **Compliance**: Captures when deletion occurred (required for audit trail)
2. **Simplicity**: Single field, clear semantics (`NULL` = active, timestamp = deleted)
3. **Existing Pattern**: Already used in `SoftDeleteMixin` and supported by `BaseRepository`
4. **Restoration**: Easy to implement "undelete" (set `deleted_at` back to `NULL`)
5. **Queries**: Natural filtering pattern (`WHERE deleted_at IS NULL`)
6. **Industry Standard**: Widely used pattern in production systems

---

## References & Related Documents

### Internal Documentation

- **Project Standards**: `.claude/standards/backend.md` - Backend development standards
- **Database Standards**: `.claude/standards/database.md` - Database schema and migration guidelines
- **API Standards**: `.claude/standards/api.md` - API endpoint design patterns
- **Testing Standards**: `.claude/standards/testing.md` - Test coverage and patterns

### SQLAlchemy Documentation

- [SQLAlchemy 2.0 Async ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Async session management
- [SQLAlchemy Mixins](https://docs.sqlalchemy.org/en/20/orm/declarative_mixins.html) - Model mixins pattern
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) - Database migrations

### Soft Delete Pattern References

- [Soft Delete Best Practices](https://www.postgresql.org/docs/current/ddl-partitioning.html#DDL-PARTITIONING-DECLARATIVE-MAINTENANCE) - PostgreSQL documentation on handling deleted records
- [Audit Trail Design](https://www.pgaudit.org/) - PostgreSQL audit logging patterns
- [GDPR Compliance](https://gdpr.eu/data-retention/) - Data retention requirements

### Testing Resources

- [pytest Documentation](https://docs.pytest.org/) - Testing framework
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Async test support
- [Test Coverage Best Practices](https://coverage.readthedocs.io/) - Coverage measurement

### FastAPI Documentation

- [FastAPI Async Support](https://fastapi.tiangolo.com/async/) - Async endpoint patterns
- [Pydantic V2 Models](https://docs.pydantic.dev/latest/) - Schema validation
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) - Dependency injection

### Related Design Patterns

- **Repository Pattern**: Encapsulation of data access logic
- **Soft Delete Pattern**: Preserving data while marking as deleted
- **Audit Trail Pattern**: Tracking all changes to entities
- **Domain-Driven Design**: Separating domain logic from infrastructure

### Compliance References

- **SOX Compliance**: 7-year retention requirement for financial records
- **GDPR Article 17**: Right to erasure (soft delete supports this)
- **GDPR Article 30**: Records of processing activities (audit trail)

---

## Appendix: Current State Analysis

### Models with `is_active` field

1. **User** (`src/models/user.py:90-95`)
   - Has: `SoftDeleteMixin` ✓
   - Has: `is_active` field ✗
   - Action: Remove `is_active`

2. **Account** (`src/models/account.py:177-181`)
   - Has: `SoftDeleteMixin` ✓
   - Has: `is_active` field ✗
   - Action: Remove `is_active`

3. **Card** (`src/models/card.py:36`)
   - Has: `SoftDeleteMixin` ✓
   - Has: `is_active` field? NO ✓
   - Action: No changes needed

4. **Transaction** (`src/models/transaction.py:58`)
   - Has: `SoftDeleteMixin` ✓
   - Has: `is_active` field? NO ✓
   - Action: No changes needed

5. **FinancialInstitution** (`src/models/financial_institution.py:24,132-138`)
   - Has: `SoftDeleteMixin`? NO ✗
   - Has: `is_active` field ✗
   - Action: Add `SoftDeleteMixin`, remove `is_active`

6. **AccountType** (`src/models/account_type.py:23,97-102`)
   - Has: `SoftDeleteMixin`? NO ✓ (master data, should use hard delete)
   - Has: `is_active` field ✗
   - Action: Remove `is_active`, use hard delete

### Models without soft delete (correct)

- **RefreshToken**: No soft delete, no `is_active` ✓
- **AuditLog**: No soft delete, no `is_active` ✓
- **AccountShare**: Has `SoftDeleteMixin` ✓ (junction table with audit requirements)

### Repository Methods with `is_active` Filtering

Based on grep results, the following repositories have `is_active` filtering:
- `src/repositories/user_repository.py`
- `src/repositories/account_repository.py`
- `src/repositories/financial_institution_repository.py`
- `src/repositories/account_type_repository.py`

All must be updated to remove `is_active` filters.

### API Endpoints with `is_active`

Based on grep results, the following routes reference `is_active`:
- `src/api/routes/users.py`
- `src/api/routes/accounts.py`
- `src/api/routes/financial_institutions.py`
- `src/api/routes/account_types.py`

All must be updated to remove `is_active` from request/response handling.

### Test Files with `is_active` Assertions

Based on grep results, 10 test files reference `is_active`:
- Unit tests (3): `test_auth_service.py`, `test_user_service.py`, `test_account_service.py`
- Repository tests (1): `test_account_repository.py`
- Integration tests (6): Various route tests

All must be updated to test `deleted_at` instead of `is_active`.

---

## Conclusion

This implementation plan provides a comprehensive roadmap for establishing consistent soft delete patterns across the Emerald Finance Platform. By removing the redundant `is_active` field and relying exclusively on `deleted_at`, we simplify the codebase, reduce cognitive load, and maintain clear semantics for entity status.

The refactoring is **atomic** and must be completed in a single phase to avoid leaving the codebase in an inconsistent state. With careful attention to the detailed specifications above, the implementation should be straightforward and result in a cleaner, more maintainable codebase.

**Key Takeaways**:
- **Single source of truth**: `deleted_at` field in repository layer only
- **Clear layer separation**: Repository = ONLY layer that knows about `deleted_at`. Services and routes NEVER check entity status.
- **Trust-based architecture**: Services trust repository filtering - if entity returned, it's active. If `None` returned, entity not found (deleted OR never existed = equivalent).
- **Simplified business logic**: No status checks in services - just handle NotFoundError when repository returns `None`
- **Automatic filtering**: `BaseRepository._apply_soft_delete_filter()` handles all soft delete logic
- **Compliance-ready**: Audit trail preservation through soft delete
- **Breaking changes**: API responses will no longer include `is_active`

**Next Steps**:
1. Review and approve this plan
2. Create feature branch: `refactor/soft-delete-consistency`
3. Begin implementation following the detailed task list in Phase 1
4. Run tests frequently to catch regressions early
5. Review and merge after all criteria met
