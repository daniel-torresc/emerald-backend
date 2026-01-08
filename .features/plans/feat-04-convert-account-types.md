# Implementation Plan: Convert Accounts to Use Account Types Table

**Feature ID**: feat-04-convert-account-types
**Phase**: 2 - Integration
**Priority**: High
**Estimated Effort**: 1 week (40 hours)
**Dependencies**: Feature 1.2 (Account Types Master Data) - ✅ Complete

---

## Executive Summary

This implementation plan details the migration of the `accounts` table from using a hardcoded `AccountType` enum (with 4 fixed values: checking, savings, investment, other) to a flexible foreign key relationship with the `account_types` table. This migration enables users to leverage both system-defined and custom account types, providing a foundation for specialized account categories (HSA, 529, Crypto, etc.).

### Primary Objectives

1. **Database Migration**: Replace the `account_type` enum column with `account_type_id` UUID foreign key
2. **Data Integrity**: Migrate all existing accounts to reference the correct account_type records
3. **API Evolution**: Update all account endpoints to accept/return `account_type_id` instead of enum strings
4. **Client Compatibility**: Document breaking changes and provide clear migration path for API clients
5. **Zero Data Loss**: Ensure all accounts maintain their type classification through the migration

### Expected Outcomes

- **Flexibility**: Users can create custom account types beyond the 4 system defaults
- **Scalability**: Support for unlimited account type variations without code changes
- **Better UX**: Account types with descriptions, icons, and metadata for improved user experience
- **Type Safety**: Foreign key constraints prevent invalid account type references
- **Backward Compatibility**: Clear migration path minimizes client disruption

### Success Criteria

- All accounts successfully migrated with correct account type references
- Account type enum removed from database and codebase
- All API endpoints updated and tested
- Zero data loss or corruption
- Test coverage ≥80% for all changes
- API documentation updated with migration guide

---

## Technical Architecture

### 2.1 System Design Overview

The migration involves transforming a tightly-coupled enum-based classification system into a flexible foreign key relationship:

```
BEFORE:
┌─────────────────────────────────┐
│  accounts                       │
│  ├─ id: UUID                    │
│  ├─ account_name: VARCHAR       │
│  ├─ account_type: ENUM ───────► (checking, savings, investment, other)
│  └─ ...                         │
└─────────────────────────────────┘

AFTER:
┌─────────────────────────────────┐       ┌────────────────────────────────┐
│  accounts                       │       │  account_types                 │
│  ├─ id: UUID                    │       │  ├─ id: UUID (PK)              │
│  ├─ account_name: VARCHAR       │       │  ├─ key: VARCHAR (unique)      │
│  ├─ account_type_id: UUID ──────┼──────►│  ├─ name: VARCHAR              │
│  │    (FK, NOT NULL)            │       │  ├─ description: VARCHAR       │
│  └─ ...                         │       │  ├─ icon_url: VARCHAR          │
└─────────────────────────────────┘       │  ├─ is_system: BOOLEAN         │
                                          │  ├─ user_id: UUID (nullable)   │
                                          │  └─ is_active: BOOLEAN         │
                                          └────────────────────────────────┘
```

#### Key Integration Points

1. **Account Model** (`src/models/account.py`):
   - Remove `account_type: AccountType` enum field
   - Add `account_type_id: UUID` foreign key field
   - Add SQLAlchemy relationship to `AccountType` model
   - Add index on `account_type_id` for query performance

2. **Account Service** (`src/services/account_service.py`):
   - Update `create_account()` to accept `account_type_id` instead of `account_type` enum
   - Add validation: account type must exist, be active, and be accessible to user
   - Update `update_account()` to allow changing account type (with same validations)
   - Implement business logic for account type accessibility (system types vs custom types)

3. **Account Repository** (`src/repositories/account_repository.py`):
   - Update queries to join with `account_types` table
   - Add filtering methods for `account_type_id`
   - Ensure soft delete queries include account type relationship

4. **Account Schemas** (`src/schemas/account.py`):
   - Update `AccountCreate` to accept `account_type_id: UUID` instead of `account_type: AccountType`
   - Update `AccountUpdate` to allow changing `account_type_id`
   - Update `AccountResponse` to include nested `account_type` object with full details
   - Add validators for account type ID format and non-nil UUID

5. **Account Routes** (`src/api/routes/accounts.py`):
   - Update endpoint documentation to reflect new field
   - Add query parameter `account_type_id` for filtering accounts by type
   - Return account type details in responses (id, key, name, description, icon)

#### Data Flow

```
1. CLIENT REQUEST
   POST /api/v1/accounts
   { "account_type_id": "uuid-here", ... }
          ↓
2. PYDANTIC VALIDATION (schemas/account.py)
   - Validate UUID format
   - Validate not nil UUID
          ↓
3. ROUTE LAYER (api/routes/accounts.py)
   - Extract account_type_id
   - Pass to service layer
          ↓
4. SERVICE LAYER (services/account_service.py)
   - Validate account type exists
   - Validate account type is active
   - Validate user can access type (system or own custom)
   - Create account with account_type_id
          ↓
5. REPOSITORY LAYER (repositories/account_repository.py)
   - Insert account record with account_type_id FK
   - Join with account_types on response
          ↓
6. DATABASE
   - Foreign key constraint enforced
   - Data persisted
          ↓
7. RESPONSE
   - Account object with eager-loaded account_type relationship
   - Serialized to AccountResponse with nested account_type details
```

### 2.2 Technology Decisions

#### **Alembic Migration Framework**
- **Purpose**: Database schema migrations for PostgreSQL
- **Why this choice**: Already used in the project; supports async operations; excellent PostgreSQL support
- **Version**: 1.13+ (supports async operations)
- **Alternatives considered**:
  - Manual SQL migrations: Rejected due to lack of version control and rollback support
  - Django migrations: Not compatible with SQLAlchemy/FastAPI stack

#### **SQLAlchemy 2.0 Async ORM**
- **Purpose**: Object-relational mapping with async support
- **Why this choice**: Project standard; native async/await support; powerful relationship loading
- **Version**: 2.0+ (async only)
- **Key features used**:
  - `Mapped[UUID]` type annotations
  - `relationship()` with `lazy="selectin"` for async-safe eager loading
  - `ForeignKey()` with `ondelete="RESTRICT"` to prevent orphaned accounts

#### **Pydantic v2**
- **Purpose**: Request/response validation and serialization
- **Why this choice**: FastAPI native integration; excellent UUID support; nested model serialization
- **Version**: 2.0+
- **Key features**:
  - UUID field validation (automatic from type hint)
  - `model_validate()` for ORM model conversion
  - `Field()` with examples for API documentation
  - Nested model serialization for account type details

#### **PostgreSQL Enums Removal Strategy**
- **Approach**: Drop column and enum type completely (not ALTER TYPE)
- **Why this choice**:
  - ALTER TYPE limitations: Cannot remove enum values, only add/rename
  - Clean break: Eliminates confusion between old enum and new FK system
  - Performance: Removes unused type from database catalog
- **References**:
  - [Migrating PostgreSQL Enum using SQLAlchemy and Alembic](https://code.keplergrp.com/blog/migrating-postgresql-enum-sqlalchemy-alembic)
  - [Simplifying PostgreSQL enum migrations](https://roman.pt/posts/alembic-enums/)

### 2.3 File Structure

This migration affects the following directories:

```
src/
├── models/
│   ├── account.py              # MODIFY: Replace enum with FK, add relationship
│   ├── enums.py                # MODIFY: Remove AccountType enum (keep others)
│   └── account_type.py         # EXISTS: AccountType model (from Feature 1.2)
│
├── schemas/
│   └── account.py              # MODIFY: Replace enum with UUID, add nested type
│
├── services/
│   ├── account_service.py      # MODIFY: Update CRUD methods for FK
│   └── account_type_service.py # EXISTS: Already implemented
│
├── repositories/
│   ├── account_repository.py   # MODIFY: Update queries to join account_types
│   └── account_type_repository.py  # EXISTS: Already implemented
│
├── api/routes/
│   ├── accounts.py             # MODIFY: Update endpoints and docs
│   └── account_types.py        # EXISTS: Already implemented
│
alembic/versions/
│   └── {timestamp}_convert_account_type_to_fk.py  # NEW: Migration script
│
tests/
├── integration/
│   ├── test_account_routes.py  # MODIFY: Update tests for new FK field
│   └── test_account_migration.py  # NEW: Migration-specific tests
│
└── unit/
    ├── test_account_service.py # MODIFY: Update service tests
    └── test_account_schemas.py # MODIFY: Update schema validation tests
```

---

## Implementation Specification

### 3.1 Component Breakdown

#### Component 1: Database Migration

**Files Involved**:
- `alembic/versions/{timestamp}_convert_account_type_to_fk.py` (new)

**Purpose**: Safely migrate the `accounts` table from enum to foreign key relationship with zero data loss.

**Implementation Requirements**:

1. **Core Logic**:
   - Add `account_type_id` column as nullable UUID initially (allows phased migration)
   - Create foreign key constraint to `account_types.id` with `ON DELETE RESTRICT`
   - Create index on `account_type_id` for query performance
   - Migrate existing data by mapping enum values to account_types records
   - Make `account_type_id` NOT NULL after data migration (enforce constraint)
   - Drop old `account_type` enum column
   - Drop `AccountType` enum type from PostgreSQL catalog

2. **Data Handling**:
   - **Input**: Existing accounts with `account_type` enum values
   - **Mapping Strategy**:
     ```sql
     UPDATE accounts
     SET account_type_id = (
       SELECT id FROM account_types
       WHERE key = accounts.account_type::text
         AND is_system = true
     );
     ```
   - **Output**: All accounts have valid `account_type_id` references
   - **Verification**: Count accounts before/after, verify no NULL values

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: account_types table is empty (should never happen if Feature 1.2 complete)
     - **Mitigation**: Add pre-migration check; fail migration if no system types exist
   - [ ] Handle case: Enum value doesn't match any account_type.key
     - **Mitigation**: Use COALESCE to default to 'other' type if no match
   - [ ] Handle case: Multiple account types with same key (should be prevented by unique constraint)
     - **Mitigation**: Rely on unique constraint; migration will fail loudly if violated
   - [ ] Handle case: Foreign key constraint fails during migration
     - **Mitigation**: Verify all account_type_id values reference valid IDs before applying NOT NULL

4. **Dependencies**:
   - **Internal**: Requires `account_types` table to exist and be seeded with system types
   - **External**: PostgreSQL 16+ for enum handling

5. **Testing Requirements**:
   - [ ] Unit test: Migration script syntax is valid (can be imported)
   - [ ] Integration test: Migration runs successfully on empty database
   - [ ] Integration test: Migration runs successfully with existing accounts
     - Create accounts with all 4 enum values (checking, savings, investment, other)
     - Run migration
     - Verify all accounts have account_type_id set correctly
     - Verify enum column dropped
     - Verify enum type dropped
   - [ ] Integration test: Verify rollback (downgrade) works correctly
     - Run migration
     - Downgrade
     - Verify enum column restored
     - Verify data intact

**Acceptance Criteria**:
- [ ] Migration runs without errors on clean database
- [ ] Migration runs without errors on database with existing accounts
- [ ] All accounts have non-NULL account_type_id after migration
- [ ] Mapping verified: checking→checking, savings→savings, investment→investment, other→other
- [ ] Enum column completely removed from accounts table
- [ ] AccountType enum type removed from PostgreSQL catalog
- [ ] Foreign key constraint enforced (cannot insert invalid account_type_id)
- [ ] Index on account_type_id exists and is used by queries
- [ ] Downgrade restores previous state with data intact

**Implementation Notes**:
- **Critical**: Test migration on a copy of production data before deploying
- **Performance**: For large datasets (>100k accounts), consider batched updates to avoid transaction timeout
- **Rollback**: Keep migration reversible for at least 2 weeks post-deployment
- **Monitoring**: Log count of migrated accounts and any failures

---

#### Component 2: Account Model Changes

**Files Involved**:
- `src/models/account.py`
- `src/models/enums.py`

**Purpose**: Update the Account model to use foreign key relationship instead of enum field.

**Implementation Requirements**:

1. **Core Logic** (`src/models/account.py`):

   **Step 1**: Remove enum import and field
   ```python
   # REMOVE:
   from src.models.enums import AccountType

   # REMOVE THIS FIELD:
   account_type: Mapped[AccountType] = mapped_column(
       nullable=False,
       index=True,
   )
   ```

   **Step 2**: Add foreign key field and relationship
   ```python
   # ADD:
   from src.models.account_type import AccountType

   # ADD THIS FIELD (after account_name):
   account_type_id: Mapped[uuid.UUID] = mapped_column(
       UUID(as_uuid=True),
       ForeignKey("account_types.id", ondelete="RESTRICT"),
       nullable=False,
       index=True,
       comment="Foreign key to account_types table",
   )

   # ADD THIS RELATIONSHIP (after owner relationship):
   account_type: Mapped["AccountType"] = relationship(
       "AccountType",
       foreign_keys=[account_type_id],
       lazy="selectin",  # Async-safe eager loading
   )
   ```

   **Step 3**: Update docstring and `__repr__`
   ```python
   # UPDATE docstring (line ~57):
   account_type_id: Foreign key to account_types (system or user-defined type)

   # UPDATE __repr__ (line ~241):
   def __repr__(self) -> str:
       return (
           f"Account(id={self.id}, name={self.account_name}, "
           f"type={self.account_type.key}, balance={self.current_balance} {self.currency}, "
           f"institution={self.financial_institution.short_name})"
       )
   ```

2. **Core Logic** (`src/models/enums.py`):

   **Step 1**: Remove AccountType enum class entirely
   ```python
   # REMOVE lines 17-63 (entire AccountType enum class)
   # KEEP: PermissionLevel, TransactionType, InstitutionType enums
   ```

3. **Data Handling**:
   - **Type change**: `AccountType` (enum) → `uuid.UUID` (foreign key)
   - **Relationship**: Eager-load account type details via `lazy="selectin"`
   - **Access pattern**: `account.account_type.name` instead of `account.account_type.value`

4. **Edge Cases & Error Handling**:
   - [ ] Handle case: account_type relationship returns None
     - **Solution**: NOT NULL constraint on account_type_id prevents this at database level
   - [ ] Handle case: Accessing account_type before it's loaded
     - **Solution**: `lazy="selectin"` ensures eager loading in async context
   - [ ] Handle case: Account type deleted while referenced by accounts
     - **Solution**: ON DELETE RESTRICT prevents this at database level

5. **Dependencies**:
   - **Internal**: Requires AccountType model from `src/models/account_type.py`
   - **Migration**: Must run migration before deploying this code

6. **Testing Requirements**:
   - [ ] Unit test: Account model can be instantiated with account_type_id
   - [ ] Unit test: Account type relationship loads correctly
   - [ ] Unit test: `__repr__` works with account_type.key
   - [ ] Integration test: Create account with account_type_id succeeds
   - [ ] Integration test: Create account with invalid account_type_id fails (FK violation)
   - [ ] Integration test: Create account with NULL account_type_id fails (NOT NULL violation)
   - [ ] Integration test: Account query eager-loads account_type (no N+1 queries)

**Acceptance Criteria**:
- [ ] AccountType enum completely removed from `src/models/enums.py`
- [ ] Account model has `account_type_id` UUID foreign key field
- [ ] Account model has `account_type` relationship with `lazy="selectin"`
- [ ] Account model's `__repr__` uses `account_type.key`
- [ ] No references to old AccountType enum in Account model
- [ ] All imports updated correctly
- [ ] Type hints correct (`Mapped[uuid.UUID]`, `Mapped["AccountType"]`)

**Implementation Notes**:
- **Critical**: Update all imports of `AccountType` enum to point to the model instead
- **Performance**: `lazy="selectin"` prevents N+1 query issues when listing accounts
- **Code Search**: Use grep to find all `from src.models.enums import AccountType` and update

---

#### Component 3: Account Schema Changes

**Files Involved**:
- `src/schemas/account.py`

**Purpose**: Update Pydantic schemas to accept/return `account_type_id` UUID instead of enum, and include account type details in responses.

**Implementation Requirements**:

1. **Core Logic - AccountBase**:

   **Step 1**: Remove enum import and field
   ```python
   # REMOVE:
   from src.models.enums import AccountType

   # REMOVE FROM AccountBase (line ~40):
   account_type: AccountType = Field(...)
   ```

2. **Core Logic - AccountCreate**:

   **Step 1**: Add account_type_id field
   ```python
   # ADD (after account_name, before currency):
   account_type_id: uuid.UUID = Field(
       description="Account type ID (must reference active account type)",
       examples=["550e8400-e29b-41d4-a716-446655440000"],
   )

   # ADD validator (after validate_financial_institution_id):
   @field_validator("account_type_id")
   @classmethod
   def validate_account_type_id(cls, value: uuid.UUID) -> uuid.UUID:
       """
       Validate account type ID is a valid UUID.

       Business validation (exists, is_active, is_accessible) happens in service layer.
       """
       # Ensure not nil UUID
       if value == uuid.UUID("00000000-0000-0000-0000-000000000000"):
           raise ValueError("Account type ID cannot be nil UUID")
       return value
   ```

3. **Core Logic - AccountUpdate**:

   **Step 1**: Add optional account_type_id field
   ```python
   # ADD (after account_name):
   account_type_id: uuid.UUID | None = Field(
       default=None,
       description="New account type ID (optional, must reference active account type)",
       examples=["550e8400-e29b-41d4-a716-446655440000"],
   )

   # ADD validator (after validate_financial_institution_id):
   @field_validator("account_type_id")
   @classmethod
   def validate_account_type_id(cls, value: uuid.UUID | None) -> uuid.UUID | None:
       """Validate account type ID if provided."""
       if value is not None and value == uuid.UUID("00000000-0000-0000-0000-000000000000"):
           raise ValueError("Account type ID cannot be nil UUID")
       return value
   ```

4. **Core Logic - AccountResponse**:

   **Step 1**: Add account_type_id field and nested account_type object
   ```python
   # ADD import at top:
   from src.schemas.account_type import AccountTypeListItem

   # ADD (after financial_institution):
   account_type_id: uuid.UUID = Field(
       description="Account type ID"
   )
   account_type: AccountTypeListItem = Field(
       description="Account type details (key, name, icon, etc.)"
   )
   ```

5. **Core Logic - AccountListItem**:

   **Step 1**: Add account_type_id field and nested account_type object
   ```python
   # ADD import at top (if not already present):
   from src.schemas.account_type import AccountTypeListItem

   # REPLACE:
   account_type: AccountType  # OLD

   # WITH:
   account_type_id: uuid.UUID
   account_type: AccountTypeListItem
   ```

6. **Core Logic - AccountFilterParams**:

   **Step 1**: Update filter to use account_type_id instead of enum
   ```python
   # REPLACE:
   account_type: AccountType | None = Field(...)  # OLD

   # WITH:
   account_type_id: uuid.UUID | None = Field(
       default=None,
       description="Filter by account type ID",
   )
   ```

7. **Data Handling**:
   - **Input format**: `{"account_type_id": "uuid-string"}`
   - **Output format**:
     ```json
     {
       "account_type_id": "uuid-here",
       "account_type": {
         "id": "uuid-here",
         "key": "checking",
         "name": "Checking Account",
         "icon_url": "💳",
         "is_active": true,
         "sort_order": 1
       }
     }
     ```
   - **Nested serialization**: Pydantic automatically serializes `AccountType` model to `AccountTypeListItem` schema using `model_config = {"from_attributes": True}`

8. **Edge Cases & Error Handling**:
   - [ ] Validate: account_type_id is valid UUID format
     - **Solution**: Automatic from UUID type hint
   - [ ] Validate: account_type_id is not nil UUID
     - **Solution**: Custom validator checks for all-zeros UUID
   - [ ] Handle: Invalid UUID format in request
     - **Solution**: Pydantic returns 422 Unprocessable Entity with detailed error
   - [ ] Handle: Missing account_type_id in create request
     - **Solution**: Pydantic enforces required field (422 error)

9. **Dependencies**:
   - **Internal**: Requires `AccountTypeListItem` schema from `src/schemas/account_type.py`
   - **Pydantic**: Version 2.0+ for nested model serialization

10. **Testing Requirements**:
    - [ ] Unit test: AccountCreate validates UUID format
    - [ ] Unit test: AccountCreate rejects nil UUID
    - [ ] Unit test: AccountCreate requires account_type_id (not optional)
    - [ ] Unit test: AccountUpdate accepts optional account_type_id
    - [ ] Unit test: AccountUpdate rejects nil UUID if provided
    - [ ] Unit test: AccountResponse serializes with nested account_type object
    - [ ] Unit test: AccountListItem serializes with nested account_type object
    - [ ] Unit test: AccountFilterParams accepts account_type_id filter
    - [ ] Integration test: API validates account_type_id in create request
    - [ ] Integration test: API returns account_type details in response

**Acceptance Criteria**:
- [ ] AccountType enum import removed from schemas
- [ ] AccountCreate accepts `account_type_id: UUID` (required)
- [ ] AccountUpdate accepts `account_type_id: UUID | None` (optional)
- [ ] AccountResponse includes `account_type_id` and nested `account_type` object
- [ ] AccountListItem includes `account_type_id` and nested `account_type` object
- [ ] AccountFilterParams uses `account_type_id` for filtering
- [ ] All validators updated to handle UUID instead of enum
- [ ] Nil UUID validation in place for all schemas
- [ ] Type hints correct and passing mypy checks

**Implementation Notes**:
- **Breaking Change**: This changes the API contract; coordinate with frontend team
- **Documentation**: OpenAPI schema will automatically update with new UUID field
- **Migration Guide**: Provide mapping from enum strings to UUID fetch endpoint

---

#### Component 4: Account Service Updates

**Files Involved**:
- `src/services/account_service.py`

**Purpose**: Update service layer business logic to handle account_type_id foreign key, including validation that account type exists, is active, and is accessible to the user.

**Implementation Requirements**:

1. **Core Logic - create_account()**:

   **Step 1**: Update method signature
   ```python
   # CHANGE (line ~70):
   async def create_account(
       self,
       user_id: uuid.UUID,
       account_name: str,
       account_type_id: uuid.UUID,  # CHANGED from account_type: AccountType
       currency: str,
       opening_balance: Decimal,
       financial_institution_id: uuid.UUID,
       current_user: User,
       # ... rest of params
   ) -> Account:
   ```

   **Step 2**: Add account type validation logic (before financial institution check)
   ```python
   # ADD (around line ~115, before financial institution validation):

   # Validate account type exists and is active
   account_type = await self.account_type_repo.get_by_id(account_type_id)
   if not account_type:
       raise NotFoundError(
           message=f"Account type with ID {account_type_id} not found",
           resource="account_type",
       )

   if not account_type.is_active:
       raise ValidationError(
           message="Cannot create account with inactive account type",
           field="account_type_id",
       )

   # Validate user can access this account type
   # System types (is_system=True) are accessible to all users
   # Custom types (is_system=False) are only accessible to their creator
   if not account_type.is_system and account_type.user_id != current_user.id:
       raise AuthorizationError(
           message="You do not have permission to use this custom account type",
           resource="account_type",
       )
   ```

   **Step 3**: Update Account creation
   ```python
   # CHANGE (around line ~160):
   account = Account(
       user_id=user_id,
       account_name=account_name,
       account_type_id=account_type_id,  # CHANGED from account_type
       currency=currency.upper(),
       # ... rest of fields
   )
   ```

   **Step 4**: Add repository dependency
   ```python
   # ADD to __init__ method (line ~54):
   from src.repositories.account_type_repository import AccountTypeRepository

   def __init__(self, session: AsyncSession, encryption_service: EncryptionService):
       # ... existing init code
       self.account_type_repo = AccountTypeRepository(session)  # ADD THIS
   ```

2. **Core Logic - update_account()**:

   **Step 1**: Allow account_type_id in updates
   ```python
   # UPDATE method signature (add parameter around line ~220):
   async def update_account(
       self,
       account_id: uuid.UUID,
       current_user: User,
       account_name: str | None = None,
       is_active: bool | None = None,
       financial_institution_id: uuid.UUID | None = None,
       account_type_id: uuid.UUID | None = None,  # ADD THIS
       color_hex: str | None = None,
       icon_url: HttpUrl | None = None,
       notes: str | None = None,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None,
   ) -> Account:
   ```

   **Step 2**: Add validation for account_type_id if provided
   ```python
   # ADD (after financial_institution_id validation, around line ~270):
   if account_type_id is not None:
       # Validate account type exists and is active
       account_type = await self.account_type_repo.get_by_id(account_type_id)
       if not account_type:
           raise NotFoundError(
               message=f"Account type with ID {account_type_id} not found",
               resource="account_type",
           )

       if not account_type.is_active:
           raise ValidationError(
               message="Cannot change to inactive account type",
               field="account_type_id",
           )

       # Validate user can access this account type
       if not account_type.is_system and account_type.user_id != current_user.id:
           raise AuthorizationError(
               message="You do not have permission to use this custom account type",
               resource="account_type",
           )

       # Update account type
       account.account_type_id = account_type_id
   ```

3. **Core Logic - list_accounts()**:

   **Step 1**: Update filter parameter
   ```python
   # UPDATE method signature (around line ~320):
   async def list_accounts(
       self,
       user_id: uuid.UUID,
       is_active: bool | None = None,
       account_type_id: uuid.UUID | None = None,  # CHANGED from account_type
       financial_institution_id: uuid.UUID | None = None,
       skip: int = 0,
       limit: int = 20,
   ) -> list[Account]:
   ```

   **Step 2**: Update repository call
   ```python
   # UPDATE (around line ~340):
   accounts = await self.account_repo.get_accounts_by_user(
       user_id=user_id,
       is_active=is_active,
       account_type_id=account_type_id,  # CHANGED from account_type
       financial_institution_id=financial_institution_id,
       skip=skip,
       limit=limit,
   )
   ```

4. **Data Handling**:
   - **Input validation**: Verify account_type_id references an existing, active account type
   - **Authorization**: System types accessible to all; custom types only to creator
   - **State changes**: Account can change from one type to another (with same validations)

5. **Edge Cases & Error Handling**:
   - [ ] Validate: account_type_id references existing account type
     - **Error**: NotFoundError with resource="account_type"
   - [ ] Validate: account type is active (is_active=True)
     - **Error**: ValidationError with field="account_type_id"
   - [ ] Validate: user can access account type (system or owned custom)
     - **Error**: AuthorizationError with message explaining custom type ownership
   - [ ] Handle: account_type_id is None in update (should be allowed, means no change)
     - **Solution**: Skip validation if account_type_id is None

6. **Dependencies**:
   - **Internal**:
     - `AccountTypeRepository` for fetching account type records
     - `NotFoundError`, `ValidationError`, `AuthorizationError` exceptions
   - **Business Rules**:
     - System account types (is_system=True) are globally accessible
     - Custom account types (is_system=False) are only accessible to their creator (user_id)

7. **Testing Requirements**:
   - [ ] Unit test: create_account validates account type exists
   - [ ] Unit test: create_account rejects inactive account type
   - [ ] Unit test: create_account allows system account type for any user
   - [ ] Unit test: create_account allows custom account type for owner
   - [ ] Unit test: create_account rejects custom account type for non-owner
   - [ ] Unit test: update_account validates account type if provided
   - [ ] Unit test: update_account allows changing account type (with validation)
   - [ ] Unit test: list_accounts filters by account_type_id
   - [ ] Integration test: Create account with system type succeeds
   - [ ] Integration test: Create account with own custom type succeeds
   - [ ] Integration test: Create account with other user's custom type fails (403)
   - [ ] Integration test: Create account with inactive type fails (400)
   - [ ] Integration test: Create account with non-existent type fails (404)
   - [ ] Integration test: Update account type succeeds with valid type
   - [ ] Integration test: List accounts filtered by account_type_id works

**Acceptance Criteria**:
- [ ] `create_account()` accepts `account_type_id` instead of `account_type` enum
- [ ] `create_account()` validates account type exists and is active
- [ ] `create_account()` validates user can access account type (system or owned custom)
- [ ] `update_account()` allows changing account_type_id with same validations
- [ ] `list_accounts()` filters by `account_type_id` instead of enum
- [ ] AccountTypeRepository dependency added to service
- [ ] All validation errors have clear messages
- [ ] Authorization logic correctly distinguishes system vs custom types

**Implementation Notes**:
- **Security**: Custom account types are user-scoped; prevent access to other users' types
- **Performance**: account_type_repo.get_by_id() is a single query; acceptable overhead
- **Alternative**: Could add a method `validate_account_type_access()` to reduce duplication between create and update

---

#### Component 5: Account Repository Updates

**Files Involved**:
- `src/repositories/account_repository.py`

**Purpose**: Update repository queries to handle account_type_id foreign key and join with account_types table for eager loading.

**Implementation Requirements**:

1. **Core Logic - get_accounts_by_user()**:

   **Step 1**: Update method signature
   ```python
   # UPDATE (around line ~50):
   async def get_accounts_by_user(
       self,
       user_id: uuid.UUID,
       is_active: bool | None = None,
       account_type_id: uuid.UUID | None = None,  # CHANGED from account_type
       financial_institution_id: uuid.UUID | None = None,
       skip: int = 0,
       limit: int = 20,
   ) -> list[Account]:
   ```

   **Step 2**: Update filter logic
   ```python
   # UPDATE query builder (around line ~65):
   query = (
       select(Account)
       .where(Account.user_id == user_id)
       .where(Account.deleted_at.is_(None))  # Soft delete filter
   )

   if is_active is not None:
       query = query.where(Account.is_active == is_active)

   if account_type_id is not None:  # CHANGED from account_type
       query = query.where(Account.account_type_id == account_type_id)

   if financial_institution_id is not None:
       query = query.where(Account.financial_institution_id == financial_institution_id)

   query = (
       query
       .order_by(Account.created_at.desc())
       .offset(skip)
       .limit(limit)
   )
   ```

2. **Core Logic - Eager Loading Verification**:

   The model already has `lazy="selectin"` on the account_type relationship, so no changes needed here. Repository just needs to ensure queries don't break eager loading.

   **Verification Step**: Confirm account_type relationship is loaded
   ```python
   # NO CHANGES needed if model has:
   # account_type: Mapped["AccountType"] = relationship(
   #     "AccountType",
   #     lazy="selectin",
   # )

   # SQLAlchemy will automatically issue a second query to load all account_types
   # for the returned accounts using a SELECT IN query (N+1 prevention)
   ```

3. **Data Handling**:
   - **Input**: Filter parameters including `account_type_id: UUID | None`
   - **Query**: Standard SQLAlchemy select with WHERE clause on account_type_id
   - **Output**: List of Account objects with account_type relationship eager-loaded
   - **Performance**: `lazy="selectin"` issues 1 query for accounts + 1 query for all their account_types (total: 2 queries)

4. **Edge Cases & Error Handling**:
   - [ ] Handle: account_type_id filter is None (return all types)
     - **Solution**: Conditional WHERE clause only added if not None
   - [ ] Handle: account_type_id references non-existent type
     - **Solution**: Query returns empty result set (no error, expected behavior)
   - [ ] Handle: Account has account_type_id but account type is deleted
     - **Solution**: Relationship still loads (no soft delete on account_types)

5. **Dependencies**:
   - **Internal**: Account model with account_type relationship
   - **SQLAlchemy**: Version 2.0+ for select() syntax

6. **Testing Requirements**:
   - [ ] Unit test: get_accounts_by_user filters by account_type_id
   - [ ] Unit test: get_accounts_by_user returns empty list if no matches
   - [ ] Unit test: Query structure correct (WHERE clause on account_type_id)
   - [ ] Integration test: Filter by account_type_id returns correct accounts
   - [ ] Integration test: Filter by non-existent account_type_id returns empty list
   - [ ] Integration test: Account type relationship is eager-loaded (no N+1)
   - [ ] Performance test: Verify only 2 queries issued for list of 50 accounts

**Acceptance Criteria**:
- [ ] `get_accounts_by_user()` accepts `account_type_id` parameter
- [ ] Query filters by `Account.account_type_id` when provided
- [ ] Account type relationship is eager-loaded (no N+1 queries)
- [ ] All existing repository tests pass with account_type_id instead of enum
- [ ] No performance regression in account listing queries

**Implementation Notes**:
- **Minimal Changes**: Repository changes are small due to SQLAlchemy's automatic FK handling
- **Performance**: Eager loading via `lazy="selectin"` is optimal for async contexts
- **Alternative**: Could use `joinedload()` for single query, but selectin is safer for async

---

#### Component 6: API Route Updates

**Files Involved**:
- `src/api/routes/accounts.py`

**Purpose**: Update API endpoints to accept `account_type_id` in requests, return account type details in responses, and update documentation.

**Implementation Requirements**:

1. **Core Logic - create_account endpoint**:

   **Step 1**: Update service call
   ```python
   # UPDATE (around line ~105):
   account = await account_service.create_account(
       user_id=current_user.id,
       account_name=account_data.account_name,
       account_type_id=account_data.account_type_id,  # CHANGED from account_type
       currency=account_data.currency,
       opening_balance=account_data.opening_balance,
       financial_institution_id=account_data.financial_institution_id,
       current_user=current_user,
       # ... rest of params
   )
   ```

   **Step 2**: Update docstring and examples
   ```python
   # UPDATE docstring (around line ~82):
   """
   Request body:
       - account_name: Account name (1-100 characters, unique per user)
       - account_type_id: Account type UUID (must reference active system or user's custom type)
       - currency: ISO 4217 code (USD, EUR, GBP, etc.)
       - financial_institution_id: Financial institution UUID (REQUIRED, must be active)
       # ... rest of fields
   """

   # UPDATE example response (around line ~54):
   "example": {
       "id": "550e8400-e29b-41d4-a716-446655440000",
       "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
       "account_name": "Chase Checking",
       "account_type_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
       "account_type": {
           "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
           "key": "checking",
           "name": "Checking Account",
           "icon_url": "💳",
           "is_active": true,
           "sort_order": 1
       },
       "currency": "USD",
       "opening_balance": "1000.00",
       # ... rest of fields
   }
   ```

2. **Core Logic - update_account endpoint**:

   **Step 1**: Update service call to pass account_type_id
   ```python
   # UPDATE (around line ~235):
   account = await account_service.update_account(
       account_id=account_id,
       current_user=current_user,
       account_name=update_data.account_name,
       is_active=update_data.is_active,
       financial_institution_id=update_data.financial_institution_id,
       account_type_id=update_data.account_type_id,  # ADD THIS
       color_hex=update_data.color_hex,
       icon_url=update_data.icon_url,
       notes=update_data.notes,
       # ... rest of params
   )
   ```

   **Step 2**: Update docstring
   ```python
   # UPDATE docstring (around line ~200):
   """
   Request body (all fields optional):
       - account_name: New account name
       - is_active: New active status
       - financial_institution_id: New financial institution ID
       - account_type_id: New account type ID (must be active and accessible)
       # ... rest of fields
   """
   ```

3. **Core Logic - list_accounts endpoint**:

   **Step 1**: Update query parameters
   ```python
   # UPDATE (around line ~130):
   @router.get(
       "",
       response_model=list[AccountListItem],
       # ... rest of decorator
   )
   async def list_accounts(
       is_active: bool | None = Query(None, description="Filter by active status"),
       account_type_id: uuid.UUID | None = Query(None, description="Filter by account type ID"),  # CHANGED
       financial_institution_id: uuid.UUID | None = Query(None, description="Filter by institution"),
       skip: int = Query(0, ge=0),
       limit: int = Query(20, ge=1, le=100),
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service),
   ) -> list[AccountListItem]:
   ```

   **Step 2**: Update service call
   ```python
   # UPDATE (around line ~165):
   accounts = await account_service.list_user_accounts(
       user_id=current_user.id,
       is_active=is_active,
       account_type_id=account_type_id,  # CHANGED from account_type
       financial_institution_id=financial_institution_id,
       skip=skip,
       limit=limit,
   )
   ```

   **Step 3**: Update example response
   ```python
   # UPDATE example (around line ~145):
   "example": [
       {
           "id": "550e8400-e29b-41d4-a716-446655440000",
           "account_name": "Chase Checking",
           "account_type_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
           "account_type": {
               "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
               "key": "checking",
               "name": "Checking Account",
               "icon_url": "💳",
               "is_active": true,
               "sort_order": 1
           },
           "currency": "USD",
           "current_balance": "1234.56",
           # ... rest of fields
       }
   ]
   ```

4. **Core Logic - Import updates**:

   **Step 1**: Remove AccountType enum import
   ```python
   # REMOVE (around line ~18):
   from src.models.enums import AccountType
   ```

5. **Data Handling**:
   - **Input**: Accept `account_type_id: UUID` in create/update requests
   - **Query params**: Accept `account_type_id: UUID | None` for filtering
   - **Output**: Return nested account_type object with full details in all responses
   - **Serialization**: Pydantic handles ORM→schema conversion automatically

6. **Edge Cases & Error Handling**:
   - [ ] Handle: Invalid UUID format in account_type_id
     - **Solution**: FastAPI/Pydantic returns 422 with validation error details
   - [ ] Handle: Non-existent account_type_id
     - **Solution**: Service layer returns 404 NotFoundError
   - [ ] Handle: Inactive account_type_id
     - **Solution**: Service layer returns 400 ValidationError
   - [ ] Handle: Other user's custom account type
     - **Solution**: Service layer returns 403 AuthorizationError

7. **Dependencies**:
   - **Internal**: Updated AccountService methods
   - **Schemas**: Updated AccountCreate, AccountUpdate, AccountResponse, AccountListItem

8. **Testing Requirements**:
   - [ ] Integration test: POST /accounts with account_type_id succeeds
   - [ ] Integration test: POST /accounts with invalid account_type_id returns 404
   - [ ] Integration test: POST /accounts with inactive account_type_id returns 400
   - [ ] Integration test: POST /accounts with other user's custom type returns 403
   - [ ] Integration test: PATCH /accounts with account_type_id succeeds
   - [ ] Integration test: GET /accounts returns account_type details
   - [ ] Integration test: GET /accounts?account_type_id=uuid filters correctly
   - [ ] Integration test: OpenAPI schema shows account_type_id as UUID
   - [ ] Integration test: OpenAPI schema shows account_type as nested object

**Acceptance Criteria**:
- [ ] All endpoints accept `account_type_id: UUID` instead of enum
- [ ] All responses include nested `account_type` object with details
- [ ] List endpoint has `account_type_id` query parameter for filtering
- [ ] All docstrings updated to reflect new field
- [ ] All example responses show new structure
- [ ] OpenAPI schema updated (automatic via Pydantic)
- [ ] Import of AccountType enum removed

**Implementation Notes**:
- **Breaking Change**: API contract changes; frontend must update simultaneously
- **Documentation**: OpenAPI schema auto-updates; provide migration guide separately
- **Coordination**: Schedule deployment with frontend team to avoid breaking clients

---

#### Component 7: Testing Updates

**Files Involved**:
- `tests/integration/test_account_routes.py`
- `tests/unit/test_account_service.py`
- `tests/unit/test_account_schemas.py`
- `tests/integration/test_account_migration.py` (new)

**Purpose**: Update existing tests to use account_type_id instead of enum, and add comprehensive migration-specific tests.

**Implementation Requirements**:

1. **Core Logic - Update test_account_routes.py**:

   **Step 1**: Update test fixtures to create account types
   ```python
   # ADD at top of file (after imports):
   @pytest.fixture
   async def checking_account_type(async_client: AsyncClient, admin_token: dict):
       """Fetch checking account type (system type)."""
       response = await async_client.get(
           "/api/v1/account-types?key=checking",
           headers={"Authorization": f"Bearer {admin_token['access_token']}"},
       )
       assert response.status_code == 200
       types = response.json()
       assert len(types) > 0
       return types[0]  # Return first matching type

   @pytest.fixture
   async def savings_account_type(async_client: AsyncClient, admin_token: dict):
       """Fetch savings account type (system type)."""
       response = await async_client.get(
           "/api/v1/account-types?key=savings",
           headers={"Authorization": f"Bearer {admin_token['access_token']}"},
       )
       assert response.status_code == 200
       types = response.json()
       return types[0]
   ```

   **Step 2**: Update test_create_account
   ```python
   # UPDATE:
   async def test_create_account(async_client, test_user_token, active_institution, checking_account_type):
       response = await async_client.post(
           "/api/v1/accounts",
           json={
               "account_name": "My Checking",
               "account_type_id": checking_account_type["id"],  # CHANGED from "account_type": "checking"
               "currency": "USD",
               "opening_balance": "1000.00",
               "financial_institution_id": str(active_institution.id),
           },
           headers={"Authorization": f"Bearer {test_user_token['access_token']}"},
       )
       assert response.status_code == 201
       data = response.json()
       assert data["account_type_id"] == checking_account_type["id"]
       assert data["account_type"]["key"] == "checking"  # Verify nested object
       assert data["account_type"]["name"] == "Checking Account"
   ```

   **Step 3**: Update all other account creation tests similarly
   - test_create_account_duplicate_name
   - test_create_account_invalid_currency
   - test_update_account
   - test_list_accounts
   - test_filter_accounts_by_type

2. **Core Logic - Update test_account_service.py**:

   **Step 1**: Update test fixtures
   ```python
   # ADD fixture for account type:
   @pytest.fixture
   async def checking_account_type(session: AsyncSession):
       """Create system checking account type."""
       from src.repositories.account_type_repository import AccountTypeRepository
       repo = AccountTypeRepository(session)

       # Fetch existing system type
       types = await repo.get_all(is_active=True, is_system=True)
       checking = next((t for t in types if t.key == "checking"), None)
       assert checking is not None, "System checking type not found"
       return checking
   ```

   **Step 2**: Update service tests
   ```python
   # UPDATE:
   async def test_create_account(account_service, test_user, active_institution, checking_account_type):
       account = await account_service.create_account(
           user_id=test_user.id,
           account_name="Test Account",
           account_type_id=checking_account_type.id,  # CHANGED from account_type=AccountType.checking
           currency="USD",
           opening_balance=Decimal("1000.00"),
           financial_institution_id=active_institution.id,
           current_user=test_user,
       )
       assert account.account_type_id == checking_account_type.id
       assert account.account_type.key == "checking"  # Test relationship
   ```

3. **Core Logic - Update test_account_schemas.py**:

   **Step 1**: Update schema validation tests
   ```python
   # UPDATE:
   def test_account_create_valid(checking_account_type_id, active_institution_id):
       data = {
           "account_name": "My Checking",
           "account_type_id": str(checking_account_type_id),  # CHANGED
           "currency": "USD",
           "opening_balance": "1000.00",
           "financial_institution_id": str(active_institution_id),
       }
       schema = AccountCreate(**data)
       assert schema.account_type_id == checking_account_type_id

   def test_account_create_nil_uuid():
       data = {
           "account_name": "Test",
           "account_type_id": "00000000-0000-0000-0000-000000000000",  # Nil UUID
           "currency": "USD",
           "opening_balance": "1000.00",
           "financial_institution_id": "550e8400-e29b-41d4-a716-446655440000",
       }
       with pytest.raises(ValidationError, match="Account type ID cannot be nil UUID"):
           AccountCreate(**data)
   ```

4. **Core Logic - Create test_account_migration.py** (new file):

   **Purpose**: Test the migration script in isolation

   ```python
   """
   Tests for account type enum to FK migration.

   These tests verify the migration script works correctly with:
   - Empty database
   - Database with existing accounts
   - All 4 enum values (checking, savings, investment, other)
   - Rollback/downgrade scenarios
   """

   import pytest
   from alembic import command
   from alembic.config import Config
   from sqlalchemy.ext.asyncio import AsyncSession


   @pytest.mark.asyncio
   async def test_migration_on_empty_database(session: AsyncSession):
       """Test migration runs successfully on empty database."""
       # Run migration (tested separately from pytest using alembic CLI)
       # This test verifies post-migration state

       # Verify account_type enum column does not exist
       result = await session.execute(
           "SELECT column_name FROM information_schema.columns "
           "WHERE table_name = 'accounts' AND column_name = 'account_type'"
       )
       assert result.scalar() is None, "account_type enum column should be removed"

       # Verify account_type_id column exists
       result = await session.execute(
           "SELECT column_name FROM information_schema.columns "
           "WHERE table_name = 'accounts' AND column_name = 'account_type_id'"
       )
       assert result.scalar() == "account_type_id"

       # Verify FK constraint exists
       result = await session.execute(
           "SELECT constraint_name FROM information_schema.table_constraints "
           "WHERE table_name = 'accounts' AND constraint_type = 'FOREIGN KEY' "
           "AND constraint_name LIKE '%account_type_id%'"
       )
       assert result.scalar() is not None, "FK constraint should exist"


   @pytest.mark.asyncio
   async def test_migration_with_existing_accounts(session: AsyncSession):
       """Test migration correctly maps existing accounts to account types."""
       # This test would need to:
       # 1. Insert accounts with old enum structure (in downgraded state)
       # 2. Run upgrade migration
       # 3. Verify all accounts have account_type_id set
       # 4. Verify mapping is correct (enum value → account_type.key)

       # Count accounts before migration
       # Run migration
       # Count accounts after migration (should match)
       # Verify no accounts have NULL account_type_id
       pass  # Implementation in Phase 1
   ```

5. **Data Handling**:
   - **Test data**: Use fixtures to fetch system account types
   - **Assertions**: Verify both account_type_id field and nested account_type object
   - **Coverage**: Test all CRUD operations with new field structure

6. **Edge Cases & Error Handling**:
   - [ ] Test: Create account with non-existent account_type_id (404)
   - [ ] Test: Create account with inactive account_type_id (400)
   - [ ] Test: Create account with other user's custom account type (403)
   - [ ] Test: Create account with nil UUID account_type_id (422)
   - [ ] Test: Update account type to valid type (200)
   - [ ] Test: Update account type to invalid type (404/400)
   - [ ] Test: Filter accounts by account_type_id (returns correct subset)
   - [ ] Test: Migration preserves all account data
   - [ ] Test: Migration correctly maps all 4 enum values

7. **Dependencies**:
   - **Fixtures**: Need to create/fetch account types before creating accounts
   - **Test data**: Seed system account types in test database setup

8. **Testing Requirements**:
   - [ ] Update all test_account_routes.py tests to use account_type_id
   - [ ] Update all test_account_service.py tests to use account_type_id
   - [ ] Update all test_account_schemas.py tests to validate UUID field
   - [ ] Create test_account_migration.py with migration-specific tests
   - [ ] Add fixtures for fetching system account types
   - [ ] Add tests for custom account type access control
   - [ ] Ensure test coverage ≥80% for all modified code
   - [ ] Verify no test regressions (all existing tests pass)

**Acceptance Criteria**:
- [ ] All existing account tests updated to use account_type_id
- [ ] All tests pass with new field structure
- [ ] Migration-specific tests added and passing
- [ ] Test coverage ≥80% for all modified code
- [ ] Fixtures created for account types
- [ ] Tests verify nested account_type object in responses
- [ ] Edge cases covered (invalid IDs, access control, etc.)

**Implementation Notes**:
- **Test Data**: Use system account types seeded in test database setup
- **Fixtures**: Create reusable fixtures for common account types (checking, savings)
- **Coverage**: Focus on service and schema validation tests for new logic

---

### 3.2 Detailed File Specifications

#### `alembic/versions/{timestamp}_convert_account_type_to_fk.py`

**Purpose**: Database migration script to convert account_type from enum to foreign key.

**Implementation**:

```python
"""Convert account_type from enum to foreign key

Revision ID: {generated}
Revises: a2abdbb7e119
Create Date: {timestamp}

This migration:
1. Adds account_type_id UUID column (nullable initially)
2. Creates foreign key constraint to account_types.id
3. Creates index on account_type_id
4. Migrates data: enum value → account_type.key mapping
5. Makes account_type_id NOT NULL
6. Drops old account_type enum column
7. Drops AccountType enum type
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '{generated}'
down_revision: Union[str, None] = 'a2abdbb7e119'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Step 1: Add account_type_id column (nullable initially for migration)
    op.add_column(
        'accounts',
        sa.Column(
            'account_type_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Foreign key to account_types table'
        )
    )

    # Step 2: Create foreign key constraint (with ON DELETE RESTRICT)
    op.create_foreign_key(
        'fk_accounts_account_type_id',
        'accounts',
        'account_types',
        ['account_type_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # Step 3: Create index on account_type_id for query performance
    op.create_index(
        'ix_accounts_account_type_id',
        'accounts',
        ['account_type_id']
    )

    # Step 4: Migrate data - map enum values to account_types records
    # This SQL maps:
    #   'checking' → account_types where key='checking' AND is_system=true
    #   'savings' → account_types where key='savings' AND is_system=true
    #   'investment' → account_types where key='investment' AND is_system=true
    #   'other' → account_types where key='other' AND is_system=true
    op.execute("""
        UPDATE accounts
        SET account_type_id = (
            SELECT id
            FROM account_types
            WHERE key = accounts.account_type::text
              AND is_system = true
            LIMIT 1
        )
        WHERE account_type_id IS NULL;
    """)

    # Step 5: Verify all accounts have account_type_id set
    # This will fail the migration if any accounts still have NULL
    op.execute("""
        DO $$
        DECLARE
            null_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO null_count
            FROM accounts
            WHERE account_type_id IS NULL;

            IF null_count > 0 THEN
                RAISE EXCEPTION 'Migration failed: % accounts have NULL account_type_id', null_count;
            END IF;
        END $$;
    """)

    # Step 6: Make account_type_id NOT NULL (now that all data is migrated)
    op.alter_column(
        'accounts',
        'account_type_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False
    )

    # Step 7: Drop old account_type enum column
    op.drop_column('accounts', 'account_type')

    # Step 8: Drop AccountType enum type from database
    # Note: This will fail if any other tables/columns use this enum
    op.execute("DROP TYPE IF EXISTS accounttype")


def downgrade() -> None:
    """Downgrade database schema (rollback)."""

    # Step 1: Recreate AccountType enum
    op.execute("""
        CREATE TYPE accounttype AS ENUM (
            'checking',
            'savings',
            'investment',
            'other'
        )
    """)

    # Step 2: Add account_type enum column (nullable initially)
    op.add_column(
        'accounts',
        sa.Column(
            'account_type',
            postgresql.ENUM('checking', 'savings', 'investment', 'other', name='accounttype'),
            nullable=True
        )
    )

    # Step 3: Restore data - map account_type.key back to enum
    op.execute("""
        UPDATE accounts
        SET account_type = account_types.key::accounttype
        FROM account_types
        WHERE accounts.account_type_id = account_types.id;
    """)

    # Step 4: Make account_type NOT NULL
    op.alter_column(
        'accounts',
        'account_type',
        existing_type=postgresql.ENUM('checking', 'savings', 'investment', 'other', name='accounttype'),
        nullable=False
    )

    # Step 5: Drop account_type_id foreign key
    op.drop_constraint('fk_accounts_account_type_id', 'accounts', type_='foreignkey')

    # Step 6: Drop account_type_id index
    op.drop_index('ix_accounts_account_type_id', 'accounts')

    # Step 7: Drop account_type_id column
    op.drop_column('accounts', 'account_type_id')
```

**Edge Cases**:
- If no system account types exist, migration fails (expected - Feature 1.2 must be complete)
- If any account_type enum value doesn't match a system account type key, UPDATE sets NULL (then fails on verification)
- Downgrade restores enum but loses any non-system account type associations

**Tests**:
- Run migration on empty database → succeeds
- Run migration with accounts → all accounts migrated correctly
- Verify enum column and type removed
- Test downgrade restores previous state

---

## Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Database Migration & Model Updates (Priority: P0, Size: L)

**Goal**: Successfully migrate the database schema and update core models without breaking existing functionality.

**Scope**:
- ✅ Include: Database migration script, Account model changes, enum removal
- ❌ Exclude: API endpoint changes (old enum still accepted temporarily), full test updates

**Components to Implement**:
- [x] Component 1: Database Migration script
- [x] Component 2: Account Model changes (enum → FK)
- [ ] Component 2: Remove AccountType enum from enums.py

**Detailed Tasks**:

1. [ ] **Create migration script**
   - Generate migration: `uv run alembic revision --autogenerate -m "convert account type to fk"`
   - Review auto-generated migration carefully (Alembic may miss steps)
   - Manually adjust migration script using template above
   - Add data migration SQL (UPDATE statement)
   - Add verification step (check for NULL account_type_id)
   - Add downgrade logic for rollback capability
   - Test: `uv run alembic upgrade head` on development database
   - Test: `uv run alembic downgrade -1` to verify rollback works

2. [ ] **Update Account model** (`src/models/account.py`)
   - Import AccountType model: `from src.models.account_type import AccountType`
   - Remove enum import: Delete `from src.models.enums import AccountType`
   - Remove old field: Delete `account_type: Mapped[AccountType]` field
   - Add FK field: `account_type_id: Mapped[uuid.UUID]` with FK constraint
   - Add relationship: `account_type: Mapped["AccountType"]` with `lazy="selectin"`
   - Update docstring to reflect new field
   - Update `__repr__` to use `self.account_type.key`
   - Verify: Run `uv run mypy src/models/account.py`

3. [ ] **Remove AccountType enum** (`src/models/enums.py`)
   - Delete entire `AccountType` class (lines 17-63)
   - Keep other enums: PermissionLevel, TransactionType, InstitutionType
   - Search codebase for `AccountType` enum imports: `grep -r "from src.models.enums import AccountType"`
   - Update any remaining imports to use AccountType model instead
   - Verify: Run `uv run python -c "from src.models.enums import AccountType"` → should fail

4. [ ] **Test migration on development database**
   - Create test accounts with all 4 enum values (checking, savings, investment, other)
   - Count accounts: `SELECT count(*), account_type FROM accounts GROUP BY account_type;`
   - Run migration: `uv run alembic upgrade head`
   - Verify: `SELECT count(*), at.key FROM accounts a JOIN account_types at ON a.account_type_id = at.id GROUP BY at.key;`
   - Verify counts match pre/post migration
   - Verify enum column dropped: `\d accounts` in psql
   - Verify enum type dropped: `\dT` in psql (AccountType should not appear)

5. [ ] **Test rollback**
   - Downgrade: `uv run alembic downgrade -1`
   - Verify enum column restored
   - Verify data intact
   - Re-upgrade: `uv run alembic upgrade head`

**Dependencies**:
- Requires: Feature 1.2 complete (account_types table exists and seeded)
- Blocks: All other phases (cannot update API without model changes)

**Validation Criteria** (Phase complete when):
- [ ] Migration script runs without errors
- [ ] All accounts have non-NULL account_type_id
- [ ] Enum column removed from accounts table
- [ ] AccountType enum type removed from PostgreSQL
- [ ] Account model imports AccountType model (not enum)
- [ ] Account model has account_type_id FK field
- [ ] Account model has account_type relationship
- [ ] Downgrade restores previous state
- [ ] Code passes type checking (`uv run mypy src/`)

**Risk Factors**:
- **Risk**: Migration fails due to missing account types
  - **Mitigation**: Pre-flight check in migration script; fail loudly if system types missing
- **Risk**: Enum values don't match account_type keys
  - **Mitigation**: Use exact keys from Feature 1.2 (checking, savings, investment, other)
- **Risk**: Large dataset causes migration timeout
  - **Mitigation**: Test migration on production data copy; consider batched updates if >100k accounts

**Estimated Effort**: 2 days (16 hours)

---

#### Phase 2: Schema & Service Layer Updates (Priority: P0, Size: M)

**Goal**: Update Pydantic schemas and service layer business logic to accept/validate account_type_id.

**Scope**:
- ✅ Include: Schema updates, service method updates, validation logic
- ❌ Exclude: API route changes (still using old parameter names), comprehensive tests

**Components to Implement**:
- [x] Component 3: Account Schema changes
- [x] Component 4: Account Service updates

**Detailed Tasks**:

1. [ ] **Update AccountCreate schema** (`src/schemas/account.py`)
   - Remove import: `from src.models.enums import AccountType`
   - Remove field: `account_type: AccountType`
   - Add field: `account_type_id: uuid.UUID` with description
   - Add validator: `validate_account_type_id()` to reject nil UUID
   - Update docstring examples
   - Test: Create AccountCreate instance with UUID → succeeds
   - Test: Create AccountCreate with nil UUID → fails with validation error

2. [ ] **Update AccountUpdate schema** (`src/schemas/account.py`)
   - Add field: `account_type_id: uuid.UUID | None = None`
   - Add validator: `validate_account_type_id()` (same as Create)
   - Update docstring

3. [ ] **Update AccountResponse schema** (`src/schemas/account.py`)
   - Import: `from src.schemas.account_type import AccountTypeListItem`
   - Add field: `account_type_id: uuid.UUID`
   - Add field: `account_type: AccountTypeListItem` (nested object)
   - Remove field: `account_type: AccountType` (enum)
   - Test: Serialize Account model → includes nested account_type object

4. [ ] **Update AccountListItem schema** (`src/schemas/account.py`)
   - Same changes as AccountResponse
   - Add `account_type_id` and `account_type` fields
   - Remove enum field

5. [ ] **Update AccountFilterParams schema** (`src/schemas/account.py`)
   - Replace `account_type: AccountType | None` with `account_type_id: uuid.UUID | None`

6. [ ] **Update AccountService.create_account()** (`src/services/account_service.py`)
   - Add import: `from src.repositories.account_type_repository import AccountTypeRepository`
   - Add to `__init__`: `self.account_type_repo = AccountTypeRepository(session)`
   - Update signature: `account_type_id: uuid.UUID` instead of `account_type: AccountType`
   - Add validation logic (before financial institution check):
     - Fetch account type: `account_type = await self.account_type_repo.get_by_id(account_type_id)`
     - Validate exists: raise NotFoundError if None
     - Validate active: raise ValidationError if not is_active
     - Validate access: raise AuthorizationError if custom type and not owned by user
   - Update Account creation: `account_type_id=account_type_id`
   - Test: Create account with valid system type → succeeds
   - Test: Create account with invalid type ID → NotFoundError
   - Test: Create account with inactive type → ValidationError
   - Test: Create account with other user's custom type → AuthorizationError

7. [ ] **Update AccountService.update_account()** (`src/services/account_service.py`)
   - Add parameter: `account_type_id: uuid.UUID | None = None`
   - Add validation block (same as create_account)
   - Update account: `account.account_type_id = account_type_id` if provided
   - Test: Update account type → succeeds with valid type

8. [ ] **Update AccountService.list_accounts()** (`src/services/account_service.py`)
   - Update signature: `account_type_id: uuid.UUID | None` instead of `account_type: AccountType | None`
   - Pass to repository: `account_type_id=account_type_id`

**Dependencies**:
- Requires: Phase 1 complete (models updated)
- Blocks: Phase 3 (API routes need service methods updated)

**Validation Criteria** (Phase complete when):
- [ ] All schemas accept/return account_type_id UUID
- [ ] AccountResponse includes nested account_type object
- [ ] All validators pass mypy type checking
- [ ] Service methods validate account type exists, is active, is accessible
- [ ] Service methods raise appropriate errors for invalid types
- [ ] Unit tests pass for schema validation
- [ ] Unit tests pass for service validation logic

**Risk Factors**:
- **Risk**: Validation logic is complex and error-prone
  - **Mitigation**: Extract to helper method `_validate_account_type_access()` in service
- **Risk**: Nested object serialization fails
  - **Mitigation**: Test with actual ORM objects; verify `model_config = {"from_attributes": True}`

**Estimated Effort**: 1.5 days (12 hours)

---

#### Phase 3: API Routes & Repository Updates (Priority: P0, Size: M)

**Goal**: Update API routes to use new field names and update repository queries to filter by UUID.

**Scope**:
- ✅ Include: Route parameter updates, OpenAPI docs updates, repository query updates
- ❌ Exclude: Comprehensive end-to-end tests (deferred to Phase 4)

**Components to Implement**:
- [x] Component 5: Account Repository updates
- [x] Component 6: API Route updates

**Detailed Tasks**:

1. [ ] **Update AccountRepository.get_accounts_by_user()** (`src/repositories/account_repository.py`)
   - Update signature: `account_type_id: uuid.UUID | None` instead of `account_type: AccountType | None`
   - Update query: `query = query.where(Account.account_type_id == account_type_id)` if not None
   - Test: Filter by account_type_id → returns correct accounts
   - Test: Verify only 2 queries issued (accounts + account_types via selectin)

2. [ ] **Update create_account route** (`src/api/routes/accounts.py`)
   - Remove import: `from src.models.enums import AccountType`
   - Update service call: `account_type_id=account_data.account_type_id`
   - Update docstring: Reflect new field name
   - Update example request: Show `account_type_id` instead of `account_type`
   - Update example response: Show nested `account_type` object
   - Test: POST /accounts with account_type_id → 201 with nested account_type

3. [ ] **Update update_account route** (`src/api/routes/accounts.py`)
   - Update service call: Add `account_type_id=update_data.account_type_id`
   - Update docstring: Reflect new optional field
   - Test: PATCH /accounts/{id} with account_type_id → 200

4. [ ] **Update list_accounts route** (`src/api/routes/accounts.py`)
   - Update query parameter: `account_type_id: uuid.UUID | None = Query(None, ...)`
   - Update service call: `account_type_id=account_type_id`
   - Update docstring: Reflect new filter parameter
   - Update example response: Show nested `account_type` object
   - Test: GET /accounts?account_type_id=uuid → filtered results

5. [ ] **Update get_account route** (`src/api/routes/accounts.py`)
   - No parameter changes needed
   - Update example response: Show nested `account_type` object
   - Test: GET /accounts/{id} → includes account_type details

6. [ ] **Verify OpenAPI schema** (automatic via FastAPI)
   - Visit /docs in browser
   - Verify account_type_id shows as UUID in request schemas
   - Verify account_type shows as nested object in response schemas
   - Verify examples are correct

**Dependencies**:
- Requires: Phase 2 complete (schemas and services updated)
- Blocks: Phase 4 (testing phase)

**Validation Criteria** (Phase complete when):
- [ ] All routes accept account_type_id instead of account_type enum
- [ ] All route docstrings updated
- [ ] All example requests/responses updated
- [ ] Repository filters by account_type_id UUID
- [ ] OpenAPI schema shows correct types (UUID, nested object)
- [ ] Manual testing via /docs succeeds for all endpoints

**Risk Factors**:
- **Risk**: Query parameter type conversion fails
  - **Mitigation**: FastAPI handles UUID conversion automatically; test with invalid UUID
- **Risk**: Nested object not serialized in response
  - **Mitigation**: Test with actual database queries; verify relationship loaded

**Estimated Effort**: 1 day (8 hours)

---

#### Phase 4: Comprehensive Testing & Documentation (Priority: P1, Size: M)

**Goal**: Achieve ≥80% test coverage, create migration-specific tests, and document breaking changes for API clients.

**Scope**:
- ✅ Include: Test updates, migration tests, API migration guide, documentation
- ❌ Exclude: None (this is the final phase)

**Components to Implement**:
- [x] Component 7: Testing updates

**Detailed Tasks**:

1. [ ] **Update integration tests** (`tests/integration/test_account_routes.py`)
   - Create fixtures: `checking_account_type`, `savings_account_type`
   - Update all test_create_account* tests to use account_type_id
   - Update all test_update_account* tests to use account_type_id
   - Update all test_list_accounts* tests to verify nested account_type
   - Update all test_filter_accounts* tests to filter by account_type_id
   - Add test: Create account with other user's custom type → 403
   - Add test: Create account with inactive type → 400
   - Add test: Create account with non-existent type → 404
   - Run: `uv run pytest tests/integration/test_account_routes.py -v`

2. [ ] **Update unit tests** (`tests/unit/test_account_service.py`)
   - Create fixture: `checking_account_type`
   - Update all create_account tests to use account_type_id
   - Update all update_account tests to use account_type_id
   - Add test: Validate account type exists (service layer)
   - Add test: Validate account type is active (service layer)
   - Add test: Validate account type access control (service layer)
   - Run: `uv run pytest tests/unit/test_account_service.py -v`

3. [ ] **Update schema tests** (`tests/unit/test_account_schemas.py`)
   - Update AccountCreate validation tests for UUID field
   - Add test: AccountCreate rejects nil UUID
   - Add test: AccountCreate requires account_type_id (not optional)
   - Update AccountResponse tests to verify nested account_type
   - Run: `uv run pytest tests/unit/test_account_schemas.py -v`

4. [ ] **Create migration tests** (`tests/integration/test_account_migration.py`)
   - Test: Migration runs on empty database
   - Test: Migration runs with existing accounts (all 4 enum values)
   - Test: All accounts have account_type_id after migration
   - Test: Mapping is correct (enum → account_type.key)
   - Test: Enum column removed
   - Test: Enum type removed from database
   - Test: Downgrade restores previous state
   - Run: `uv run pytest tests/integration/test_account_migration.py -v`

5. [ ] **Run full test suite with coverage**
   - Run: `uv run pytest tests/ --cov=src --cov-report=term-missing`
   - Verify: Coverage ≥80% for all modified files
   - Fix: Any failing tests
   - Document: Any test exclusions or known issues

6. [ ] **Create API migration guide**
   - Document: Breaking changes in `/docs/api-migration-account-types.md`
   - Provide: Mapping from enum strings to account_type_id UUIDs
   - Example: "checking" → GET /api/v1/account-types?key=checking → use returned ID
   - Code examples: Before/after for create, update, list operations
   - Timeline: Deprecation schedule (if phased rollout)

7. [ ] **Update API documentation**
   - Update: CLAUDE.md with new field structure
   - Update: Any README or wiki pages referencing account creation
   - Update: Postman collection (if exists) with new field names

8. [ ] **Run code quality checks**
   - Format: `uv run ruff format .`
   - Lint: `uv run ruff check --fix .`
   - Type check: `uv run mypy src/`
   - Verify: No errors or warnings

**Dependencies**:
- Requires: Phase 3 complete (all implementation done)
- Blocks: None (final phase)

**Validation Criteria** (Phase complete when):
- [ ] All tests pass: `uv run pytest tests/`
- [ ] Test coverage ≥80%: `uv run pytest --cov=src --cov-report=term-missing`
- [ ] Migration tests pass and verify data integrity
- [ ] API migration guide created and reviewed
- [ ] Code quality checks pass (ruff, mypy)
- [ ] Documentation updated
- [ ] No regressions in existing functionality

**Risk Factors**:
- **Risk**: Tests reveal edge cases not considered in implementation
  - **Mitigation**: Allocate time for bug fixes in this phase (buffer time)
- **Risk**: Coverage target not met
  - **Mitigation**: Focus on service and schema validation; acceptable to skip some trivial property tests

**Estimated Effort**: 1.5 days (12 hours)

---

### 4.2 Implementation Sequence

```
Phase 1: Database & Models (P0, 2 days)
         └─ Migration script
         └─ Model updates
         └─ Enum removal
              ↓
Phase 2: Schemas & Services (P0, 1.5 days)
         └─ Schema updates
         └─ Service validation logic
              ↓
Phase 3: API & Repository (P0, 1 day)
         └─ Route updates
         └─ Repository queries
              ↓
Phase 4: Testing & Docs (P1, 1.5 days)
         └─ Test updates
         └─ Migration tests
         └─ API migration guide
```

**Rationale for ordering**:
- **Phase 1 first** because: Database schema must change before any code can use new FK structure
- **Phase 2 depends on Phase 1** because: Cannot validate UUIDs or FK relationships without database changes
- **Phase 3 depends on Phase 2** because: Routes depend on schemas and service methods
- **Phase 4 last** because: Cannot test thoroughly until all implementation is complete

**Critical Path**: Phases 1 → 2 → 3 are sequential (cannot parallelize)

**Quick Wins**:
- After Phase 1: Database is migrated, can verify data integrity immediately
- After Phase 2: Service layer is feature-complete, can do manual API testing with tools like Postman

---

## Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. Foreign key relationship is the standard database pattern for this requirement. No over-engineering.

- [x] **Have we avoided premature optimization?**
  - Yes. Using standard SQLAlchemy patterns (`lazy="selectin"`). Not implementing caching or complex query optimization prematurely.

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. Follows existing FK pattern used by `financial_institution_id`. Uses same repository/service/schema layers.

- [x] **Can we deliver value in smaller increments?**
  - Partially. Migration could be done in phases, but for 4 enum values, full migration is simpler and safer than phased approach.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. The requirement is explicit: enable custom account types beyond 4 hardcoded values. This solution delivers exactly that.

### Alternatives Considered

**Alternative 1: Keep enum + add custom_account_type_name field**
- **Description**: Keep existing enum for system types, add optional text field for custom types
- **Why rejected**:
  - Inconsistent data model (two fields for one concept)
  - No metadata support (icons, descriptions)
  - Harder to query and filter
  - Violates normalization principles

**Alternative 2: Use VARCHAR instead of foreign key**
- **Description**: Replace enum with VARCHAR field, store account type name directly
- **Why rejected**:
  - No referential integrity (typos, inconsistencies)
  - No centralized metadata management
  - Duplicate data across accounts
  - Cannot share custom types across accounts easily

**Alternative 3: Keep enum + add polymorphic account_type_id**
- **Description**: Keep enum for backward compatibility, add optional FK for custom types
- **Why rejected**:
  - Complex dual-field logic
  - Confusing for developers (which field to use?)
  - Technical debt accumulates
  - Migration pain delayed, not eliminated

**Rationale**: The proposed foreign key approach is the standard, clean database design pattern for this requirement. It's the simplest solution that solves the problem completely and aligns with existing patterns in the codebase.

---

## References & Related Documents

### Internal Documentation
- **Feature 1.2 Spec**: `.features/descriptions/feat-01-account-types-master-data.md` (dependency)
- **Project CLAUDE.md**: Architecture guidelines and standards
- **Account Model**: `src/models/account.py` (current implementation)
- **AccountType Model**: `src/models/account_type.py` (Feature 1.2)

### External Resources

#### Database Migration Best Practices
- [Migrating PostgreSQL Enum using SQLAlchemy and Alembic](https://code.keplergrp.com/blog/migrating-postgresql-enum-sqlalchemy-alembic) - Comprehensive guide on enum migrations
- [Simplifying PostgreSQL enum migrations with SQLAlchemy and alembic-enums](https://roman.pt/posts/alembic-enums/) - Alternative approaches using helper libraries
- [Alembic Auto Generating Migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) - Official documentation on autogenerate limitations

#### SQLAlchemy & Async Patterns
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) - Official docs for ORM patterns
- [SQLAlchemy Async ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Async/await patterns and selectin loading
- [Foreign Key Constraints in PostgreSQL](https://www.postgresql.org/docs/16/ddl-constraints.html#DDL-CONSTRAINTS-FK) - ON DELETE options and behavior

#### Pydantic & FastAPI
- [Pydantic v2 Documentation](https://docs.pydantic.dev/2.0/) - Schema validation and serialization
- [Pydantic Enums](https://docs.pydantic.dev/2.0/usage/types/enums/) - How Pydantic handles enums
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) - Dependency injection patterns
- [Proper way to use Enum with Pydantic & FastAPI](https://github.com/pydantic/pydantic/discussions/4967) - Community best practices

#### Migration Strategy
- [Zero-Downtime Database Migrations](https://www.braintreepayments.com/blog/safe-operations-for-high-volume-postgresql/) - Strategies for production migrations
- [PostgreSQL ALTER TYPE Limitations](https://www.postgresql.org/docs/16/sql-altertype.html) - Why we drop enum instead of alter

### Competitor Analysis
Not applicable for this internal database migration feature.

### Related Design Documents
- **Account Types API Design**: Already implemented in Feature 1.2
- **Authentication & Authorization**: Existing patterns for permission checks

---

## Appendix: Migration Safety Checklist

Before deploying this migration to production:

- [ ] **Backup database**: Full backup before running migration
- [ ] **Test on production copy**: Run migration on copy of production data, verify results
- [ ] **Measure migration time**: Time the migration on production copy to estimate downtime
- [ ] **Check for locks**: Verify migration doesn't hold exclusive locks that block reads/writes
- [ ] **Plan downtime**: Schedule maintenance window if migration takes >5 minutes
- [ ] **Communication**: Notify frontend team of deployment schedule (breaking changes)
- [ ] **Rollback plan**: Test downgrade migration, ensure it works
- [ ] **Monitoring**: Set up alerts for failed account creation after migration
- [ ] **Staged rollout**: Consider deploying to staging environment first (if exists)
- [ ] **Feature flag**: Consider feature flag to toggle new/old API (if phased rollout needed)

---

## Implementation Notes

### Critical Considerations

1. **Breaking Change Coordination**: This is a **breaking API change**. Frontend and mobile clients **must** update simultaneously. Schedule deployment carefully.

2. **Migration Testing**: The data migration SQL is critical. Test extensively on a copy of production data before deploying.

3. **Performance**: Migration performance depends on table size. For <10k accounts, migration is instant. For >100k accounts, consider batched updates.

4. **Rollback Window**: Keep the downgrade migration tested and ready for at least 2 weeks post-deployment.

5. **Account Type Seeding**: This migration assumes system account types (checking, savings, investment, other) exist in the `account_types` table. Verify this before running migration.

### Development Tips

- **Use Type Checking**: Run `uv run mypy src/` frequently during development to catch type errors early
- **Test Incrementally**: Don't wait until the end; test each component as you build it
- **Check N+1 Queries**: Use logging or query monitoring to verify `lazy="selectin"` prevents N+1 queries
- **Review Auto-Generated Migration**: Alembic's autogenerate is helpful but not perfect; always review and adjust

### Success Metrics

After implementation, verify:
- ✅ All accounts have valid account_type_id references
- ✅ No NULL account_type_id values
- ✅ Enum column and type removed from database
- ✅ API endpoints accept UUID instead of enum string
- ✅ API responses include nested account_type object
- ✅ Test coverage ≥80%
- ✅ No performance regression in account listing queries
- ✅ API clients successfully migrated to new format

---

**End of Implementation Plan**
