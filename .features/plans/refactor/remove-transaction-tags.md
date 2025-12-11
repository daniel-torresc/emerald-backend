# Implementation Plan: Remove Transaction Tags Feature

## 1. Executive Summary

This plan outlines the complete removal of the transaction tags feature from the Emerald Finance Platform backend. Transaction tags were originally implemented to allow users to categorize transactions with custom labels (e.g., "business", "tax-deductible"), but this functionality is being deprecated in favor of a different categorization approach.

The removal involves eliminating the `TransactionTag` database model, all associated API endpoints (`POST /tags`, `DELETE /tags/{tag}`), service layer logic, repository operations, and comprehensive test coverage. This is a substantial refactoring that touches multiple architectural layers—database schema, models, repositories, services, schemas, and API routes—requiring careful orchestration to maintain system integrity.

**Primary Objectives:**
- Remove all transaction tag functionality from the codebase
- Eliminate the `transaction_tags` database table via migration
- Ensure zero orphaned code, imports, or references remain
- Maintain test coverage (80% minimum) after removal
- Preserve audit trail and data integrity for existing transactions

**Expected Outcomes:**
- Cleaner, more maintainable codebase with reduced complexity
- Removal of ~1,000+ lines of code across models, repositories, services, tests
- Simplified transaction creation and management workflows
- Database schema reduced by one table and associated indexes
- All tests passing with no regressions

**Success Criteria:**
- All code quality checks pass (Ruff, MyPy)
- All existing tests pass (excluding removed tag tests)
- Test coverage remains ≥80%
- Database migration executes successfully
- Zero references to "TransactionTag" or tag-related code remain
- Production deployment completes without downtime

---

## 2. Technical Architecture

### 2.1 System Design Overview

The transaction tags feature is currently integrated across all architectural layers following the project's strict 3-layer architecture:

```
┌──────────────────────────────────────────────────────┐
│  API Layer                                           │
│  - POST /transactions/{id}/tags      (add tag)       │
│  - DELETE /transactions/{id}/tags/{tag} (remove tag) │
│  - tags field in create/response schemas             │
└──────────────────────────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│  Service Layer                                       │
│  - TransactionService.add_tag()                      │
│  - TransactionService.remove_tag()                   │
│  - Tag creation during transaction creation          │
└──────────────────────────────────────────────────────┐
                        ▼
┌──────────────────────────────────────────────────────┐
│  Repository Layer                                    │
│  - TransactionTagRepository (entire class)           │
│  - Methods: add_tag, remove_tag, get_tags, etc.      │
└──────────────────────────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│  Database Layer                                      │
│  - transaction_tags table                            │
│  - Relationship: Transaction.tags → TransactionTag   │
└──────────────────────────────────────────────────────┘
```

**Removal Strategy:**
We'll use a **bottom-up approach**, removing code starting from the database layer and working upward to the API layer. This ensures that each layer's dependencies are cleaned before the dependent code is removed, minimizing broken references during the process.

**Key Components Affected:**
- **1 database table**: `transaction_tags`
- **2 API endpoints**: Add tag, Remove tag
- **1 complete repository**: `TransactionTagRepository` (242 lines)
- **2 service methods**: `add_tag()`, `remove_tag()`
- **4 Pydantic schemas**: `TransactionCreate`, `TransactionResponse`, `TransactionListItem`, `TagRequest`
- **3 test files**: Unit tests for repository, service, and integration tests for API

**Data Flow Impact:**
Currently, when a transaction is created with tags:
1. API receives `tags: ["food", "groceries"]` in request body
2. Service creates transaction, then iterates tags and calls `tag_repo.add_tag()`
3. Repository inserts records into `transaction_tags` table
4. Response includes tags converted from `TransactionTag` objects to strings

After removal, transactions will no longer accept or return tag data.

### 2.2 Technology Decisions

**[Alembic Migration Strategy]**
- **Purpose**: Safely remove the `transaction_tags` table from production database
- **Why this choice**: Alembic is the project's standard migration tool and provides version-controlled schema changes with rollback capability
- **Version**: Alembic 1.13+ (current project version)
- **Alternatives considered**:
  - Direct SQL execution: Rejected due to lack of version control and rollback
  - Manual table drop: Rejected due to production safety concerns

**[Migration Approach: Two-Phase Removal]**
- **Purpose**: Enable zero-downtime deployment with rollback capability
- **Why this choice**: Best practice for production systems per [Sling Academy SQLAlchemy production updates](https://www.slingacademy.com/article/sqlalchemy-how-to-safely-update-a-model-in-production/)
- **Approach**:
  - **Phase 1 Migration**: Drop `transaction_tags` table
  - **Code Deployment**: Deploy code with tag references removed (compatible with schema before/after migration)
  - **Phase 2 Verification**: Confirm no errors, validate rollback procedures
- **Alternatives considered**:
  - Single-phase atomic change: Rejected due to deployment risk if code and migration aren't perfectly synchronized
  - Blue-green deployment: Overkill for this scope

**[Dead Code Detection Tool: Manual Review + Grep]**
- **Purpose**: Ensure zero orphaned tag references remain
- **Why this choice**: Lightweight, no additional dependencies, project uses `uv` only
- **Approach**: Systematic grep for "tag", "TransactionTag", "TagRequest" patterns
- **Alternatives considered**:
  - Vulture (Python dead code detector): Additional dependency, may have false positives
  - Manual code review only: Too error-prone for comprehensive verification

**[Test Strategy: Remove vs. Modify]**
- **Purpose**: Decide whether to remove tag tests entirely or modify them
- **Why this choice**: Remove entirely since tag functionality is being eliminated
- **Rationale**:
  - No need to test non-existent functionality
  - Reduces test suite maintenance burden
  - Preserves overall test coverage via remaining transaction tests
- **Alternatives considered**:
  - Keep test structure, assert tags=None: Unnecessarily clutters test suite

### 2.3 File Structure

The transaction tags feature spans the following directory structure (files marked with ❌ will be **deleted**, 🔧 will be **modified**):

```
src/
├── models/
│   └── transaction.py                                    🔧 Remove TransactionTag class, tags relationship
├── repositories/
│   ├── transaction_tag_repository.py                     ❌ DELETE ENTIRE FILE
│   └── transaction_repository.py                         🔧 Remove TransactionTag import, tags refresh
├── services/
│   └── transaction_service.py                            🔧 Remove tag methods, tag creation logic
├── schemas/
│   └── transaction.py                                    🔧 Remove tags fields, TagRequest class
└── api/
    └── routes/
        └── transactions.py                               🔧 Remove tag endpoints

alembic/
└── versions/
    ├── 4aabd1426c98_initial_schema.py                    🔧 Remove transaction_tags table creation
    └── XXXXXXXXXX_remove_transaction_tags.py             ✨ NEW MIGRATION

tests/
├── unit/
│   ├── repositories/
│   │   └── test_transaction_tag_repository.py            ❌ DELETE ENTIRE FILE
│   └── services/
│       └── test_transaction_service.py                   🔧 Remove tag test methods
├── integration/
│   └── test_transaction_api.py                           🔧 Remove tag endpoint tests
└── e2e/
    └── test_user_journey.py                              🔧 Remove tag-related assertions (if any)
```

**Directory Purpose Explanations:**

- **`src/models/`**: ORM models representing database tables. `transaction.py` contains both `Transaction` and `TransactionTag` models.
- **`src/repositories/`**: Data access layer. `transaction_tag_repository.py` is dedicated to tag CRUD operations.
- **`src/services/`**: Business logic layer. `transaction_service.py` orchestrates tag creation/management.
- **`src/schemas/`**: Pydantic validation schemas for API requests/responses.
- **`src/api/routes/`**: FastAPI endpoint definitions.
- **`alembic/versions/`**: Database migration scripts.
- **`tests/`**: Test suite organized by test type (unit, integration, e2e).

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Database Layer - Remove TransactionTag Model

**Files Involved**:
- `src/models/transaction.py`
- `alembic/versions/XXXXXXXXXX_remove_transaction_tags.py` (new migration)
- `alembic/versions/4aabd1426c98_initial_schema.py` (existing migration, optional cleanup)

**Purpose**: Eliminate the `TransactionTag` ORM model and its relationship with `Transaction`, and create a migration to drop the `transaction_tags` table from the database.

**Implementation Requirements**:

1. **Core Logic**:
   - **Step 1**: Remove the entire `TransactionTag` class definition from `transaction.py` (lines 329-406)
     - Includes: model fields, relationships, constraints, indexes, `__repr__` method
   - **Step 2**: Remove the `tags` relationship from the `Transaction` class (lines 287-293)
     - This is a SQLAlchemy `relationship()` that references `TransactionTag` with cascade delete
   - **Step 3**: Create new Alembic migration to drop the `transaction_tags` table
     - Use `alembic revision -m "remove transaction tags table"`
     - Migration must drop table, constraints, and indexes in correct order

2. **Data Handling**:
   - **Input validation**: N/A (removal only)
   - **Migration output**: SQL to drop table `transaction_tags` and associated indexes/constraints
   - **State management**:
     - Migration must be **idempotent** (safe to run multiple times)
     - Downgrade function should recreate table (for rollback capability)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Table already dropped (migration idempotency)
     - Solution: Use `DROP TABLE IF EXISTS`
   - [ ] Handle case: Foreign key constraints exist
     - Solution: Drop constraints before dropping table (Alembic auto-handles this)
   - [ ] Handle case: Rollback needed after deployment
     - Solution: Implement complete `downgrade()` function to recreate table

4. **Dependencies**:
   - **Internal**: None (this is the base layer)
   - **External**: Alembic, SQLAlchemy

5. **Testing Requirements**:
   - [ ] Unit test: Migration applies cleanly on fresh database
   - [ ] Unit test: Migration is idempotent (can run twice without error)
   - [ ] Unit test: Downgrade recreates table structure
   - [ ] Integration test: Transactions can be created without tags field
   - [ ] Integration test: Existing transactions remain intact after migration

**Acceptance Criteria**:
- [ ] `TransactionTag` class completely removed from `transaction.py`
- [ ] `Transaction.tags` relationship removed
- [ ] Migration successfully drops `transaction_tags` table
- [ ] Migration can be rolled back (downgrade function works)
- [ ] Zero references to `TransactionTag` in models directory
- [ ] MyPy type checking passes

**Implementation Notes**:
- **DO NOT** modify the initial migration (`4aabd1426c98_initial_schema.py`) in a way that breaks its ability to create a database from scratch. If removing table creation there, ensure the downgrade path is preserved for historical accuracy.
- The `transaction_tags` table has foreign key to `transactions` table with CASCADE delete, so orphaned tags shouldn't exist, but verify before dropping.
- According to [Alembic best practices](https://alembic.sqlalchemy.org/en/latest/tutorial.html), always test migrations on a staging database before production.

---

#### Component: Repository Layer - Remove TransactionTagRepository

**Files Involved**:
- `src/repositories/transaction_tag_repository.py` (DELETE)
- `src/repositories/transaction_repository.py` (modify)

**Purpose**: Eliminate the dedicated repository for tag operations and clean up tag-related code from the transaction repository.

**Implementation Requirements**:

1. **Core Logic**:
   - **Step 1**: Delete entire file `transaction_tag_repository.py` (242 lines)
     - Contains: `TransactionTagRepository` class with 6 methods
   - **Step 2**: Remove `TransactionTag` import from `transaction_repository.py` (line 22)
   - **Step 3**: Remove `tags` from eager loading in `create()` method (lines 79-82)
     - Current code: `await session.refresh(transaction, ["tags", ...])`
     - New code: `await session.refresh(transaction, [...])` (without tags)

2. **Data Handling**:
   - **Input validation**: N/A (removal only)
   - **Output format**: Repository methods return `Transaction` objects without tags relationship
   - **State management**: No state changes needed

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Other repositories import `TransactionTagRepository`
     - Solution: Remove those imports (verify with grep)
   - [ ] Validate: `TransactionRepository.create()` still works without tags refresh
     - Solution: Test transaction creation after removal

4. **Dependencies**:
   - **Internal**: Used by `TransactionService` (must be removed there first)
   - **External**: None

5. **Testing Requirements**:
   - [ ] Unit test: `TransactionRepository.create()` works without tags refresh
   - [ ] Unit test: Transactions can be queried without tag relationship
   - [ ] Integration test: Transaction creation API works end-to-end

**Acceptance Criteria**:
- [ ] `transaction_tag_repository.py` file deleted
- [ ] No imports of `TransactionTagRepository` anywhere in codebase
- [ ] `TransactionRepository` has no references to `TransactionTag` or `tags`
- [ ] All transaction repository tests pass
- [ ] Grep shows zero matches for "TransactionTagRepository"

**Implementation Notes**:
- The `transaction_repository.py` file has minimal tag coupling (only import and one refresh line), making removal straightforward.
- After deletion, verify with: `grep -r "TransactionTagRepository" src/` should return zero results.
- Per [dead code elimination best practices](https://medium.com/beyond-the-code-by-typo/how-to-identify-and-remove-dead-code-8283b0bf05a3), use static analysis to confirm no orphaned imports remain.

---

#### Component: Service Layer - Remove Tag Business Logic

**Files Involved**:
- `src/services/transaction_service.py`

**Purpose**: Remove all tag-related business logic from the transaction service, including tag creation during transaction creation, and the dedicated `add_tag()` and `remove_tag()` service methods.

**Implementation Requirements**:

1. **Core Logic**:
   - **Step 1**: Remove `TransactionTagRepository` import (line 35)
   - **Step 2**: Remove `tag_repo` initialization in `__init__()` (lines 76, 81)
     - Current: `self.tag_repo = TransactionTagRepository(session)`
   - **Step 3**: Remove tag creation logic in `create_transaction()` (lines 229-234)
     - This iterates over `tags` list and calls `tag_repo.add_tag()` for each
   - **Step 4**: Remove tags from `session.refresh()` call in `create_transaction()` (lines 262, 275)
   - **Step 5**: Remove entire `add_tag()` method (lines 957-1014, ~58 lines)
   - **Step 6**: Remove entire `remove_tag()` method (lines 1016-1071, ~56 lines)

2. **Data Handling**:
   - **Input validation**: `create_transaction()` will no longer accept `tags` parameter
   - **Output format**: Transaction responses will not include tags
   - **State management**: Audit logs for tag operations will be removed

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Existing code calls `service.add_tag()`
     - Solution: Remove those calls (should only be in API routes)
   - [ ] Validate: Transaction creation doesn't fail when tags are omitted
     - Solution: Update service signature to not expect tags parameter

4. **Dependencies**:
   - **Internal**: Depends on `TransactionTagRepository` (being removed)
   - **External**: None

5. **Testing Requirements**:
   - [ ] Unit test: `create_transaction()` works without tags parameter
   - [ ] Unit test: Service no longer has `add_tag()` or `remove_tag()` methods
   - [ ] Integration test: Transaction creation API works end-to-end without tags

**Acceptance Criteria**:
- [ ] `TransactionTagRepository` import removed
- [ ] `tag_repo` attribute removed from service
- [ ] Tag creation loop removed from `create_transaction()`
- [ ] `add_tag()` method deleted
- [ ] `remove_tag()` method deleted
- [ ] Service tests pass without tag-related tests
- [ ] No audit logging for tag operations

**Implementation Notes**:
- The `create_transaction()` method currently has conditional logic: `if tags: ...`. Simply remove the entire if block.
- Audit logs for `AuditAction.TAG_ADD` and `AuditAction.TAG_REMOVE` (if they exist) should also be cleaned from the audit action enum if no longer used.
- After removal, the service file should be ~100 lines shorter, improving maintainability.

---

#### Component: Schema Layer - Remove Tag Validation Schemas

**Files Involved**:
- `src/schemas/transaction.py`

**Purpose**: Remove tag-related fields from transaction request/response schemas and delete the dedicated `TagRequest` schema class.

**Implementation Requirements**:

1. **Core Logic**:
   - **Step 1**: Remove `tags` field from `TransactionCreate` schema (lines 174-212)
     - Includes: field definition and `validate_tags()` validator
   - **Step 2**: Remove `tags` field from `TransactionResponse` schema (lines 379-420)
     - Includes: field definition and `convert_tags()` validator
   - **Step 3**: Remove `tags` field from `TransactionListItem` schema (line 468)
   - **Step 4**: Delete entire `TagRequest` class (lines 588-611)
     - This schema validated tag add/remove API requests
   - **Step 5**: Remove `tags` field from `TransactionSearchParams` schema (lines 668-671)
     - This allowed filtering transactions by tags

2. **Data Handling**:
   - **Input validation**: API will no longer accept `tags` in request bodies
   - **Output format**: API responses will not include `tags` field
   - **State management**: N/A

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Client sends `tags` in request body
     - Solution: Pydantic will ignore unknown fields (if `extra = "forbid"` is set, will raise 422)
   - [ ] Validate: Existing transactions without tags don't cause serialization errors
     - Solution: Test with transactions created before migration

4. **Dependencies**:
   - **Internal**: Used by API routes (must update routes to not reference `TagRequest`)
   - **External**: Pydantic

5. **Testing Requirements**:
   - [ ] Unit test: `TransactionCreate` schema validates without tags
   - [ ] Unit test: `TransactionResponse` serializes without tags field
   - [ ] Unit test: Schema validation rejects if `extra = "forbid"` and tags sent
   - [ ] Integration test: API endpoints work with new schemas

**Acceptance Criteria**:
- [ ] `tags` field removed from `TransactionCreate`
- [ ] `tags` field removed from `TransactionResponse`
- [ ] `tags` field removed from `TransactionListItem`
- [ ] `TagRequest` class deleted
- [ ] `tags` field removed from `TransactionSearchParams`
- [ ] No Pydantic validators referencing tags
- [ ] Schema tests pass

**Implementation Notes**:
- The `convert_tags()` validator in `TransactionResponse` converts `TransactionTag` objects to strings using a list comprehension. Removing this eliminates the coupling between schema and model layers.
- If `TransactionCreate` has `extra = "forbid"`, sending tags will result in a 422 Unprocessable Entity error. If `extra = "ignore"` (default), tags will be silently ignored.
- Per [Pydantic best practices](https://docs.pydantic.dev/), removing fields from schemas is a breaking API change for clients, so this should be documented in release notes.

---

#### Component: API Layer - Remove Tag Endpoints

**Files Involved**:
- `src/api/routes/transactions.py`

**Purpose**: Remove the two tag-specific API endpoints (`POST /tags`, `DELETE /tags/{tag}`) and clean up tag handling in the transaction creation endpoint.

**Implementation Requirements**:

1. **Core Logic**:
   - **Step 1**: Remove `TagRequest` import (lines 27, 32, 35)
   - **Step 2**: Remove `tags` parameter from `create_transaction()` endpoint (line 105)
     - Endpoint signature changes from `request: TransactionCreate` (which includes tags) to same schema without tags field
   - **Step 3**: Delete entire `add_tag()` endpoint (lines 470-517, ~48 lines)
     - Route: `POST /api/v1/transactions/{transaction_id}/tags`
   - **Step 4**: Delete entire `remove_tag()` endpoint (lines 520-556, ~37 lines)
     - Route: `DELETE /api/v1/transactions/{transaction_id}/tags/{tag}`

2. **Data Handling**:
   - **Input validation**: Endpoints will return 404 Not Found after removal
   - **Output format**: N/A (endpoints deleted)
   - **State management**: N/A

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Client calls deleted endpoints
     - Solution: Return 404 Not Found (automatic when route removed)
   - [ ] Validate: Transaction creation endpoint works without tags
     - Solution: Integration test

4. **Dependencies**:
   - **Internal**: Depends on `TransactionService.add_tag()` and `TransactionService.remove_tag()` (being removed)
   - **External**: FastAPI

5. **Testing Requirements**:
   - [ ] Integration test: `POST /transactions` works without tags in request
   - [ ] Integration test: `POST /transactions/{id}/tags` returns 404
   - [ ] Integration test: `DELETE /transactions/{id}/tags/{tag}` returns 404
   - [ ] E2E test: Complete transaction workflow works without tags

**Acceptance Criteria**:
- [ ] `TagRequest` import removed
- [ ] `add_tag()` endpoint deleted
- [ ] `remove_tag()` endpoint deleted
- [ ] `create_transaction()` endpoint works without tags
- [ ] OpenAPI docs (Swagger) do not show tag endpoints
- [ ] API integration tests pass

**Implementation Notes**:
- After removing the endpoints, the FastAPI router will automatically update the OpenAPI schema, removing these routes from `/docs`.
- If these endpoints were documented in external API documentation (e.g., README, Postman collections), those references must also be updated.
- Per [REST API versioning best practices](https://restfulapi.net/versioning/), removing endpoints is a breaking change and should be communicated to API consumers.

---

#### Component: Test Suite - Remove Tag Tests

**Files Involved**:
- `tests/unit/repositories/test_transaction_tag_repository.py` (DELETE)
- `tests/unit/services/test_transaction_service.py` (modify)
- `tests/integration/test_transaction_api.py` (modify)
- `tests/e2e/test_user_journey.py` (verify and modify if needed)

**Purpose**: Remove all tests related to tag functionality while preserving overall test coverage for transaction features.

**Implementation Requirements**:

1. **Core Logic**:
   - **Step 1**: Delete entire `test_transaction_tag_repository.py` file (317 lines)
     - Contains: `TestTransactionTagRepository` class with 10 test methods
   - **Step 2**: Remove tag test methods from `test_transaction_service.py`:
     - `test_add_tag_success()` (lines 663-682)
     - `test_remove_tag_success()` (lines 683-702)
     - `test_tag_permission_denied()` (lines 704-723)
   - **Step 3**: Remove tag test methods from `test_transaction_api.py`:
     - Tag assertion in `test_create_transaction()` (line 48)
     - `test_add_tag()` (lines 254-283)
     - `test_remove_tag()` (lines 284-313)
   - **Step 4**: Verify `test_user_journey.py` for tag references and remove if found

2. **Data Handling**:
   - **Input validation**: N/A
   - **Output format**: Test suite output should show fewer total tests
   - **State management**: Test fixtures may need cleanup if they create tags

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Shared fixtures create transactions with tags
     - Solution: Update fixtures to not include tags
   - [ ] Validate: Test coverage remains ≥80% after removal
     - Solution: Run `pytest --cov=src --cov-report=term-missing`

4. **Dependencies**:
   - **Internal**: Tests depend on all layers (models, repos, services, routes)
   - **External**: pytest, pytest-asyncio

5. **Testing Requirements**:
   - [ ] Unit test: All remaining repository tests pass
   - [ ] Unit test: All remaining service tests pass
   - [ ] Integration test: All remaining API tests pass
   - [ ] Coverage: Overall coverage ≥80%
   - [ ] Coverage: Transaction module coverage ≥80%

**Acceptance Criteria**:
- [ ] `test_transaction_tag_repository.py` deleted
- [ ] Tag test methods removed from service tests
- [ ] Tag test methods removed from API tests
- [ ] E2E tests have no tag references
- [ ] All remaining tests pass
- [ ] Test coverage ≥80%
- [ ] No test fixtures create or reference tags

**Implementation Notes**:
- After removing ~60 test methods, expect test suite runtime to decrease by ~5-10 seconds.
- Use `pytest --collect-only` to verify no tag-related tests are collected.
- Per [testing best practices](https://www.qodo.ai/blog/8-python-code-refactoring-techniques-tools-practices/), removing obsolete tests is part of maintaining a healthy test suite.
- If test coverage drops below 80%, add tests for remaining transaction functionality to compensate.

---

### 3.2 Detailed File Specifications

#### `alembic/versions/XXXXXXXXXX_remove_transaction_tags.py`

**Purpose**: Drop the `transaction_tags` table and all associated database objects (indexes, constraints).

**Implementation**:

```python
"""remove transaction tags table

Revision ID: XXXXXXXXXX
Revises: 4aabd1426c98
Create Date: 2025-XX-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'XXXXXXXXXX'
down_revision: Union[str, None] = '4aabd1426c98'  # Or latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop transaction_tags table (CASCADE handles foreign keys automatically)
    op.drop_table('transaction_tags')


def downgrade() -> None:
    # Recreate transaction_tags table for rollback capability
    op.create_table(
        'transaction_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_transaction_tags'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], name='fk_transaction_tags_transaction_id_transactions', ondelete='CASCADE'),
        sa.UniqueConstraint('transaction_id', 'tag', name='uq_transaction_tags_transaction_tag'),
    )
    op.create_index('ix_transaction_tags_transaction_id', 'transaction_tags', ['transaction_id'], unique=False)
    op.create_index('ix_transaction_tags_tag', 'transaction_tags', ['tag'], unique=False)
    op.create_index('ix_transaction_tags_created_at', 'transaction_tags', ['created_at'], unique=False)
```

**Edge Cases**:
- When table already dropped: Use `DROP TABLE IF EXISTS` (PostgreSQL syntax)
- When foreign key constraints exist: Alembic handles CASCADE automatically
- When indexes exist: Dropping table drops indexes automatically

**Tests**:
- [ ] Test: Migration runs successfully on fresh database
- [ ] Test: Migration is idempotent (can run twice)
- [ ] Test: Downgrade recreates table with correct structure
- [ ] Test: Existing transactions remain intact after migration
- [ ] Test: Can create new transactions after migration

---

#### `src/models/transaction.py`

**Purpose**: Remove `TransactionTag` model and `tags` relationship from `Transaction`.

**Implementation**: Remove lines 329-406 (TransactionTag class) and lines 287-293 (Transaction.tags relationship).

**Before**:
```python
class Transaction(Base, SoftDeleteMixin):
    # ... other fields ...

    # Relationship to tags
    tags = relationship(
        "TransactionTag",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

# ... later in file ...

class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    transaction = relationship("Transaction", back_populates="tags")

    # Constraints
    __table_args__ = (
        UniqueConstraint("transaction_id", "tag", name="uq_transaction_tags_transaction_tag"),
        Index("ix_transaction_tags_transaction_id", "transaction_id"),
        Index("ix_transaction_tags_tag", "tag"),
        Index("ix_transaction_tags_created_at", "created_at"),
    )
```

**After**:
```python
class Transaction(Base, SoftDeleteMixin):
    # ... other fields ...
    # (tags relationship removed)

# (TransactionTag class completely removed)
```

**Edge Cases**:
- When ORM loads transactions with tags relationship: Will no longer attempt to load tags
- When existing code accesses `transaction.tags`: Will raise `AttributeError` (must be fixed in service/API layers first)

**Tests**:
- [ ] Test: Transaction model can be instantiated without tags
- [ ] Test: Transaction can be created in database without tags
- [ ] Test: MyPy type checking passes

---

#### `src/repositories/transaction_repository.py`

**Purpose**: Remove `TransactionTag` import and tags from eager loading.

**Implementation**:

**Line 22 - Remove import**:
```python
# BEFORE
from src.models.transaction import Transaction, TransactionTag, TransactionType

# AFTER
from src.models.transaction import Transaction, TransactionType
```

**Lines 79-82 - Remove tags from refresh**:
```python
# BEFORE
await session.refresh(
    transaction,
    ["account", "category", "tags", "recurring_transaction"]
)

# AFTER
await session.refresh(
    transaction,
    ["account", "category", "recurring_transaction"]
)
```

**Edge Cases**:
- When refresh is called without tags: SQLAlchemy will not attempt to load tags relationship

**Tests**:
- [ ] Test: Repository `create()` method works without tags
- [ ] Test: No references to `TransactionTag` remain in file

---

#### `src/services/transaction_service.py`

**Purpose**: Remove tag repository, tag creation logic, and tag management methods.

**Implementation**:

**Line 35 - Remove import**:
```python
# BEFORE
from src.repositories.transaction_tag_repository import TransactionTagRepository

# AFTER
(import removed)
```

**Lines 76, 81 - Remove tag_repo initialization**:
```python
# BEFORE
def __init__(self, session: AsyncSession):
    self.repo = TransactionRepository(session)
    self.tag_repo = TransactionTagRepository(session)
    # ...

# AFTER
def __init__(self, session: AsyncSession):
    self.repo = TransactionRepository(session)
    # (tag_repo removed)
```

**Lines 229-234 - Remove tag creation logic in `create_transaction()`**:
```python
# BEFORE
if tags:
    for tag in tags:
        tag_normalized = tag.lower().strip()
        if tag_normalized:  # Skip empty tags
            await self.tag_repo.add_tag(created.id, tag_normalized)

# AFTER
(entire block removed)
```

**Lines 957-1014 - Delete `add_tag()` method**:
```python
# BEFORE
async def add_tag(
    self,
    transaction_id: UUID,
    tag: str,
    user_id: UUID,
) -> Transaction:
    """Add a tag to a transaction."""
    # ... 58 lines of implementation ...

# AFTER
(entire method removed)
```

**Lines 1016-1071 - Delete `remove_tag()` method**:
```python
# BEFORE
async def remove_tag(
    self,
    transaction_id: UUID,
    tag: str,
    user_id: UUID,
) -> Transaction:
    """Remove a tag from a transaction."""
    # ... 56 lines of implementation ...

# AFTER
(entire method removed)
```

**Edge Cases**:
- When `create_transaction()` is called with `tags` in data: Pydantic schema will not include tags, so this won't happen

**Tests**:
- [ ] Test: `create_transaction()` works without tag creation
- [ ] Test: Service no longer has `add_tag` or `remove_tag` attributes
- [ ] Test: No references to `tag_repo` remain

---

#### `src/schemas/transaction.py`

**Purpose**: Remove `tags` fields and `TagRequest` schema.

**Implementation**:

**Lines 174-212 - Remove tags from `TransactionCreate`**:
```python
# BEFORE
class TransactionCreate(BaseModel):
    # ... other fields ...
    tags: list[str] | None = Field(
        default=None,
        description="Tags to categorize the transaction",
        example=["groceries", "food"],
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, tags) -> list[str] | None:
        if tags is None:
            return None
        return [tag.lower().strip() for tag in tags if tag.strip()]

# AFTER
class TransactionCreate(BaseModel):
    # ... other fields ...
    # (tags field and validator removed)
```

**Lines 379-420 - Remove tags from `TransactionResponse`**:
```python
# BEFORE
class TransactionResponse(BaseModel):
    # ... other fields ...
    tags: list[str] = Field(default_factory=list, description="Transaction tags")

    @field_validator("tags", mode="before")
    @classmethod
    def convert_tags(cls, tags) -> list[str]:
        if not tags:
            return []
        return [tag.tag if hasattr(tag, "tag") else tag for tag in tags]

# AFTER
class TransactionResponse(BaseModel):
    # ... other fields ...
    # (tags field and validator removed)
```

**Line 468 - Remove tags from `TransactionListItem`**:
```python
# BEFORE
class TransactionListItem(BaseModel):
    # ... other fields ...
    tags: list[str]

# AFTER
class TransactionListItem(BaseModel):
    # ... other fields ...
    # (tags field removed)
```

**Lines 588-611 - Delete `TagRequest` class**:
```python
# BEFORE
class TagRequest(BaseModel):
    """Request schema for adding/removing tags."""

    tag: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Tag to add or remove",
        example="groceries",
    )

    @field_validator("tag")
    @classmethod
    def validate_tag(cls, tag: str) -> str:
        """Normalize tag to lowercase and strip whitespace."""
        return tag.lower().strip()

# AFTER
(entire class removed)
```

**Lines 668-671 - Remove tags from `TransactionSearchParams`**:
```python
# BEFORE
class TransactionSearchParams(BaseModel):
    # ... other fields ...
    tags: list[str] | None = Field(default=None, description="Filter by tags")

# AFTER
class TransactionSearchParams(BaseModel):
    # ... other fields ...
    # (tags field removed)
```

**Edge Cases**:
- When client sends `tags` in request: Pydantic will ignore (if `extra="ignore"`) or reject (if `extra="forbid"`)

**Tests**:
- [ ] Test: `TransactionCreate` validates without tags
- [ ] Test: `TransactionResponse` serializes without tags
- [ ] Test: `TagRequest` class does not exist

---

#### `src/api/routes/transactions.py`

**Purpose**: Remove tag endpoints and tag handling.

**Implementation**:

**Lines 27, 32, 35 - Remove `TagRequest` import**:
```python
# BEFORE
from src.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TagRequest,  # Remove this
    # ...
)

# AFTER
from src.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    # (TagRequest removed)
)
```

**Line 105 - Remove tags from create endpoint** (if explicitly handled):
No change needed if schema already updated.

**Lines 470-517 - Delete `add_tag()` endpoint**:
```python
# BEFORE
@router.post(
    "/{transaction_id}/tags",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Add tag to transaction",
)
async def add_tag(
    transaction_id: UUID,
    tag_request: TagRequest,
    current_user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """Add a tag to a transaction."""
    # ... implementation ...

# AFTER
(entire endpoint removed)
```

**Lines 520-556 - Delete `remove_tag()` endpoint**:
```python
# BEFORE
@router.delete(
    "/{transaction_id}/tags/{tag}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove tag from transaction",
)
async def remove_tag(
    transaction_id: UUID,
    tag: str,
    current_user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """Remove a tag from a transaction."""
    # ... implementation ...

# AFTER
(entire endpoint removed)
```

**Edge Cases**:
- When client calls deleted endpoints: Returns 404 Not Found automatically

**Tests**:
- [ ] Test: `POST /transactions` works without tags
- [ ] Test: `POST /transactions/{id}/tags` returns 404
- [ ] Test: `DELETE /transactions/{id}/tags/{tag}` returns 404

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Code Removal (Size: M, Priority: P0)

**Goal**: Remove all tag-related code from the codebase, ensuring zero references remain while maintaining system functionality for existing transaction features.

**Scope**:
- ✅ Include: All code removal (models, repos, services, schemas, routes, tests)
- ❌ Exclude: Database migration execution (happens in Phase 2)

**Components to Implement**:
- [x] Remove tag tests (start here to enable safe refactoring)
- [x] Remove tag API endpoints
- [x] Remove tag service methods
- [x] Remove tag repository
- [x] Remove tag schemas
- [x] Remove tag model
- [x] Create database migration (but don't run it yet)

**Detailed Tasks**:

1. [ ] **Remove tag tests first** (enables safe refactoring)
   - Delete file: `tests/unit/repositories/test_transaction_tag_repository.py`
   - Remove methods from `tests/unit/services/test_transaction_service.py`:
     - `test_add_tag_success()` (lines 663-682)
     - `test_remove_tag_success()` (lines 683-702)
     - `test_tag_permission_denied()` (lines 704-723)
   - Remove methods from `tests/integration/test_transaction_api.py`:
     - Tag assertion in `test_create_transaction()` (line 48)
     - `test_add_tag()` (lines 254-283)
     - `test_remove_tag()` (lines 284-313)
   - Verify `tests/e2e/test_user_journey.py` for tag references
   - **Validation**: Run `pytest tests/` - some tests will fail (expected), but test collection should work

2. [ ] **Remove API layer tag code**
   - Remove `TagRequest` import from `src/api/routes/transactions.py` (lines 27, 32, 35)
   - Delete `add_tag()` endpoint (lines 470-517)
   - Delete `remove_tag()` endpoint (lines 520-556)
   - **Validation**: Routes file has no references to "tag" (case-insensitive grep)

3. [ ] **Remove schema layer tag code**
   - Remove `tags` field from `TransactionCreate` (lines 174-212)
   - Remove `tags` field from `TransactionResponse` (lines 379-420)
   - Remove `tags` field from `TransactionListItem` (line 468)
   - Delete `TagRequest` class (lines 588-611)
   - Remove `tags` field from `TransactionSearchParams` (lines 668-671)
   - **Validation**: Schema file has no references to "tag"

4. [ ] **Remove service layer tag code**
   - Remove `TransactionTagRepository` import (line 35)
   - Remove `tag_repo` initialization (lines 76, 81)
   - Remove tag creation logic in `create_transaction()` (lines 229-234)
   - Remove tags from refresh call (lines 262, 275)
   - Delete `add_tag()` method (lines 957-1014)
   - Delete `remove_tag()` method (lines 1016-1071)
   - **Validation**: Service file has no references to "tag_repo" or "TransactionTagRepository"

5. [ ] **Remove repository layer tag code**
   - Delete file: `src/repositories/transaction_tag_repository.py`
   - Remove `TransactionTag` import from `transaction_repository.py` (line 22)
   - Remove `tags` from eager loading in `create()` (lines 79-82)
   - **Validation**: No imports of `TransactionTagRepository` in codebase

6. [ ] **Remove model layer tag code**
   - Remove `tags` relationship from `Transaction` class (lines 287-293)
   - Remove `TransactionTag` class (lines 329-406)
   - **Validation**: Models file has no references to "TransactionTag"

7. [ ] **Create database migration** (don't execute yet)
   - Run: `uv run alembic revision -m "remove transaction tags table"`
   - Implement `upgrade()`: Drop `transaction_tags` table
   - Implement `downgrade()`: Recreate `transaction_tags` table with full structure
   - **Validation**: `uv run alembic upgrade head --sql` shows correct SQL (dry run)

8. [ ] **Run code quality checks**
   - Run: `uv run ruff format .`
   - Run: `uv run ruff check --fix .`
   - Run: `uv run mypy src/`
   - **Validation**: All checks pass with zero errors

9. [ ] **Verify zero orphaned references**
   - Run: `grep -ri "transactiontag" src/`
   - Run: `grep -ri "tag_repo" src/`
   - Run: `grep -ri "TagRequest" src/`
   - **Validation**: Zero matches (case-insensitive)

10. [ ] **Run full test suite**
    - Run: `uv run pytest tests/ -v`
    - Run: `uv run pytest tests/ --cov=src --cov-report=term-missing`
    - **Validation**: All tests pass, coverage ≥80%

**Dependencies**:
- Requires: None (this is the first phase)
- Blocks: Phase 2 (database migration)

**Validation Criteria** (Phase complete when):
- [ ] All code quality checks pass (Ruff, MyPy, no errors)
- [ ] All tests pass with zero failures
- [ ] Test coverage ≥80%
- [ ] Zero grep matches for "TransactionTag", "tag_repo", "TagRequest"
- [ ] Migration created but not yet applied
- [ ] Code review completed and approved

**Risk Factors**:
- **Risk**: Missed references to tags in obscure parts of codebase
  - **Mitigation**: Comprehensive grep search with multiple patterns (tag, tags, TagRequest, TransactionTag, tag_repo)
  - **Mitigation**: Use IDE "Find Usages" for deleted classes/methods

- **Risk**: Test coverage drops below 80%
  - **Mitigation**: Run coverage report before and after to identify gaps
  - **Mitigation**: Add tests for transaction features if needed to compensate

- **Risk**: Accidental removal of non-tag code (e.g., removing wrong lines)
  - **Mitigation**: Use version control, commit each file individually with clear messages
  - **Mitigation**: Code review before merging

**Estimated Effort**: 4-6 hours for 1 developer

---

#### Phase 2: Database Migration & Deployment (Size: S, Priority: P0)

**Goal**: Execute the database migration to drop the `transaction_tags` table in production, ensuring zero downtime and full rollback capability.

**Scope**:
- ✅ Include: Migration execution, production deployment, verification
- ❌ Exclude: Code changes (completed in Phase 1)

**Components to Implement**:
- [x] Test migration in staging environment
- [x] Execute migration in production
- [x] Deploy code to production
- [x] Verify system health post-deployment
- [x] Document rollback procedures

**Detailed Tasks**:

1. [ ] **Test migration in staging environment**
   - Create staging database backup: `pg_dump emerald_db > backup_before_migration.sql`
   - Run migration: `uv run alembic upgrade head`
   - Verify table dropped: `docker exec -it emerald-postgres psql -U emerald_user -d emerald_db -c "\dt"`
   - Test rollback: `uv run alembic downgrade -1` (should recreate table)
   - Test re-upgrade: `uv run alembic upgrade head` (should be idempotent)
   - **Validation**: Migration runs cleanly both directions

2. [ ] **Verify application works with migration**
   - Start application: `uv run uvicorn src.main:app --reload`
   - Create test transaction: `curl -X POST http://localhost:8000/api/v1/transactions ...`
   - List transactions: `curl http://localhost:8000/api/v1/transactions`
   - Verify no tag-related errors in logs
   - **Validation**: All transaction endpoints work without errors

3. [ ] **Execute production migration**
   - Create production database backup (critical!)
   - Put application in maintenance mode (optional, depends on downtime tolerance)
   - Run migration: `uv run alembic upgrade head`
   - Verify table dropped: Check PostgreSQL
   - **Validation**: Migration completes in <5 seconds (table should be small)

4. [ ] **Deploy code to production**
   - Merge Phase 1 code changes to `main` branch
   - Deploy application (method depends on infrastructure - Docker, K8s, etc.)
   - Monitor application logs for errors
   - **Validation**: Application starts successfully, health check passes

5. [ ] **Post-deployment verification**
   - Run health check: `curl http://localhost:8000/health`
   - Create test transaction via API
   - List transactions and verify response format
   - Check application logs for errors
   - Monitor error tracking (Sentry, etc.) for exceptions
   - **Validation**: Zero errors related to tags or transactions

6. [ ] **Document rollback procedures**
   - Create runbook with steps:
     - Revert code deployment
     - Run database downgrade: `uv run alembic downgrade -1`
     - Verify table recreated
     - Restart application
   - Test rollback in staging environment
   - **Validation**: Rollback procedure documented and tested

**Dependencies**:
- Requires: Phase 1 complete (all code removed)
- Blocks: None (this is the final phase)

**Validation Criteria** (Phase complete when):
- [ ] Migration executed successfully in production
- [ ] Code deployed to production
- [ ] Health checks pass
- [ ] Zero errors in logs related to tags
- [ ] Rollback procedure documented and tested
- [ ] Database backup created and stored safely

**Risk Factors**:
- **Risk**: Migration fails due to foreign key constraints
  - **Mitigation**: Alembic handles CASCADE automatically, test in staging first
  - **Mitigation**: Manual SQL as fallback: `DROP TABLE IF EXISTS transaction_tags CASCADE;`

- **Risk**: Orphaned tags data prevents table drop
  - **Mitigation**: Unlikely (CASCADE handles this), but verify row count before migration
  - **Mitigation**: If needed, manually delete rows first: `DELETE FROM transaction_tags;`

- **Risk**: Code deployed before migration runs (or vice versa)
  - **Mitigation**: Code is compatible with both states (tags ignored if present)
  - **Mitigation**: Run migration immediately before deployment

- **Risk**: Rollback needed but data loss occurs
  - **Mitigation**: Database backup created before migration
  - **Mitigation**: Downgrade function fully implemented and tested

**Estimated Effort**: 2-3 hours for 1 developer (including staging testing and monitoring)

---

### 4.2 Implementation Sequence

```
Phase 1: Code Removal (P0, 4-6 hours)
  │
  ├─ Remove tests (1 hour)
  ├─ Remove API layer (30 min)
  ├─ Remove schema layer (30 min)
  ├─ Remove service layer (1 hour)
  ├─ Remove repository layer (30 min)
  ├─ Remove model layer (30 min)
  ├─ Create migration (30 min)
  ├─ Code quality checks (30 min)
  └─ Verification & testing (1 hour)
  │
  ▼ Code review & approval
  │
Phase 2: Migration & Deployment (P0, 2-3 hours)
  │
  ├─ Staging migration test (1 hour)
  ├─ Production migration (30 min)
  ├─ Code deployment (30 min)
  └─ Verification & monitoring (1 hour)
```

**Rationale for ordering**:
- **Phase 1 before Phase 2**: Code must be removed before database migration to prevent runtime errors when code tries to access dropped table
- **Tests removed first**: Allows safe refactoring without breaking CI/CD
- **Bottom-up within Phase 1**: Start with tests (top of dependency chain), work down to models (bottom), minimizing broken references
- **Migration created but not run**: Enables code review of migration SQL before execution

**Quick Wins**:
- After removing tests, test suite runtime will decrease immediately
- After removing repository file, codebase is ~250 lines smaller
- After Phase 1 complete, code complexity metrics will improve (fewer classes, methods, LOC)

---

## 5. Simplicity & Design Validation

**Simplicity Checklist**:
- [x] Is this the SIMPLEST solution that solves the problem?
  - **Yes**: Direct removal is simpler than deprecation or feature toggling
- [x] Have we avoided premature optimization?
  - **Yes**: No optimization needed, this is a removal
- [x] Does this align with existing patterns in the codebase?
  - **Yes**: Follows standard Alembic migration and 3-layer architecture patterns
- [x] Can we deliver value in smaller increments?
  - **No**: Tags must be removed atomically to avoid inconsistent state
- [x] Are we solving the actual problem vs. a perceived problem?
  - **Yes**: Tags feature is being deprecated, not refactored

**Alternatives Considered**:

**Alternative 1: Soft Delete (Keep Code, Mark Feature as Deprecated)**
- **Description**: Keep all code but add feature flag to disable tags, mark as deprecated in API docs
- **Pros**: Easier rollback if tags needed later, gradual migration for clients
- **Cons**: Maintains technical debt, code complexity remains, database table stays, testing burden continues
- **Why rejected**: Client explicitly requested complete removal, not deprecation

**Alternative 2: Keep Table, Remove Code (Orphaned Data)**
- **Description**: Remove all code but leave `transaction_tags` table in database
- **Pros**: Faster implementation (no migration), preserves historical tag data
- **Cons**: Orphaned table wastes disk space, confuses future developers, violates data governance
- **Why rejected**: Violates clean codebase principles, per [dead code best practices](https://devopedia.org/dead-code)

**Alternative 3: Archive Tags to JSON Column**
- **Description**: Before removing table, migrate tag data to a `tags_archive` JSON column on transactions
- **Pros**: Preserves historical tag data for analytics
- **Cons**: Adds migration complexity, increases transaction table size, unclear if data is needed
- **Why rejected**: No requirement to preserve tag data, YAGNI principle

**Rationale**:
The proposed approach (complete removal) is preferred because:
1. **Simplicity**: Removes all tag-related complexity in one clean refactoring
2. **Maintainability**: Future developers won't encounter confusing deprecated code
3. **Performance**: Removes unnecessary table join and storage overhead
4. **Clarity**: Clear intent (feature removed) vs. ambiguous (feature disabled but code remains)

---

## 6. References & Related Documents

### Official Documentation
- [Alembic Tutorial - Database Migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/)

### Research & Best Practices
- [SQLAlchemy: How to safely update a model in production - Sling Academy](https://www.slingacademy.com/article/sqlalchemy-how-to-safely-update-a-model-in-production/)
- [Mastering Alembic Migrations in Python: A Comprehensive Guide - ThinhDA](https://thinhdanggroup.github.io/alembic-python/)
- [How to identify and remove dead code? - Typo Diaries (Medium)](https://medium.com/beyond-the-code-by-typo/how-to-identify-and-remove-dead-code-8283b0bf05a3)
- [Python Refactoring: Techniques, Tools, and Best Practices - CodeSee](https://www.codesee.io/learning-center/python-refactoring)
- [Dead Code - Refactoring Guru](https://refactoring.guru/smells/dead-code)

### Tools & Libraries
- [vulture - Dead Code Detector for Python](https://pypi.org/project/vulture/)
- [deadcode - Find and Fix Unused Python Code](https://github.com/albertas/deadcode)
- [Alembic on PyPI](https://pypi.org/project/alembic/)

### Internal Documentation
- Project Standards: `.claude/standards/backend.md`
- Database Standards: `.claude/standards/database.md`
- API Standards: `.claude/standards/api.md`
- Testing Standards: `.claude/standards/testing.md`
- CLAUDE.md: Project overview and commands

### Related Design Documents
- Feature description: `.features/descriptions/refactor/remove-transaction-tags.md`
- Initial schema migration: `alembic/versions/4aabd1426c98_initial_schema.py`

---

## Sources

Research for this plan incorporated best practices from:
- [SQLAlchemy: How to safely update a model in production - Sling Academy](https://www.slingacademy.com/article/sqlalchemy-how-to-safely-update-a-model-in-production/)
- [Mastering Alembic Migrations in Python: A Comprehensive Guide - ThinhDA](https://thinhdanggroup.github.io/alembic-python/)
- [Exploring Alembic in Python: A Database Migration Tool - CodeRivers](https://coderivers.org/blog/alembic-python/)
- [How to identify and remove dead code? | by typo | The Typo Diaries | Medium](https://medium.com/beyond-the-code-by-typo/how-to-identify-and-remove-dead-code-8283b0bf05a3)
- [8 Python Code Refactoring Techniques: Tools & Practices](https://www.qodo.ai/blog/8-python-code-refactoring-techniques-tools-practices/)
- [Handling Legacy Code and Refactoring Techniques: Best Practices for Python Developers - Syskool](https://syskool.com/handling-legacy-code-and-refactoring-techniques-best-practices-for-python-developers/)
- [Dead Code - Refactoring Guru](https://refactoring.guru/smells/dead-code)
- [Python Refactoring: Techniques, Tools, and Best Practices](https://www.codesee.io/learning-center/python-refactoring)

---

**Plan Prepared By**: Claude Code (AI Assistant)
**Date**: 2025-12-11
**Version**: 1.0
**Status**: Ready for Implementation
