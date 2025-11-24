# Phase 3: Transaction Management System - Implementation Plan

**Created:** 2025-11-08
**Feature:** Transaction Management with CRUD, Categorization, and Splitting
**Dependencies:** Phase 1 (Authentication & User Management) ✅, Phase 2 (Account Management) ✅
**Status:** Planning Complete - Ready for Implementation

---

## 1. Executive Summary

### Overview

Phase 3 implements a comprehensive transaction management system for the personal finance platform. This phase builds upon the existing authentication (Phase 1) and account management (Phase 2) infrastructure to enable users to record, categorize, search, and analyze their financial transactions.

The transaction system supports:
- Full CRUD operations on financial transactions with proper permission controls
- Advanced search and filtering capabilities (date ranges, amounts, merchants, descriptions)
- Transaction splitting for shared expenses (e.g., split a $100 restaurant bill into $60 mine + $40 others)
- Free-form tagging for flexible categorization
- Fuzzy text matching for merchant and description searches (handles typos)
- Real-time account balance calculations based on transaction history
- Complete audit trail for all transaction operations
- Multi-currency support aligned with account currency constraints

### Primary Objectives

1. **Transaction Management**: Enable users to create, read, update, and delete financial transactions with proper validation and permission checks
2. **Advanced Search**: Provide powerful filtering and search capabilities to help users find transactions quickly
3. **Transaction Splitting**: Allow users to break down complex transactions into multiple parts for detailed expense tracking
4. **Balance Integrity**: Ensure account balances are always accurately calculated from transaction history
5. **Data Integrity**: Maintain referential integrity between accounts and transactions with proper soft delete support
6. **Performance**: Handle large transaction volumes efficiently with proper indexing and query optimization

### Expected Outcomes

1. Users can record all financial transactions with detailed information (date, amount, merchant, description, notes)
2. Account balances update automatically when transactions are added, modified, or deleted
3. Users can search and filter transactions using multiple criteria (date ranges, amounts, types, tags)
4. Complex transactions can be split into multiple parts for detailed tracking
5. Fuzzy search helps users find transactions even with typos in merchant names or descriptions
6. All transaction operations are audited for compliance and debugging
7. Permission-based access ensures users can only view/modify transactions for accounts they have access to
8. System maintains ACID guarantees for balance calculations even under concurrent access

### Success Criteria

- All 267 acceptance criteria from Phase 3 requirements are met
- Test coverage exceeds 80% for transaction-related code
- Transaction list queries return results in < 500ms for datasets with 10,000+ transactions
- Balance calculations remain accurate to 2 decimal places
- Fuzzy search finds results with up to 2 character differences
- All endpoints return appropriate HTTP status codes with clear error messages
- Audit logs capture all transaction operations with complete before/after snapshots

---

## 2. Technical Architecture

### 2.1 System Design Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                     │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Transaction    │  │ Transaction Tag  │  │ Transaction     │  │
│  │ CRUD Routes    │  │ Routes           │  │ Split Routes    │  │
│  └────────┬───────┘  └────────┬─────────┘  └────────┬────────┘  │
└───────────┼───────────────────┼─────────────────────┼───────────┘
            │                   │                     │
            ▼                   ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │          TransactionService (Business Logic)            │    │
│  │  - CRUD operations                                      │    │
│  │  - Balance calculation & update                         │    │
│  │  - Split validation & creation                          │    │
│  │  - Permission checking integration                      │    │
│  │  - Audit logging integration                            │    │
│  └─────────┬───────────────────────────────────────────────┘    │
└────────────┼────────────────────────────────────────────────────┘
             │
             ├──────────────┬──────────────┬──────────────┐
             ▼              ▼              ▼              ▼
┌────────────────────────────────────────────────────────────────┐
│                    Repository Layer                            │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │ Transaction  │  │ Transaction │  │  Account             │   │
│  │ Repository   │  │ Tag Repo    │  │  Repository          │   │
│  └──────────────┘  └─────────────┘  └──────────────────────┘   │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer (PostgreSQL)                │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────┐    │
│  │ transactions │  │ transaction │  │ accounts (existing)  │    │
│  │  - Full text │  │   _tags     │  │  - Balance update    │    │
│  │    indexes   │  │  - Tag idx  │  │    triggers          │    │
│  │  - Date idx  │  │             │  │                      │    │
│  └──────────────┘  └─────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

Supporting Services (Existing from Phase 1-2):
┌────────────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ PermissionService  │  │  AuditService   │  │ AccountService   │
│ - Check user's     │  │ - Log all TX    │  │ - Update balance │
│   account access   │  │   operations    │  │   after TX ops   │
│ - Verify edit      │  │ - Before/after  │  │                  │
│   permissions      │  │   snapshots     │  │                  │
└────────────────────┘  └─────────────────┘  └──────────────────┘
```

**Key Design Decisions:**

1. **Transaction Model Architecture**: Single table for all transactions with parent-child relationships for splits (using `parent_transaction_id` foreign key)
2. **Tag Normalization**: Separate `transaction_tags` table for many-to-many relationship (allows efficient tag filtering)
3. **Balance Calculation**: Cached balance in `accounts.current_balance` for performance, calculated via:
   ```
   current_balance = opening_balance + SUM(transactions WHERE deleted_at IS NULL)
   ```
4. **Soft Delete Pattern**: Transactions use soft delete (`deleted_at` timestamp) to preserve audit trail and allow undo operations
5. **Permission Integration**: Leverage existing `PermissionService` to check account access before transaction operations
6. **Fuzzy Search**: PostgreSQL `pg_trgm` extension for trigram similarity matching on merchant and description fields

### 2.2 Data Flow

**Creating a Transaction:**
```
User Request → Auth Middleware → Route Handler → TransactionService
    ↓
TransactionService checks:
  1. User has account access (PermissionService)
  2. Currency matches account (validation)
  3. Account not deleted (validation)
    ↓
TransactionRepository creates transaction
    ↓
AccountService updates current_balance
    ↓
AuditService logs creation
    ↓
Response with created transaction
```

**Splitting a Transaction:**
```
User Request → Route Handler → TransactionService
    ↓
TransactionService validates:
  1. Split amounts sum to parent amount
  2. User owns transaction or is admin
    ↓
For each split:
  - Create child transaction with parent_transaction_id
  - Copy currency, account_id, base fields
  - Use individual split amount and description
    ↓
Update account balance (net zero change)
    ↓
AuditService logs split operation
    ↓
Response with parent + child transactions
```

### 2.3 State Management

**Transaction Lifecycle States:**
- **Active**: `deleted_at IS NULL` - Appears in queries, affects balance
- **Soft Deleted**: `deleted_at IS NOT NULL` - Hidden from queries, doesn't affect balance

**Split Transaction States:**
- **Standalone**: `parent_transaction_id IS NULL` - Regular transaction
- **Parent**: Has child transactions (via `parent_transaction_id` foreign key)
- **Child**: Has `parent_transaction_id` set - Part of a split

**Balance Calculation State:**
- Account balance is **eventually consistent** - updated after each transaction operation
- Database transaction ensures balance update and transaction creation/update are atomic
- No balance drift possible due to transactional integrity

---

### 2.4 Technology Decisions

#### **PostgreSQL Extensions**

**pg_trgm (Trigram Matching)**
- **Purpose**: Enable fuzzy text search for merchant and description fields
- **Why this choice**:
  - Built-in PostgreSQL extension (no external dependencies)
  - Excellent performance with GIN indexes
  - Supports similarity scoring for ranking results
  - Handles typos up to 2-3 characters effectively
  - Production-proven for financial search (used by Stripe, Plaid)
- **Version**: PostgreSQL 13+ (already in use)
- **Alternatives considered**:
  - Elasticsearch: Overkill for current scale, adds operational complexity
  - Full-text search (tsvector): No fuzzy matching support
  - Levenshtein distance: Slower than trigrams for large datasets

**Configuration:**
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_transactions_merchant_trgm ON transactions USING GIN (merchant gin_trgm_ops);
CREATE INDEX idx_transactions_description_trgm ON transactions USING GIN (description gin_trgm_ops);
```

#### **Decimal Precision**

**Numeric(15, 2)**
- **Purpose**: Store monetary amounts without floating-point rounding errors
- **Why this choice**:
  - Financial standard for precision (2 decimal places for cents/pence)
  - Supports balances up to ±999,999,999,999.99 (sufficient for personal finance)
  - PostgreSQL NUMERIC is exact (no IEEE 754 rounding issues)
  - Python Decimal type ensures precision through entire stack
- **Alternatives considered**:
  - Integer cents: Less intuitive, requires conversion logic
  - Float/Double: Accumulates rounding errors (unacceptable for finance)

#### **SQLAlchemy 2.0 Async**

**AsyncSession with Explicit Transactions**
- **Purpose**: Handle concurrent transaction operations with proper isolation
- **Why this choice**:
  - Async/await prevents blocking on database I/O
  - Explicit transactions ensure balance updates are atomic
  - `SELECT ... FOR UPDATE` prevents race conditions on balance updates
  - Follows existing codebase patterns (Phase 1-2)
- **Pattern**:
  ```python
  async with db.begin():  # Explicit transaction
      transaction = await repo.create(...)
      account = await account_repo.get_for_update(account_id)  # Row lock
      account.current_balance += transaction.amount
      await db.commit()
  ```
- **Alternatives considered**:
  - Database triggers for balance: Less flexible, harder to test
  - Read-modify-write without locking: Race conditions possible

#### **Pydantic V2 Schemas**

**Separate Request/Response Schemas**
- **Purpose**: Validate input data and serialize responses
- **Why this choice**:
  - Type safety at API boundaries
  - Automatic OpenAPI documentation generation
  - Follows existing project pattern (Phase 1-2)
  - V2 performance improvements (20-50x faster than V1)
- **Schemas needed**:
  - `TransactionCreate`: Request for creating transaction
  - `TransactionUpdate`: Request for updating transaction
  - `TransactionResponse`: Response with full transaction data
  - `TransactionListItem`: Lighter response for list endpoints
  - `TransactionSplitRequest`: Request for splitting transaction

#### **ISO 8601 Date Handling**

**Date and DateTime Fields**
- **Purpose**: Store transaction dates and value dates
- **Why this choice**:
  - `date` type for transaction_date (no timezone ambiguity)
  - `datetime` type for timestamps (created_at, updated_at) with UTC
  - ISO 8601 string representation in API (YYYY-MM-DD)
  - Python `datetime.date` and `datetime.datetime` alignment
- **Configuration**:
  ```python
  date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
  value_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
  ```

---

### 2.5 File Structure

```
src/
├── models/
│   ├── transaction.py           # NEW: Transaction and TransactionTag models
│   └── enums.py                 # MODIFIED: Add TransactionType enum
│
├── schemas/
│   ├── transaction.py           # NEW: Pydantic schemas for transactions
│   └── common.py                # EXISTING: DateRangeFilter, PaginationParams
│
├── repositories/
│   ├── transaction_repository.py       # NEW: Transaction CRUD + search queries
│   ├── transaction_tag_repository.py   # NEW: Tag management
│   └── account_repository.py           # MODIFIED: Add get_for_update() method
│
├── services/
│   ├── transaction_service.py   # NEW: Business logic for transactions
│   ├── account_service.py       # MODIFIED: Add update_balance() method
│   ├── permission_service.py    # EXISTING: Check account access
│   └── audit_service.py         # EXISTING: Log transaction operations
│
├── api/
│   └── routes/
│       ├── transactions.py      # NEW: Transaction CRUD endpoints
│       ├── transaction_tags.py  # NEW: Tag management endpoints (optional, can merge)
│       └── __init__.py          # MODIFIED: Register transaction routes
│
├── core/
│   └── database.py              # EXISTING: Database session management
│
└── main.py                      # MODIFIED: Include transaction routes

alembic/
└── versions/
    └── YYYYMMDD_create_transactions_and_tags.py  # NEW: Migration for tables

tests/
├── unit/
│   ├── services/
│   │   └── test_transaction_service.py     # NEW: Service unit tests
│   └── repositories/
│       └── test_transaction_repository.py  # NEW: Repository unit tests
├── integration/
│   └── test_transaction_routes.py          # NEW: API integration tests
└── conftest.py                              # MODIFIED: Add transaction fixtures
```

**Directory Purposes:**
- `models/`: Database table definitions (SQLAlchemy ORM models)
- `schemas/`: API request/response validation (Pydantic models)
- `repositories/`: Database query layer (abstracts SQLAlchemy)
- `services/`: Business logic layer (orchestrates repositories, applies rules)
- `api/routes/`: HTTP endpoint definitions (FastAPI routes)
- `tests/`: Test suites organized by type (unit, integration, e2e)

---

## 3. Implementation Specification

### 3.1 Component Breakdown

---

#### Component: Transaction Model

**Files Involved:**
- `src/models/transaction.py` (NEW)
- `src/models/enums.py` (MODIFIED)
- `alembic/versions/YYYYMMDD_create_transactions_and_tags.py` (NEW)

**Purpose:**
Define the core database schema for financial transactions and their tags. Transactions store all financial activity (debits, credits, transfers, fees) with full audit trail support. Tags enable flexible categorization.

**Implementation Requirements:**

1. **Core Transaction Model (src/models/transaction.py)**:
   ```python
   class Transaction(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
       __tablename__ = "transactions"

       # Relationships
       account_id: UUID (ForeignKey to accounts, CASCADE delete, indexed)
       parent_transaction_id: UUID | None (ForeignKey to transactions, SET NULL, indexed)

       # Transaction Details
       date: date (transaction date, required, indexed)
       value_date: date | None (value date, optional)
       amount: Numeric(15, 2) (transaction amount, required)
       currency: str (3-char ISO 4217, required, must match account)
       description: str (1-500 chars, required, indexed for search)
       merchant: str | None (1-100 chars, optional, indexed for search)
       transaction_type: TransactionType (enum, required, indexed)
       user_notes: str | None (max 1000 chars, optional)

       # Relationships (lazy="selectin" for N+1 prevention)
       account: relationship to Account
       parent_transaction: relationship to self (parent)
       child_transactions: relationship to self (children)
       tags: relationship to TransactionTag (cascade delete-orphan)

       # Constraints
       - CHECK: currency matches '^[A-Z]{3}$'
       - CHECK: amount != 0
       - Foreign key on account_id references accounts(id)
       - Foreign key on parent_transaction_id references transactions(id)
   ```

2. **Transaction Tag Model (src/models/transaction.py)**:
   ```python
   class TransactionTag(Base, TimestampMixin):
       __tablename__ = "transaction_tags"

       transaction_id: UUID (ForeignKey to transactions, CASCADE delete, indexed)
       tag: str (1-50 chars, required, lowercased, indexed for filtering)

       # Relationships
       transaction: relationship to Transaction

       # Constraints
       - Unique constraint on (transaction_id, tag) to prevent duplicates
       - Index on tag for efficient filtering
   ```

3. **Transaction Type Enum (src/models/enums.py)**:
   ```python
   class TransactionType(str, enum.Enum):
       DEBIT = "debit"        # Money out (expenses, withdrawals)
       CREDIT = "credit"      # Money in (income, deposits)
       TRANSFER = "transfer"  # Between accounts (future: Phase 4)
       FEE = "fee"            # Bank fees, service charges
       INTEREST = "interest"  # Interest earned or paid
       OTHER = "other"        # Miscellaneous transactions
   ```

4. **Data Handling**:
   - **Input validation**:
     - Currency must match account.currency (enforced in service layer)
     - Date cannot be in future (configurable via settings)
     - Amount must be non-zero
     - Description 1-500 characters
     - Merchant 1-100 characters if provided
     - User notes max 1000 characters
   - **Output format**:
     - All amounts serialized as strings with 2 decimal places
     - Dates in ISO 8601 format (YYYY-MM-DD)
     - Include computed fields: `is_split_parent`, `is_split_child`
   - **State management**:
     - Soft delete pattern (deleted_at timestamp)
     - Parent-child relationship for splits maintained via foreign key

5. **Edge Cases & Error Handling**:
   - [ ] Handle orphaned child transactions if parent is hard deleted (SET NULL on FK)
   - [ ] Prevent circular parent-child relationships (service layer validation)
   - [ ] Handle timezone conversion for dates (always store in UTC)
   - [ ] Validate currency exists in ISO 4217 list (optional: add validation)
   - [ ] Prevent parent_transaction_id pointing to self

6. **Dependencies**:
   - **Internal**: Account model, User model, AuditFieldsMixin, SoftDeleteMixin, TimestampMixin
   - **External**: SQLAlchemy 2.0+, PostgreSQL 13+

7. **Testing Requirements**:
   - [ ] Unit test: Transaction creation with all required fields
   - [ ] Unit test: Transaction with optional fields (merchant, value_date, user_notes)
   - [ ] Unit test: Soft delete sets deleted_at timestamp
   - [ ] Unit test: Parent-child relationship correctly established for splits
   - [ ] Unit test: Tag relationship (add, remove, list tags)
   - [ ] Unit test: Currency validation constraint
   - [ ] Unit test: Amount non-zero constraint
   - [ ] Integration test: Transaction cascade deletes when account deleted
   - [ ] Integration test: Unique tag constraint per transaction

**Acceptance Criteria**:
- [ ] Transaction model has all required fields (id, account_id, date, amount, currency, description, transaction_type)
- [ ] Parent-child relationship works for splits (can query parent.child_transactions)
- [ ] Soft delete preserves transaction data
- [ ] Tags can be added/removed from transactions
- [ ] Currency and amount constraints enforced at database level
- [ ] All timestamps auto-populate (created_at, updated_at)
- [ ] Relationships load efficiently (no N+1 queries)

**Implementation Notes**:
- Use `Numeric(15, 2)` for amount to avoid floating-point precision issues
- Use `String(3)` for currency with CHECK constraint for ISO 4217 format
- Index `date`, `account_id`, `transaction_type`, `merchant`, `description` for query performance
- GIN indexes on `merchant` and `description` for trigram fuzzy search
- Consider partial index on `parent_transaction_id WHERE parent_transaction_id IS NOT NULL` for split queries

---

#### Component: Transaction Repository

**Files Involved:**
- `src/repositories/transaction_repository.py` (NEW)
- `src/repositories/transaction_tag_repository.py` (NEW)
- `src/repositories/account_repository.py` (MODIFIED)

**Purpose:**
Provide data access layer for transaction operations. Encapsulates all SQL queries for creating, reading, updating, deleting, and searching transactions. Separates database concerns from business logic.

**Implementation Requirements:**

1. **Core CRUD Operations (transaction_repository.py)**:
   ```python
   class TransactionRepository:
       async def create(transaction: Transaction) -> Transaction
       async def get_by_id(transaction_id: UUID) -> Transaction | None
       async def update(transaction: Transaction) -> Transaction
       async def soft_delete(transaction_id: UUID) -> bool
       async def get_by_account_id(account_id: UUID, skip: int, limit: int) -> list[Transaction]
       async def count_by_account_id(account_id: UUID) -> int
   ```

2. **Advanced Query Operations**:
   ```python
   async def search_transactions(
       account_id: UUID,
       date_from: date | None = None,
       date_to: date | None = None,
       amount_min: Decimal | None = None,
       amount_max: Decimal | None = None,
       description: str | None = None,  # Fuzzy search with pg_trgm
       merchant: str | None = None,      # Fuzzy search with pg_trgm
       tags: list[str] | None = None,    # Filter by tags (AND or OR logic)
       transaction_type: TransactionType | None = None,
       sort_by: str = "date",            # date, amount, description, created_at
       sort_order: str = "desc",         # asc or desc
       skip: int = 0,
       limit: int = 20,
   ) -> tuple[list[Transaction], int]:
       """
       Advanced search with multiple filters.
       Returns (transactions, total_count).
       Uses pg_trgm for fuzzy matching on description/merchant.
       """
   ```

3. **Split Transaction Queries**:
   ```python
   async def get_children(parent_id: UUID) -> list[Transaction]
   async def get_parent(transaction_id: UUID) -> Transaction | None
   async def has_children(transaction_id: UUID) -> bool
   ```

4. **Balance Calculation Queries**:
   ```python
   async def calculate_account_balance(account_id: UUID) -> Decimal:
       """
       Calculate balance as: SUM(amount) WHERE account_id = ? AND deleted_at IS NULL
       Used to verify cached balance in accounts.current_balance
       """

   async def get_balance_at_date(account_id: UUID, as_of_date: date) -> Decimal:
       """
       Calculate historical balance at specific date.
       """
   ```

5. **Tag Repository (transaction_tag_repository.py)**:
   ```python
   class TransactionTagRepository:
       async def add_tag(transaction_id: UUID, tag: str) -> TransactionTag
       async def remove_tag(transaction_id: UUID, tag: str) -> bool
       async def get_tags(transaction_id: UUID) -> list[TransactionTag]
       async def get_all_tags_for_account(account_id: UUID) -> list[str]:
           """Return unique tags used in account (for autocomplete)"""
   ```

6. **Account Repository Modifications (account_repository.py)**:
   ```python
   # Add method for row-level locking during balance updates
   async def get_for_update(account_id: UUID) -> Account:
       """
       Get account with SELECT ... FOR UPDATE lock.
       Prevents race conditions during concurrent balance updates.
       """
       return await db.execute(
           select(Account).where(Account.id == account_id).with_for_update()
       )
   ```

7. **Data Handling**:
   - **Query optimization**:
     - Use `selectinload()` for relationships to prevent N+1 queries
     - Add `.options(selectinload(Transaction.tags))` when loading transactions
     - Use `.execution_options(populate_existing=True)` for updates
   - **Fuzzy search implementation**:
     ```python
     # Trigram similarity search (threshold 0.3 = ~70% match)
     if description:
         filters.append(func.similarity(Transaction.description, description) > 0.3)
         query = query.order_by(func.similarity(Transaction.description, description).desc())
     ```
   - **Pagination**:
     - Always use `offset(skip).limit(limit)`
     - Separate count query for total results
     - Return tuple: `(results, total_count)`

8. **Edge Cases & Error Handling**:
   - [ ] Handle empty result sets (return empty list, not None)
   - [ ] Handle invalid sort_by values (fallback to "date")
   - [ ] Handle negative skip/limit (raise ValueError)
   - [ ] Handle very large limit values (cap at 100)
   - [ ] Handle special characters in search terms (escape SQL injection)
   - [ ] Handle database connection errors (let SQLAlchemy raise, service handles)

9. **Dependencies**:
   - **Internal**: Transaction model, TransactionTag model, Account model
   - **External**: SQLAlchemy AsyncSession, pg_trgm extension

10. **Testing Requirements**:
    - [ ] Unit test: Create transaction and verify fields saved
    - [ ] Unit test: Get transaction by ID returns correct transaction
    - [ ] Unit test: Update transaction modifies fields
    - [ ] Unit test: Soft delete sets deleted_at
    - [ ] Unit test: Deleted transactions excluded from queries
    - [ ] Unit test: Search by date range filters correctly
    - [ ] Unit test: Search by amount range filters correctly
    - [ ] Unit test: Fuzzy search finds transactions with typos
    - [ ] Unit test: Tag filtering (AND logic) works
    - [ ] Unit test: Calculate balance sums amounts correctly
    - [ ] Unit test: Calculate balance excludes deleted transactions
    - [ ] Unit test: Pagination returns correct page
    - [ ] Unit test: Pagination total count is accurate
    - [ ] Integration test: get_for_update acquires row lock

**Acceptance Criteria**:
- [ ] All CRUD operations work correctly (create, read, update, soft delete)
- [ ] Search filters work individually and in combination
- [ ] Fuzzy search finds transactions with 1-2 character typos
- [ ] Pagination works correctly with skip/limit
- [ ] Balance calculation excludes soft-deleted transactions
- [ ] Tag operations work (add, remove, list)
- [ ] get_for_update prevents race conditions on balance updates
- [ ] All queries use proper indexes (verify with EXPLAIN ANALYZE)

**Implementation Notes**:
- Use SQLAlchemy's `select()` for queries, not ORM query API (deprecated)
- Implement fuzzy search threshold as configurable setting (default 0.3)
- Consider caching frequent tag autocomplete queries
- Use database indexes: `(account_id, date)`, `(account_id, deleted_at)`, GIN on description/merchant
- Benchmark search performance with 10,000+ transactions

---

#### Component: Transaction Service

**Files Involved:**
- `src/services/transaction_service.py` (NEW)
- `src/services/account_service.py` (MODIFIED)

**Purpose:**
Implement business logic for transaction operations. Orchestrates repositories, enforces business rules, handles permission checking, manages balance updates, and coordinates audit logging.

**Implementation Requirements:**

1. **Core Service Structure**:
   ```python
   class TransactionService:
       def __init__(self, db: AsyncSession):
           self.db = db
           self.transaction_repo = TransactionRepository(db)
           self.tag_repo = TransactionTagRepository(db)
           self.account_repo = AccountRepository(db)
           self.permission_service = PermissionService(db)
           self.audit_service = AuditService(db)
   ```

2. **Create Transaction Logic**:
   ```python
   async def create_transaction(
       account_id: UUID,
       date: date,
       amount: Decimal,
       currency: str,
       description: str,
       transaction_type: TransactionType,
       current_user: User,
       merchant: str | None = None,
       value_date: date | None = None,
       user_notes: str | None = None,
       tags: list[str] | None = None,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None,
   ) -> Transaction:
       """
       Create transaction with validation and balance update.

       Steps:
       1. Check user has account access (permission_service.check_account_access)
       2. Get account and verify currency matches
       3. Verify account is not deleted and is active
       4. Create transaction in database
       5. Add tags if provided
       6. Update account balance (in same transaction)
       7. Log audit entry
       8. Return created transaction
       """
       # Validate permissions
       await self.permission_service.check_account_access(
           user_id=current_user.id,
           account_id=account_id,
           required_permission=PermissionLevel.editor,  # Editors can create
       )

       # Validate currency matches account
       account = await self.account_repo.get_by_id(account_id)
       if account.currency != currency:
           raise ValidationError("Transaction currency must match account currency")

       # Use database transaction for atomicity
       async with self.db.begin():
           # Create transaction
           transaction = Transaction(...)
           created = await self.transaction_repo.create(transaction)

           # Add tags
           if tags:
               for tag in tags:
                   await self.tag_repo.add_tag(created.id, tag.lower().strip())

           # Update account balance with row lock
           account = await self.account_repo.get_for_update(account_id)
           account.current_balance += amount

           # Audit log
           await self.audit_service.log_event(
               user_id=current_user.id,
               action=AuditAction.CREATE,
               entity_type="transaction",
               entity_id=created.id,
               new_values=created.__dict__,
               ...
           )

       return created
   ```

3. **Update Transaction Logic**:
   ```python
   async def update_transaction(
       transaction_id: UUID,
       current_user: User,
       date: date | None = None,
       amount: Decimal | None = None,
       description: str | None = None,
       merchant: str | None = None,
       transaction_type: TransactionType | None = None,
       user_notes: str | None = None,
       value_date: date | None = None,
       ...
   ) -> Transaction:
       """
       Update transaction with permission check and balance recalculation.

       Steps:
       1. Get existing transaction
       2. Check user can edit (creator or admin or account owner)
       3. Verify immutable fields not changed (currency, account_id)
       4. Calculate balance delta (new_amount - old_amount)
       5. Update transaction
       6. Update account balance by delta
       7. Log audit with old/new values
       """
       # Get existing
       existing = await self.transaction_repo.get_by_id(transaction_id)

       # Permission check
       has_permission = (
           existing.created_by == current_user.id or  # Creator
           current_user.is_admin or                   # Admin
           await self.permission_service.has_permission(
               current_user.id, existing.account_id, PermissionLevel.owner
           )
       )
       if not has_permission:
           raise AuthorizationError("Cannot edit this transaction")

       # Calculate balance delta
       old_amount = existing.amount
       new_amount = amount if amount is not None else old_amount
       balance_delta = new_amount - old_amount

       async with self.db.begin():
           # Update transaction
           for field, value in updates.items():
               setattr(existing, field, value)
           updated = await self.transaction_repo.update(existing)

           # Update balance if amount changed
           if balance_delta != 0:
               account = await self.account_repo.get_for_update(existing.account_id)
               account.current_balance += balance_delta

           # Audit log
           await self.audit_service.log_data_change(
               user_id=current_user.id,
               action=AuditAction.UPDATE,
               entity_type="transaction",
               entity_id=transaction_id,
               old_values={"amount": old_amount, ...},
               new_values={"amount": new_amount, ...},
               ...
           )

       return updated
   ```

4. **Delete Transaction Logic**:
   ```python
   async def delete_transaction(
       transaction_id: UUID,
       current_user: User,
       ...
   ) -> bool:
       """
       Soft delete transaction and update account balance.

       Only owners or creators can delete.
       Deleting a parent deletes all children (cascade).
       """
       existing = await self.transaction_repo.get_by_id(transaction_id)

       # Permission check (only owners can delete)
       await self.permission_service.check_account_access(
           user_id=current_user.id,
           account_id=existing.account_id,
           required_permission=PermissionLevel.owner,
       )

       async with self.db.begin():
           # If parent, delete all children first
           if await self.transaction_repo.has_children(transaction_id):
               children = await self.transaction_repo.get_children(transaction_id)
               for child in children:
                   await self.transaction_repo.soft_delete(child.id)

           # Delete transaction (soft delete)
           await self.transaction_repo.soft_delete(transaction_id)

           # Update balance (subtract amount since it's now excluded)
           account = await self.account_repo.get_for_update(existing.account_id)
           account.current_balance -= existing.amount

           # Audit log
           await self.audit_service.log_event(
               user_id=current_user.id,
               action=AuditAction.DELETE,
               entity_type="transaction",
               entity_id=transaction_id,
               old_values=existing.__dict__,
               ...
           )

       return True
   ```

5. **Split Transaction Logic**:
   ```python
   async def split_transaction(
       transaction_id: UUID,
       splits: list[dict],  # [{"amount": Decimal, "description": str, "merchant": str}, ...]
       current_user: User,
       ...
   ) -> tuple[Transaction, list[Transaction]]:
       """
       Split transaction into multiple child transactions.

       Validation:
       1. Sum of split amounts must equal parent amount
       2. User must be creator or owner
       3. Parent cannot already be a child
       4. At least 2 splits required

       Process:
       1. Create child transactions with parent_transaction_id set
       2. Each child inherits: account_id, currency, date, value_date
       3. Each child has individual: amount, description, merchant
       4. Tags are NOT inherited (each child tagged independently)
       5. Balance update is net-zero (total in = total out)
       """
       parent = await self.transaction_repo.get_by_id(transaction_id)

       # Validation
       if parent.parent_transaction_id is not None:
           raise ValidationError("Cannot split a child transaction")

       total_splits = sum(s["amount"] for s in splits)
       if total_splits != parent.amount:
           raise ValidationError(f"Split amounts ({total_splits}) must equal parent amount ({parent.amount})")

       if len(splits) < 2:
           raise ValidationError("At least 2 splits required")

       # Permission check
       await self.permission_service.check_account_access(
           user_id=current_user.id,
           account_id=parent.account_id,
           required_permission=PermissionLevel.editor,
       )

       async with self.db.begin():
           children = []
           for split_data in splits:
               child = Transaction(
                   account_id=parent.account_id,
                   parent_transaction_id=parent.id,
                   date=parent.date,
                   value_date=parent.value_date,
                   amount=split_data["amount"],
                   currency=parent.currency,
                   description=split_data["description"],
                   merchant=split_data.get("merchant"),
                   transaction_type=parent.transaction_type,
                   user_notes=split_data.get("user_notes"),
                   created_by=current_user.id,
                   updated_by=current_user.id,
               )
               created_child = await self.transaction_repo.create(child)
               children.append(created_child)

           # No balance update needed (parent still exists, children don't add new amounts)

           # Audit log
           await self.audit_service.log_event(
               user_id=current_user.id,
               action=AuditAction.SPLIT_TRANSACTION,  # New audit action
               entity_type="transaction",
               entity_id=parent.id,
               new_values={"children": [c.id for c in children]},
               ...
           )

       return parent, children
   ```

6. **Join (Reverse Split) Logic**:
   ```python
   async def join_split_transaction(
       transaction_id: UUID,
       current_user: User,
       ...
   ) -> Transaction:
       """
       Reverse a split by deleting all children.
       Parent transaction remains as single transaction.
       """
       parent = await self.transaction_repo.get_by_id(transaction_id)

       if not await self.transaction_repo.has_children(transaction_id):
           raise ValidationError("Transaction has no splits to join")

       async with self.db.begin():
           children = await self.transaction_repo.get_children(transaction_id)

           # Delete all children
           for child in children:
               await self.transaction_repo.soft_delete(child.id)

           # No balance update (children never affected balance independently)

           # Audit log
           await self.audit_service.log_event(
               user_id=current_user.id,
               action=AuditAction.JOIN_TRANSACTION,  # New audit action
               entity_type="transaction",
               entity_id=parent.id,
               old_values={"children": [c.id for c in children]},
               ...
           )

       return parent
   ```

7. **Edge Cases & Error Handling**:
   - [ ] Handle concurrent transaction creation (row locks prevent duplicate balance updates)
   - [ ] Handle deleted accounts (validate account.deleted_at is NULL before creating transaction)
   - [ ] Handle inactive accounts (configurable: allow or block transactions)
   - [ ] Handle future dates (configurable: allow or block)
   - [ ] Handle very large amounts (Decimal supports arbitrary precision)
   - [ ] Handle split rounding errors (validate splits sum exactly, reject if mismatch)
   - [ ] Handle orphaned child transactions (if parent hard deleted, children have parent_id NULL)
   - [ ] Handle circular splits (validation prevents parent_id pointing to child or self)

8. **Dependencies**:
   - **Internal**: TransactionRepository, TagRepository, AccountRepository, PermissionService, AuditService
   - **External**: SQLAlchemy AsyncSession

9. **Testing Requirements**:
   - [ ] Unit test: Create transaction updates account balance correctly
   - [ ] Unit test: Update transaction amount updates balance by delta
   - [ ] Unit test: Delete transaction subtracts from balance
   - [ ] Unit test: Currency mismatch raises ValidationError
   - [ ] Unit test: Permission check prevents unauthorized creation
   - [ ] Unit test: Split validation rejects amounts that don't sum to parent
   - [ ] Unit test: Split creates correct number of children
   - [ ] Unit test: Join deletes all children
   - [ ] Unit test: Audit log created for all operations
   - [ ] Integration test: Concurrent transaction creation maintains balance integrity
   - [ ] Integration test: Transaction creation and balance update are atomic
   - [ ] E2E test: Full transaction lifecycle (create, update, split, join, delete)

**Acceptance Criteria**:
- [ ] All CRUD operations update account balance correctly
- [ ] Permission checks prevent unauthorized access
- [ ] Currency validation prevents mismatched currencies
- [ ] Split validation ensures amounts sum correctly
- [ ] All operations are atomic (transaction + balance update together)
- [ ] Audit logs capture all operations with before/after snapshots
- [ ] Soft delete preserves data and updates balance

**Implementation Notes**:
- Use `async with db.begin()` for explicit transactions (not dependency-scoped transactions)
- Use `SELECT ... FOR UPDATE` on account to prevent race conditions
- Calculate balance delta for updates (don't recalculate entire balance)
- Consider adding a `recalculate_balance()` method for balance verification/repair
- Add configuration flag for allowing future-dated transactions
- Add SPLIT_TRANSACTION and JOIN_TRANSACTION to AuditAction enum

---

#### Component: Transaction API Routes

**Files Involved:**
- `src/api/routes/transactions.py` (NEW)
- `src/schemas/transaction.py` (NEW)
- `src/api/routes/__init__.py` (MODIFIED)

**Purpose:**
Expose transaction operations via RESTful HTTP endpoints. Handle request validation, response serialization, error handling, and HTTP-specific concerns. Delegate business logic to TransactionService.

**Implementation Requirements:**

1. **Pydantic Schemas (src/schemas/transaction.py)**:
   ```python
   # Request schemas
   class TransactionCreate(BaseModel):
       date: date
       amount: Decimal = Field(..., decimal_places=2)
       currency: str = Field(..., pattern="^[A-Z]{3}$", min_length=3, max_length=3)
       description: str = Field(..., min_length=1, max_length=500)
       transaction_type: TransactionType
       merchant: str | None = Field(None, min_length=1, max_length=100)
       value_date: date | None = None
       user_notes: str | None = Field(None, max_length=1000)
       tags: list[str] | None = Field(None, max_items=20)

       @field_validator("tags")
       def validate_tags(cls, v):
           if v:
               return [tag.lower().strip() for tag in v if tag.strip()]
           return v

   class TransactionUpdate(BaseModel):
       date: date | None = None
       amount: Decimal | None = Field(None, decimal_places=2)
       description: str | None = Field(None, min_length=1, max_length=500)
       merchant: str | None = Field(None, min_length=1, max_length=100)
       transaction_type: TransactionType | None = None
       user_notes: str | None = Field(None, max_length=1000)
       value_date: date | None = None

   class TransactionSplitRequest(BaseModel):
       splits: list[SplitItem] = Field(..., min_items=2)

       class SplitItem(BaseModel):
           amount: Decimal = Field(..., decimal_places=2)
           description: str = Field(..., min_length=1, max_length=500)
           merchant: str | None = Field(None, min_length=1, max_length=100)
           user_notes: str | None = Field(None, max_length=1000)

   # Response schemas
   class TransactionResponse(BaseModel):
       id: UUID
       account_id: UUID
       date: date
       value_date: date | None
       amount: Decimal
       currency: str
       description: str
       merchant: str | None
       transaction_type: TransactionType
       user_notes: str | None
       tags: list[str]
       parent_transaction_id: UUID | None
       is_split_parent: bool
       is_split_child: bool
       created_at: datetime
       updated_at: datetime
       created_by: UUID
       updated_by: UUID

       model_config = ConfigDict(from_attributes=True)

   class TransactionListItem(BaseModel):
       """Lighter response for list endpoints"""
       id: UUID
       date: date
       amount: Decimal
       currency: str
       description: str
       merchant: str | None
       transaction_type: TransactionType
       tags: list[str]
       is_split_parent: bool

       model_config = ConfigDict(from_attributes=True)

   class TransactionListResponse(BaseModel):
       items: list[TransactionListItem]
       total: int
       skip: int
       limit: int
   ```

2. **API Routes (src/api/routes/transactions.py)**:
   ```python
   router = APIRouter(prefix="/accounts/{account_id}/transactions", tags=["Transactions"])

   @router.post("", response_model=TransactionResponse, status_code=201)
   async def create_transaction(
       account_id: UUID,
       request: Request,
       transaction_data: TransactionCreate,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> TransactionResponse:
       """
       Create new transaction for account.

       Requires EDITOR or OWNER permission on account.
       Updates account balance automatically.
       """
       transaction = await transaction_service.create_transaction(
           account_id=account_id,
           date=transaction_data.date,
           amount=transaction_data.amount,
           currency=transaction_data.currency,
           description=transaction_data.description,
           transaction_type=transaction_data.transaction_type,
           merchant=transaction_data.merchant,
           value_date=transaction_data.value_date,
           user_notes=transaction_data.user_notes,
           tags=transaction_data.tags,
           current_user=current_user,
           request_id=request.state.request_id,
           ip_address=request.client.host,
           user_agent=request.headers.get("user-agent"),
       )
       return TransactionResponse.model_validate(transaction)

   @router.get("/{transaction_id}", response_model=TransactionResponse)
   async def get_transaction(
       account_id: UUID,
       transaction_id: UUID,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> TransactionResponse:
       """Get transaction by ID. Requires VIEWER+ permission."""
       transaction = await transaction_service.get_transaction(
           transaction_id=transaction_id,
           current_user=current_user,
       )

       # Verify transaction belongs to requested account
       if transaction.account_id != account_id:
           raise NotFoundError("Transaction not found")

       return TransactionResponse.model_validate(transaction)

   @router.get("", response_model=TransactionListResponse)
   async def list_transactions(
       account_id: UUID,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
       skip: int = Query(0, ge=0),
       limit: int = Query(20, ge=1, le=100),
       date_from: date | None = Query(None),
       date_to: date | None = Query(None),
       amount_min: Decimal | None = Query(None),
       amount_max: Decimal | None = Query(None),
       description: str | None = Query(None, max_length=500),
       merchant: str | None = Query(None, max_length=100),
       tags: list[str] | None = Query(None),
       transaction_type: TransactionType | None = Query(None),
       sort_by: str = Query("date", pattern="^(date|amount|description|created_at)$"),
       sort_order: str = Query("desc", pattern="^(asc|desc)$"),
   ) -> TransactionListResponse:
       """
       List and filter transactions for account.

       Supports:
       - Date range filtering (date_from, date_to)
       - Amount range filtering (amount_min, amount_max)
       - Fuzzy search on description and merchant
       - Tag filtering (transactions with ANY of the specified tags)
       - Transaction type filtering
       - Sorting by date, amount, description, or created_at
       - Pagination (skip, limit)
       """
       transactions, total = await transaction_service.search_transactions(
           account_id=account_id,
           current_user=current_user,
           date_from=date_from,
           date_to=date_to,
           amount_min=amount_min,
           amount_max=amount_max,
           description=description,
           merchant=merchant,
           tags=tags,
           transaction_type=transaction_type,
           sort_by=sort_by,
           sort_order=sort_order,
           skip=skip,
           limit=limit,
       )

       return TransactionListResponse(
           items=[TransactionListItem.model_validate(t) for t in transactions],
           total=total,
           skip=skip,
           limit=limit,
       )

   @router.put("/{transaction_id}", response_model=TransactionResponse)
   async def update_transaction(
       account_id: UUID,
       transaction_id: UUID,
       request: Request,
       transaction_data: TransactionUpdate,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> TransactionResponse:
       """
       Update transaction.

       Requires: User is creator, account owner, or admin.
       Cannot change currency or account_id.
       """
       transaction = await transaction_service.update_transaction(
           transaction_id=transaction_id,
           current_user=current_user,
           date=transaction_data.date,
           amount=transaction_data.amount,
           description=transaction_data.description,
           merchant=transaction_data.merchant,
           transaction_type=transaction_data.transaction_type,
           user_notes=transaction_data.user_notes,
           value_date=transaction_data.value_date,
           request_id=request.state.request_id,
           ip_address=request.client.host,
           user_agent=request.headers.get("user-agent"),
       )
       return TransactionResponse.model_validate(transaction)

   @router.delete("/{transaction_id}", status_code=204)
   async def delete_transaction(
       account_id: UUID,
       transaction_id: UUID,
       request: Request,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> None:
       """
       Soft delete transaction.

       Requires OWNER permission.
       Updates account balance.
       """
       await transaction_service.delete_transaction(
           transaction_id=transaction_id,
           current_user=current_user,
           request_id=request.state.request_id,
           ip_address=request.client.host,
           user_agent=request.headers.get("user-agent"),
       )

   @router.post("/{transaction_id}/split", response_model=TransactionResponse)
   async def split_transaction(
       account_id: UUID,
       transaction_id: UUID,
       request: Request,
       split_request: TransactionSplitRequest,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> TransactionResponse:
       """
       Split transaction into multiple child transactions.

       Requires EDITOR+ permission.
       Split amounts must sum to original transaction amount.
       """
       parent, children = await transaction_service.split_transaction(
           transaction_id=transaction_id,
           splits=[s.model_dump() for s in split_request.splits],
           current_user=current_user,
           request_id=request.state.request_id,
           ip_address=request.client.host,
           user_agent=request.headers.get("user-agent"),
       )
       return TransactionResponse.model_validate(parent)

   @router.delete("/{transaction_id}/split", response_model=TransactionResponse)
   async def join_split_transaction(
       account_id: UUID,
       transaction_id: UUID,
       request: Request,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> TransactionResponse:
       """
       Reverse transaction split (join children back to parent).

       Requires EDITOR+ permission.
       Deletes all child transactions.
       """
       parent = await transaction_service.join_split_transaction(
           transaction_id=transaction_id,
           current_user=current_user,
           request_id=request.state.request_id,
           ip_address=request.client.host,
           user_agent=request.headers.get("user-agent"),
       )
       return TransactionResponse.model_validate(parent)

   # Tag management endpoints
   @router.post("/{transaction_id}/tags", response_model=TransactionResponse)
   async def add_tag(
       account_id: UUID,
       transaction_id: UUID,
       tag: str = Body(..., embed=True, min_length=1, max_length=50),
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> TransactionResponse:
       """Add tag to transaction. Requires EDITOR+ permission."""
       transaction = await transaction_service.add_tag(
           transaction_id=transaction_id,
           tag=tag,
           current_user=current_user,
       )
       return TransactionResponse.model_validate(transaction)

   @router.delete("/{transaction_id}/tags/{tag}", status_code=204)
   async def remove_tag(
       account_id: UUID,
       transaction_id: UUID,
       tag: str,
       current_user: User = Depends(require_active_user),
       transaction_service: TransactionService = Depends(get_transaction_service),
   ) -> None:
       """Remove tag from transaction. Requires EDITOR+ permission."""
       await transaction_service.remove_tag(
           transaction_id=transaction_id,
           tag=tag,
           current_user=current_user,
       )
   ```

3. **Dependency Injection (src/api/dependencies.py)**:
   ```python
   async def get_transaction_service(
       db: AsyncSession = Depends(get_db),
   ) -> TransactionService:
       return TransactionService(db)
   ```

4. **Edge Cases & Error Handling**:
   - [ ] Handle 400: Currency mismatch, split amounts don't sum, amount is zero
   - [ ] Handle 401: Not authenticated (middleware handles)
   - [ ] Handle 403: User doesn't have account access
   - [ ] Handle 404: Account not found, transaction not found
   - [ ] Handle 409: Split amounts don't total parent amount
   - [ ] Handle 422: Validation errors (Pydantic handles)
   - [ ] Handle 500: Database errors, unexpected exceptions

5. **Dependencies**:
   - **Internal**: TransactionService, require_active_user dependency
   - **External**: FastAPI, Pydantic

6. **Testing Requirements**:
   - [ ] Integration test: POST creates transaction and returns 201
   - [ ] Integration test: GET retrieves transaction with all fields
   - [ ] Integration test: PUT updates transaction and returns updated data
   - [ ] Integration test: DELETE soft deletes and returns 204
   - [ ] Integration test: POST split validates amount sum
   - [ ] Integration test: List with filters returns correct results
   - [ ] Integration test: Fuzzy search finds transactions
   - [ ] Integration test: Permission errors return 403
   - [ ] Integration test: Invalid currency returns 400
   - [ ] Integration test: Pagination works correctly
   - [ ] E2E test: Full transaction flow (create → update → split → join → delete)

**Acceptance Criteria**:
- [ ] All endpoints follow RESTful conventions
- [ ] Request validation uses Pydantic schemas
- [ ] Response format is consistent across endpoints
- [ ] Error responses include clear error messages
- [ ] All endpoints require authentication
- [ ] Permission checks prevent unauthorized access
- [ ] OpenAPI documentation generated automatically
- [ ] All endpoints include example requests/responses

**Implementation Notes**:
- Use `response_model` for automatic validation and serialization
- Use `status_code` parameter for proper HTTP status codes
- Use `Query()` for query parameter validation
- Use `Body()` for request body validation
- Include comprehensive docstrings for OpenAPI generation
- Add rate limiting decorators if needed (e.g., `@limiter.limit("100/minute")`)
- Consider adding endpoint-specific rate limits for expensive searches

---

#### Component: Database Migration

**Files Involved:**
- `alembic/versions/YYYYMMDD_create_transactions_and_tags.py` (NEW)

**Purpose:**
Create database schema for transactions and transaction tags tables. Install required PostgreSQL extensions. Create indexes for query performance.

**Implementation Requirements:**

1. **Migration File Structure**:
   ```python
   """Create transactions and transaction_tags tables

   Revision ID: abc123def456
   Revises: 7cd3ac786069  # Latest migration from Phase 2
   Create Date: 2025-11-08
   """

   from alembic import op
   import sqlalchemy as sa
   from sqlalchemy.dialects import postgresql
   import uuid

   # revision identifiers
   revision = 'abc123def456'
   down_revision = '7cd3ac786069'
   branch_labels = None
   depends_on = None
   ```

2. **Extension Installation**:
   ```python
   def upgrade():
       # Install pg_trgm extension for fuzzy search
       op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
   ```

3. **Enum Type Creation**:
   ```python
   # Create TransactionType enum
   transaction_type_enum = postgresql.ENUM(
       'debit', 'credit', 'transfer', 'fee', 'interest', 'other',
       name='transactiontype',
       create_type=False,
   )
   transaction_type_enum.create(op.get_bind(), checkfirst=True)
   ```

4. **Transactions Table**:
   ```python
   op.create_table(
       'transactions',
       # Primary Key
       sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),

       # Foreign Keys
       sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
       sa.Column('parent_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),

       # Transaction Data
       sa.Column('date', sa.Date, nullable=False),
       sa.Column('value_date', sa.Date, nullable=True),
       sa.Column('amount', sa.Numeric(15, 2), nullable=False),
       sa.Column('currency', sa.String(3), nullable=False),
       sa.Column('description', sa.String(500), nullable=False),
       sa.Column('merchant', sa.String(100), nullable=True),
       sa.Column('transaction_type', transaction_type_enum, nullable=False),
       sa.Column('user_notes', sa.String(1000), nullable=True),

       # Timestamps (from TimestampMixin)
       sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
       sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

       # Soft Delete (from SoftDeleteMixin)
       sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),

       # Audit Fields (from AuditFieldsMixin)
       sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
       sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),

       # Constraints
       sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_transactions_currency_format'),
       sa.CheckConstraint("amount != 0", name='ck_transactions_amount_nonzero'),
   )
   ```

5. **Transaction Tags Table**:
   ```python
   op.create_table(
       'transaction_tags',
       # Primary Key
       sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),

       # Foreign Key
       sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),

       # Tag Data
       sa.Column('tag', sa.String(50), nullable=False),

       # Timestamp
       sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

       # Constraints
       sa.UniqueConstraint('transaction_id', 'tag', name='uq_transaction_tags_transaction_tag'),
   )
   ```

6. **Indexes for Performance**:
   ```python
   # Transactions table indexes
   op.create_index('ix_transactions_account_id', 'transactions', ['account_id'])
   op.create_index('ix_transactions_date', 'transactions', ['date'])
   op.create_index('ix_transactions_transaction_type', 'transactions', ['transaction_type'])
   op.create_index('ix_transactions_parent_transaction_id', 'transactions', ['parent_transaction_id'], postgresql_where=sa.text('parent_transaction_id IS NOT NULL'))
   op.create_index('ix_transactions_deleted_at', 'transactions', ['deleted_at'])

   # Composite index for common queries (account + date range)
   op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'date'])

   # Composite index for soft delete queries
   op.create_index('ix_transactions_account_deleted', 'transactions', ['account_id', 'deleted_at'])

   # GIN indexes for trigram fuzzy search
   op.execute("CREATE INDEX ix_transactions_merchant_trgm ON transactions USING GIN (merchant gin_trgm_ops)")
   op.execute("CREATE INDEX ix_transactions_description_trgm ON transactions USING GIN (description gin_trgm_ops)")

   # Transaction tags indexes
   op.create_index('ix_transaction_tags_transaction_id', 'transaction_tags', ['transaction_id'])
   op.create_index('ix_transaction_tags_tag', 'transaction_tags', ['tag'])
   ```

7. **Downgrade Function**:
   ```python
   def downgrade():
       # Drop tables
       op.drop_table('transaction_tags')
       op.drop_table('transactions')

       # Drop enum type
       transaction_type_enum.drop(op.get_bind(), checkfirst=True)

       # Extension remains (safe to leave installed)
   ```

8. **Edge Cases & Error Handling**:
   - [ ] Handle existing extension installation (CREATE EXTENSION IF NOT EXISTS)
   - [ ] Handle enum type already exists (create_type=False, checkfirst=True)
   - [ ] Handle downgrade with existing data (soft delete cascade)
   - [ ] Handle index creation on large tables (use CONCURRENTLY for production)

9. **Dependencies**:
   - **Internal**: Existing accounts and users tables
   - **External**: PostgreSQL 13+, Alembic, pg_trgm extension

10. **Testing Requirements**:
    - [ ] Test: Migration runs successfully (alembic upgrade head)
    - [ ] Test: Downgrade runs successfully (alembic downgrade -1)
    - [ ] Test: Tables created with correct schema
    - [ ] Test: Indexes created successfully
    - [ ] Test: Constraints enforced (currency format, amount nonzero)
    - [ ] Test: Foreign keys enforce referential integrity
    - [ ] Test: Cascade delete from account deletes transactions
    - [ ] Test: SET NULL on parent delete handles orphaned children
    - [ ] Test: pg_trgm extension installed

**Acceptance Criteria**:
- [ ] Migration creates transactions table with all required columns
- [ ] Migration creates transaction_tags table
- [ ] Migration creates TransactionType enum
- [ ] Migration installs pg_trgm extension
- [ ] All indexes created for query performance
- [ ] Constraints enforce data integrity
- [ ] Foreign keys enforce referential integrity
- [ ] Downgrade removes all changes cleanly

**Implementation Notes**:
- Use `postgresql.UUID(as_uuid=True)` for UUID columns
- Use `sa.Numeric(15, 2)` for decimal precision
- Use `sa.DateTime(timezone=True)` for timestamp columns
- Use `server_default=sa.func.now()` for auto-populated timestamps
- Use `onupdate=sa.func.now()` for auto-updated timestamps
- Use `ondelete='CASCADE'` for account_id foreign key
- Use `ondelete='SET NULL'` for parent_transaction_id foreign key
- For production, consider using `CREATE INDEX CONCURRENTLY` to avoid table locks

---

#### Component: Account Service Balance Update

**Files Involved:**
- `src/services/account_service.py` (MODIFIED)

**Purpose:**
Add balance calculation and update methods to AccountService to support transaction operations. Ensure balance integrity and provide balance verification capabilities.

**Implementation Requirements:**

1. **New Methods to Add**:
   ```python
   class AccountService:
       # Existing methods...

       async def update_balance(
           self,
           account_id: UUID,
           delta: Decimal,
           current_user: User,
       ) -> Account:
           """
           Update account balance by delta amount.

           Used by TransactionService when creating/updating/deleting transactions.
           Uses SELECT ... FOR UPDATE to prevent race conditions.

           Args:
               account_id: Account to update
               delta: Amount to add to current balance (can be negative)
               current_user: User performing operation (for audit)

           Returns:
               Updated account with new balance
           """
           async with self.db.begin():
               # Lock row for update
               account = await self.account_repo.get_for_update(account_id)

               if not account:
                   raise NotFoundError("Account not found")

               # Update balance
               old_balance = account.current_balance
               account.current_balance += delta
               new_balance = account.current_balance

               # Save
               updated_account = await self.account_repo.update(account)

               # Audit log (optional: could be noisy)
               # await self.audit_service.log_data_change(...)

               return updated_account

       async def recalculate_balance(
           self,
           account_id: UUID,
           current_user: User,
       ) -> tuple[Decimal, Decimal]:
           """
           Recalculate account balance from scratch.

           Useful for:
           - Balance verification (compare cached vs calculated)
           - Balance repair after data issues
           - Administrative operations

           Returns:
               tuple: (cached_balance, calculated_balance)
           """
           from src.repositories.transaction_repository import TransactionRepository

           transaction_repo = TransactionRepository(self.db)

           account = await self.account_repo.get_by_id(account_id)
           if not account:
               raise NotFoundError("Account not found")

           cached_balance = account.current_balance

           # Calculate from transactions
           calculated_balance = await transaction_repo.calculate_account_balance(account_id)
           calculated_balance += account.opening_balance

           return cached_balance, calculated_balance

       async def verify_and_fix_balance(
           self,
           account_id: UUID,
           current_user: User,
       ) -> dict:
           """
           Verify balance matches calculation. Fix if mismatch.

           Admin-only operation.

           Returns:
               dict with verification results
           """
           if not current_user.is_admin:
               raise AuthorizationError("Admin access required")

           cached, calculated = await self.recalculate_balance(account_id, current_user)

           mismatch = cached != calculated

           if mismatch:
               # Fix balance
               async with self.db.begin():
                   account = await self.account_repo.get_for_update(account_id)
                   account.current_balance = calculated
                   await self.account_repo.update(account)

                   # Audit log
                   await self.audit_service.log_event(
                       user_id=current_user.id,
                       action=AuditAction.UPDATE,
                       entity_type="account",
                       entity_id=account_id,
                       description="Balance mismatch repaired",
                       old_values={"current_balance": str(cached)},
                       new_values={"current_balance": str(calculated)},
                   )

           return {
               "account_id": str(account_id),
               "cached_balance": str(cached),
               "calculated_balance": str(calculated),
               "mismatch": mismatch,
               "fixed": mismatch,
           }
   ```

2. **Edge Cases & Error Handling**:
   - [ ] Handle concurrent balance updates (row lock prevents race conditions)
   - [ ] Handle very large balance deltas (Decimal supports arbitrary precision)
   - [ ] Handle negative balances (allowed for credit cards and loans)
   - [ ] Handle balance calculation for deleted transactions (exclude from calculation)

3. **Dependencies**:
   - **Internal**: AccountRepository, TransactionRepository, AuditService
   - **External**: SQLAlchemy AsyncSession

4. **Testing Requirements**:
   - [ ] Unit test: update_balance adds delta correctly
   - [ ] Unit test: update_balance subtracts delta correctly
   - [ ] Unit test: recalculate_balance matches expected value
   - [ ] Unit test: verify_and_fix_balance repairs mismatches
   - [ ] Integration test: Concurrent balance updates maintain integrity
   - [ ] Integration test: Balance calculation excludes deleted transactions

**Acceptance Criteria**:
- [ ] update_balance method updates balance atomically
- [ ] recalculate_balance method calculates from transactions
- [ ] verify_and_fix_balance repairs mismatches
- [ ] Row locking prevents race conditions
- [ ] All methods handle errors gracefully

**Implementation Notes**:
- Use `SELECT ... FOR UPDATE` for row-level locking
- Consider adding a scheduled job to verify all balances periodically
- Add admin endpoint for balance verification/repair
- Log balance repairs to audit log for compliance

---

### 3.2 Testing Strategy

**Test Organization:**
- Unit tests: Test individual functions/methods in isolation (repositories, service methods)
- Integration tests: Test API endpoints with database interactions
- E2E tests: Test complete user workflows (create account → add transactions → split → delete)

**Coverage Requirements:**
- Minimum 80% code coverage for transaction-related code
- 100% coverage for balance calculation logic (critical path)
- All edge cases must have explicit tests

**Key Test Scenarios:**

1. **Transaction CRUD:**
   - [ ] Create transaction with all fields
   - [ ] Create transaction with minimal fields
   - [ ] Get transaction by ID
   - [ ] Update transaction amount (verify balance delta)
   - [ ] Update transaction description (no balance change)
   - [ ] Delete transaction (verify balance update)
   - [ ] Soft deleted transaction not in queries

2. **Balance Integrity:**
   - [ ] Create transaction updates balance
   - [ ] Update amount updates balance by delta
   - [ ] Delete transaction subtracts from balance
   - [ ] Split transaction doesn't change balance (net-zero)
   - [ ] Concurrent transactions maintain balance integrity
   - [ ] Recalculate balance matches expected

3. **Search & Filtering:**
   - [ ] Filter by date range
   - [ ] Filter by amount range
   - [ ] Filter by transaction type
   - [ ] Filter by tags (any tag, all tags)
   - [ ] Fuzzy search on merchant (1 char typo)
   - [ ] Fuzzy search on description (2 char typo)
   - [ ] Combine multiple filters
   - [ ] Pagination works correctly

4. **Transaction Splitting:**
   - [ ] Split validates amounts sum to parent
   - [ ] Split creates correct number of children
   - [ ] Split children have parent_id set
   - [ ] Split preserves currency and account
   - [ ] Split doesn't change balance
   - [ ] Join removes all children
   - [ ] Join restores parent as standalone
   - [ ] Cannot split a child transaction
   - [ ] Cannot split with < 2 splits

5. **Permissions:**
   - [ ] VIEWER can list transactions
   - [ ] VIEWER cannot create transactions
   - [ ] EDITOR can create transactions
   - [ ] EDITOR can update own transactions
   - [ ] EDITOR cannot delete transactions
   - [ ] OWNER can delete transactions
   - [ ] User cannot access other accounts
   - [ ] Admin can access all accounts

6. **Validation:**
   - [ ] Currency must match account
   - [ ] Amount must be non-zero
   - [ ] Date cannot be in future (configurable)
   - [ ] Description 1-500 characters
   - [ ] Merchant max 100 characters
   - [ ] User notes max 1000 characters
   - [ ] Tags max 50 characters each

7. **Audit Logging:**
   - [ ] Create transaction logged
   - [ ] Update transaction logged with old/new
   - [ ] Delete transaction logged
   - [ ] Split logged with children
   - [ ] Join logged with children
   - [ ] Tag add/remove logged

**Test Fixtures (conftest.py):**

```python
@pytest.fixture
async def sample_transaction(db_session, sample_account, sample_user):
    """Create sample transaction for testing"""
    transaction = Transaction(
        account_id=sample_account.id,
        date=date.today(),
        amount=Decimal("100.50"),
        currency="USD",
        description="Test Transaction",
        merchant="Test Merchant",
        transaction_type=TransactionType.debit,
        created_by=sample_user.id,
        updated_by=sample_user.id,
    )
    db_session.add(transaction)
    await db_session.commit()
    await db_session.refresh(transaction)
    return transaction


@pytest.fixture
async def sample_split_transaction(db_session, sample_account, sample_user):
    """Create split transaction for testing"""
    parent = Transaction(...)
    child1 = Transaction(parent_transaction_id=parent.id, amount=Decimal("60.00"), ...)
    child2 = Transaction(parent_transaction_id=parent.id, amount=Decimal("40.50"), ...)
    db_session.add_all([parent, child1, child2])
    await db_session.commit()
    return parent, [child1, child2]
```

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

This implementation is structured as a single phase with sequential steps. The feature is cohesive and doesn't benefit from staged delivery - all components must work together for the system to be functional.

---

#### Phase 1: Core Transaction System (Size: L, Priority: P0)

**Goal:** Deliver a fully functional transaction management system with CRUD operations, balance calculations, search capabilities, and transaction splitting.

**Scope:**
- ✅ Include: All transaction CRUD operations, balance updates, search/filtering, transaction splitting, tags, audit logging
- ❌ Exclude: Transaction categories (Phase 4), recurring transactions (future), bulk imports (future)

**Components to Implement:**

**Step 1: Database Schema & Models**
- [ ] Create TransactionType enum in `src/models/enums.py`
- [ ] Create Transaction model in `src/models/transaction.py`
- [ ] Create TransactionTag model in `src/models/transaction.py`
- [ ] Create Alembic migration `YYYYMMDD_create_transactions_and_tags.py`
- [ ] Add SPLIT_TRANSACTION and JOIN_TRANSACTION to AuditAction enum

**Step 2: Repository Layer**
- [ ] Create `src/repositories/transaction_repository.py`
  - [ ] Implement create, get_by_id, update, soft_delete methods
  - [ ] Implement list and count methods
  - [ ] Implement advanced search_transactions method with fuzzy search
  - [ ] Implement split-related methods (get_children, get_parent, has_children)
  - [ ] Implement balance calculation methods
- [ ] Create `src/repositories/transaction_tag_repository.py`
  - [ ] Implement add_tag, remove_tag, get_tags methods
  - [ ] Implement get_all_tags_for_account for autocomplete
- [ ] Modify `src/repositories/account_repository.py`
  - [ ] Add get_for_update method with row locking

**Step 3: Service Layer**
- [ ] Create `src/services/transaction_service.py`
  - [ ] Implement create_transaction with permission check and balance update
  - [ ] Implement get_transaction with permission check
  - [ ] Implement search_transactions with all filters
  - [ ] Implement update_transaction with balance delta calculation
  - [ ] Implement delete_transaction with balance update
  - [ ] Implement split_transaction with validation
  - [ ] Implement join_split_transaction
  - [ ] Implement add_tag and remove_tag methods
- [ ] Modify `src/services/account_service.py`
  - [ ] Add update_balance method
  - [ ] Add recalculate_balance method
  - [ ] Add verify_and_fix_balance method (admin only)

**Step 4: API Layer**
- [ ] Create `src/schemas/transaction.py`
  - [ ] Create TransactionCreate schema
  - [ ] Create TransactionUpdate schema
  - [ ] Create TransactionResponse schema
  - [ ] Create TransactionListItem schema
  - [ ] Create TransactionListResponse schema
  - [ ] Create TransactionSplitRequest schema
- [ ] Create `src/api/routes/transactions.py`
  - [ ] Implement POST /accounts/{id}/transactions (create)
  - [ ] Implement GET /accounts/{id}/transactions/{tx_id} (get one)
  - [ ] Implement GET /accounts/{id}/transactions (list with filters)
  - [ ] Implement PUT /accounts/{id}/transactions/{tx_id} (update)
  - [ ] Implement DELETE /accounts/{id}/transactions/{tx_id} (delete)
  - [ ] Implement POST /accounts/{id}/transactions/{tx_id}/split (split)
  - [ ] Implement DELETE /accounts/{id}/transactions/{tx_id}/split (join)
  - [ ] Implement POST /accounts/{id}/transactions/{tx_id}/tags (add tag)
  - [ ] Implement DELETE /accounts/{id}/transactions/{tx_id}/tags/{tag} (remove tag)
- [ ] Modify `src/api/routes/__init__.py` to register transaction routes
- [ ] Add get_transaction_service dependency to `src/api/dependencies.py`

**Step 5: Database Migration**
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify tables created: `transactions`, `transaction_tags`
- [ ] Verify indexes created (check with `\d transactions` in psql)
- [ ] Verify pg_trgm extension installed
- [ ] Test downgrade: `alembic downgrade -1`
- [ ] Test upgrade again: `alembic upgrade head`

**Step 6: Testing**
- [ ] Write unit tests for `transaction_repository.py`
  - [ ] Test CRUD operations
  - [ ] Test search with filters
  - [ ] Test fuzzy search
  - [ ] Test balance calculations
  - [ ] Test pagination
- [ ] Write unit tests for `transaction_service.py`
  - [ ] Test create with balance update
  - [ ] Test update with balance delta
  - [ ] Test delete with balance update
  - [ ] Test split validation
  - [ ] Test permission checks
  - [ ] Test audit logging
- [ ] Write integration tests for `transactions.py` routes
  - [ ] Test all endpoints (POST, GET, PUT, DELETE)
  - [ ] Test search and filtering
  - [ ] Test split and join operations
  - [ ] Test tag management
  - [ ] Test permission enforcement
  - [ ] Test error responses
- [ ] Write E2E tests for complete workflows
  - [ ] Create account → add transactions → split → join → delete
  - [ ] Search and filter transactions
  - [ ] Verify balance integrity throughout

**Step 7: Documentation**
- [ ] Update OpenAPI documentation (auto-generated from route docstrings)
- [ ] Add transaction examples to API docs
- [ ] Update README with transaction management section
- [ ] Document fuzzy search behavior and threshold
- [ ] Document balance calculation logic
- [ ] Document split transaction rules and validation

**Step 8: Performance Optimization**
- [ ] Benchmark search queries with 10,000+ transactions
- [ ] Verify indexes used with EXPLAIN ANALYZE
- [ ] Optimize N+1 queries (use selectinload)
- [ ] Consider adding database trigger for balance updates (optional)
- [ ] Test concurrent transaction creation (load test)

**Dependencies:**
- **Requires:** Phase 1 (authentication, users) ✅, Phase 2 (accounts, permissions) ✅
- **Blocks:** Phase 4 (categories), Phase 5 (budgets), Phase 6 (reports)

**Validation Criteria** (Phase complete when):
- [ ] All 267 acceptance criteria from Phase 3 requirements met
- [ ] All tests pass with 80%+ code coverage
- [ ] Transaction list queries return in < 500ms for 10k transactions
- [ ] Balance calculations accurate to 2 decimal places
- [ ] Fuzzy search finds results with 1-2 character typos
- [ ] All endpoints documented in OpenAPI
- [ ] Code reviewed and approved
- [ ] Migration tested on staging database
- [ ] Load testing shows acceptable performance

**Risk Factors:**
- **Risk:** Fuzzy search performance degrades with large datasets
  - **Mitigation:** Use GIN indexes, benchmark early, consider search service if needed
- **Risk:** Concurrent balance updates cause race conditions
  - **Mitigation:** Use SELECT FOR UPDATE row locks, test with concurrent requests
- **Risk:** Split validation edge cases (floating-point precision)
  - **Mitigation:** Use Decimal type throughout, validate with exact equality
- **Risk:** Large transaction volumes slow down queries
  - **Mitigation:** Proper indexing, pagination, consider partitioning if needed

**Estimated Effort:** 3-4 weeks for 1 developer (assuming Phase 1-2 complete)

- Week 1: Models, migrations, repositories (Steps 1-2)
- Week 2: Services, API routes, schemas (Steps 3-4)
- Week 3: Migration execution, testing (Steps 5-6)
- Week 4: Documentation, optimization, fixes (Steps 7-8)

---

### 4.2 Implementation Sequence

**Sequential Implementation** (no parallelization - each step builds on previous):

```
Step 1: Database Schema & Models (3 days)
   ↓
Step 2: Repository Layer (4 days)
   ↓
Step 3: Service Layer (5 days)
   ↓
Step 4: API Layer (4 days)
   ↓
Step 5: Database Migration (1 day)
   ↓
Step 6: Testing (5 days)
   ↓
Step 7: Documentation (2 days)
   ↓
Step 8: Performance Optimization (3 days)
```

**Rationale for ordering:**
- **Step 1 first:** Database schema must exist before any code can use it
- **Step 2 depends on Step 1:** Repositories query database tables
- **Step 3 depends on Step 2:** Services orchestrate repositories
- **Step 4 depends on Step 3:** API routes call services
- **Step 5 can happen after Step 1:** Migration can be written and tested early
- **Step 6 can start incrementally:** Write tests alongside implementation
- **Step 7 after implementation:** Documentation reflects final code
- **Step 8 last:** Optimization requires complete system to benchmark

**Incremental Testing Approach:**
- Write unit tests for repositories as you implement them (Step 2)
- Write unit tests for services as you implement them (Step 3)
- Write integration tests for routes as you implement them (Step 4)
- Run tests continuously during development (not just at Step 6)
- Step 6 is for comprehensive test coverage and E2E tests

**Quick Wins:**
- After Step 5 (migration), basic CRUD can be manually tested via SQL
- After Step 4, API endpoints can be tested via Swagger UI
- After Step 3, service methods can be tested in isolation

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. Single transaction table with parent-child foreign key is simpler than separate split tables or complex join tables.
  - Cached balance in account table is simpler than calculating on every query.
  - Soft delete is simpler than hard delete + audit table.

- [x] **Have we avoided premature optimization?**
  - Yes. Using database indexes and row locks is necessary optimization, not premature.
  - No caching layer added (could be future optimization if needed).
  - No sharding or partitioning (not needed at current scale).

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. Follows Phase 1-2 patterns: Repository → Service → Route architecture.
  - Uses existing mixins (TimestampMixin, SoftDeleteMixin, AuditFieldsMixin).
  - Uses existing permission system (PermissionService).
  - Uses existing audit system (AuditService).

- [x] **Can we deliver value in smaller increments?**
  - No. Transaction system requires all components to be functional:
    - Transactions without balance updates would cause data inconsistency
    - Balance updates without permission checks would be insecure
    - Search without fuzzy matching would frustrate users
    - This is MVP scope - cannot be reduced further

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. Requirements come from Phase 3 specification (user needs validated).
  - Balance integrity is critical for finance app (actual requirement).
  - Transaction splitting is requested feature (actual user need).
  - Fuzzy search addresses real usability issue (typos in merchant names).

### Alternatives Considered

**Alternative 1: Separate Split Transactions Table**
- **Approach:** Create `split_transactions` table linking parent to children
- **Why not chosen:**
  - Adds complexity with extra table and joins
  - Parent-child foreign key on `transactions` table is simpler
  - No significant benefit over self-referential foreign key
  - More code to maintain

**Alternative 2: Calculate Balance on Every Query**
- **Approach:** Remove `current_balance` from accounts, calculate from transactions each time
- **Why not chosen:**
  - Slow for accounts with many transactions (O(n) per query)
  - Violates performance requirement (< 500ms for 10k transactions)
  - Cached balance with atomic updates is faster and still consistent

**Alternative 3: Elasticsearch for Search**
- **Approach:** Index transactions in Elasticsearch for advanced search
- **Why not chosen:**
  - Adds operational complexity (another service to run)
  - PostgreSQL pg_trgm is sufficient for current scale
  - No need for advanced features (faceted search, highlights, etc.)
  - Can migrate to Elasticsearch later if needed

**Alternative 4: Hard Delete Transactions**
- **Approach:** Permanently delete transactions when user deletes
- **Why not chosen:**
  - Loses audit trail (compliance issue)
  - Cannot undo deletions
  - Balance history becomes incomplete
  - Soft delete is industry standard for finance apps

**Alternative 5: Optimistic Locking for Balance Updates**
- **Approach:** Use version numbers instead of row locks
- **Why not chosen:**
  - More complex error handling (retry logic)
  - PostgreSQL row locks are efficient and simpler
  - No benefit for typical usage patterns (low contention)

**Rationale for Proposed Approach:**
The proposed design strikes the best balance between:
- **Simplicity:** Minimal tables, straightforward relationships
- **Performance:** Cached balance, proper indexes, row-level locks
- **Maintainability:** Follows existing codebase patterns
- **Correctness:** Atomic balance updates, soft delete audit trail
- **Scalability:** Can handle 100k+ transactions per account with current design

---

## 6. References & Related Documents

### Internal Documentation
- [Phase 1 Requirements](.features/descriptions/phase-1.md) - Authentication & User Management
- [Phase 2 Requirements](.features/descriptions/phase-2.md) - Account Management
- [Phase 3 Requirements](.features/descriptions/phase-3.md) - Transaction Management (this implementation)
- [Backend Standards](.claude/standards/backend.md) - Python/FastAPI coding standards
- [Database Standards](.claude/standards/database.md) - PostgreSQL and migration standards
- [API Design Standards](.claude/standards/api.md) - RESTful API conventions
- [Testing Standards](.claude/standards/testing.md) - Test organization and coverage

### PostgreSQL Documentation
- [PostgreSQL pg_trgm Extension](https://www.postgresql.org/docs/current/pgtrgm.html) - Trigram matching for fuzzy search
- [PostgreSQL Numeric Type](https://www.postgresql.org/docs/current/datatype-numeric.html) - Decimal precision
- [PostgreSQL Row Locking](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS) - SELECT FOR UPDATE
- [PostgreSQL GIN Indexes](https://www.postgresql.org/docs/current/gin.html) - Generalized Inverted Indexes

### SQLAlchemy Documentation
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) - ORM and Core
- [Async Session Management](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - AsyncSession usage
- [SQLAlchemy Relationship Patterns](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html) - Self-referential relationships

### FastAPI Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Framework reference
- [Pydantic V2](https://docs.pydantic.dev/latest/) - Schema validation
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) - Dependency injection

### Financial Transaction Design Patterns
- [Building a Financial Ledger with Postgres](https://henrycourse.com/blog/2023/10/08/building-a-financial-ledger/) - Balance calculation patterns
- [Banking Transaction Database Design](https://ithy.com/article/banking-transaction-database-postgresql-6mu1u0pa) - PostgreSQL schema design
- [Double-Entry Bookkeeping Principles](https://en.wikipedia.org/wiki/Double-entry_bookkeeping) - Accounting fundamentals

### Fuzzy Search Implementation
- [Optimizing PostgreSQL Full-Text Search with Fuzzy Matching](https://blog.poespas.me/posts/2025/02/15/postgresql-full-text-search-fuzzy-matching/) - Recent 2025 guide
- [PostgreSQL Fuzzy Search Best Practices](https://www.alibabacloud.com/blog/postgresql-fuzzy-search-best-practices-single-word-double-word-and-multi-word-fuzzy-search-methods_595635) - Performance optimization

### Security & Compliance
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/) - API security best practices
- [PCI DSS Requirements](https://www.pcisecuritystandards.org/) - Financial data handling (if storing card data)
- [GDPR Compliance for Financial Apps](https://gdpr.eu/) - Data retention and user rights

### Testing Resources
- [Pytest Documentation](https://docs.pytest.org/) - Testing framework
- [Pytest-Asyncio](https://pytest-asyncio.readthedocs.io/) - Async test support
- [Testing SQLAlchemy Applications](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites) - Test database setup

### Performance & Monitoring
- [PostgreSQL EXPLAIN ANALYZE](https://www.postgresql.org/docs/current/sql-explain.html) - Query performance analysis
- [Database Indexing Strategies](https://use-the-index-luke.com/) - Index design patterns
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/deployment/performance/) - Production optimization

---

## 7. Additional Considerations

### Rate Limiting
Consider adding rate limits to expensive endpoints:
- List transactions: 60 requests/minute (search queries can be heavy)
- Create transaction: 120 requests/minute (normal usage)
- Split transaction: 30 requests/minute (less frequent operation)

### Monitoring & Alerting
Add monitoring for:
- Balance calculation errors (cached vs. calculated mismatch)
- Slow queries (> 500ms for transaction searches)
- Failed transaction creation (validation errors)
- High volume of deletions (potential data loss)

### Future Enhancements (Post-Phase 3)
- **Recurring Transactions** (Phase 4+): Auto-create transactions on schedule
- **Transaction Categories** (Phase 4): Hierarchical category system
- **Bulk Import** (Phase 5+): CSV/OFX import for bank statements
- **Transaction Attachments** (Phase 6+): Upload receipts/invoices
- **Multi-Account Transfers** (Phase 4+): Link two transactions as transfer pair
- **Smart Merchant Detection** (Phase 5+): Auto-categorize based on merchant
- **Duplicate Detection** (Phase 5+): Warn user about potential duplicates

### Security Considerations
- **SQL Injection:** Mitigated by SQLAlchemy parameterized queries
- **Mass Assignment:** Prevented by Pydantic schema validation (only allowed fields)
- **Unauthorized Access:** Prevented by permission checks in service layer
- **Data Leakage:** Prevented by filtering queries by account_id and permission checks
- **Audit Trail:** All operations logged for forensic analysis

### Data Migration
If migrating from existing system:
- Create data migration script to import transactions
- Validate balance calculations after import
- Preserve original transaction IDs if possible
- Handle missing/invalid data gracefully

---

## 8. Success Metrics

**Functional Metrics:**
- All 267 acceptance criteria from Phase 3 requirements met ✅
- All tests pass with 80%+ code coverage ✅
- All API endpoints documented in OpenAPI ✅

**Performance Metrics:**
- Transaction list queries return in < 500ms for 10,000 transactions
- Transaction creation (with balance update) completes in < 200ms
- Fuzzy search finds matches in < 300ms for 10,000 transactions
- Balance calculation (recalculate) completes in < 100ms for 1,000 transactions

**Quality Metrics:**
- Zero balance calculation errors (cached = calculated)
- Zero data loss (soft delete preserves all data)
- Zero unauthorized access (permission checks enforced)
- All audit logs captured (100% coverage for mutating operations)

**User Experience Metrics:**
- Fuzzy search finds transactions with 1-2 character typos
- Tag autocomplete provides relevant suggestions
- Search filters combine intuitively (AND logic)
- Split validation provides clear error messages

---

## 9. Appendix

### Glossary
- **Transaction:** Record of financial activity (income, expense, transfer, etc.)
- **Split Transaction:** Single transaction broken into multiple parts for detailed tracking
- **Soft Delete:** Marking record as deleted without removing from database (sets `deleted_at`)
- **Balance Calculation:** Sum of all non-deleted transactions + opening balance
- **Fuzzy Search:** Text search that finds approximate matches (handles typos)
- **Trigram:** Sequence of 3 consecutive characters used for similarity matching
- **Row Lock:** Database lock preventing concurrent updates to same row
- **Atomic Operation:** All-or-nothing database operation (transaction + balance update together)

### Acronyms
- **CRUD:** Create, Read, Update, Delete
- **ORM:** Object-Relational Mapping
- **UUID:** Universally Unique Identifier
- **ISO 4217:** International standard for currency codes
- **GIN:** Generalized Inverted Index (PostgreSQL index type)
- **ACID:** Atomicity, Consistency, Isolation, Durability
- **API:** Application Programming Interface
- **REST:** Representational State Transfer

---

**Plan Prepared By:** Claude Code Agent
**Plan Review Status:** Ready for Implementation
**Implementation Start:** After user approval
**Estimated Completion:** 3-4 weeks from start date

