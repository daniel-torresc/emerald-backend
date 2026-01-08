# Implementation Plan: Link Accounts to Financial Institutions

**Feature ID**: feat-03
**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: Feature 1.1 (Financial Institutions Master Data)
**Estimated Effort**: 1.5 weeks (1 developer)

---

## 1. Executive Summary

This implementation replaces the free-text `bank_name` field in the accounts table with a **mandatory** foreign key relationship to the `financial_institutions` master data table. This change standardizes institution data across all user accounts, eliminating data inconsistency issues like "Chase", "chase bank", and "JPMorgan Chase" referring to the same institution.

### Primary Objectives

1. **Enforce Data Standardization**: All accounts must reference a validated financial institution from the master data table
2. **Enable Rich Metadata**: Provide standardized institution names, logos, SWIFT codes, and routing numbers for all accounts
3. **Improve Analytics**: Enable institution-based filtering, grouping, and reporting across the platform
4. **Maintain Data Integrity**: Prevent orphaned accounts through ON DELETE RESTRICT constraints

### Expected Outcomes

- **Zero** accounts with NULL or invalid institution references (enforced by NOT NULL constraint)
- **100%** of accounts linked to standardized financial institution data
- **Improved** visual account organization through institution logos and names
- **Enhanced** filtering and grouping capabilities for users
- **Better** data quality for analytics and reporting

### Success Criteria

- All accounts have valid `financial_institution_id` references
- The `bank_name` field is completely removed from accounts table
- API endpoints enforce mandatory institution selection
- Users cannot create accounts without selecting an institution
- Foreign key constraint with ON DELETE RESTRICT prevents accidental institution deletion
- All tests pass with 80%+ coverage

---

## 2. Technical Architecture

### 2.1 System Design Overview

This feature modifies the existing accounts domain by adding a mandatory relationship to the financial institutions master data:

```
┌─────────────────────────────────────┐
│  financial_institutions             │
│  (Master Data - Read-Only for Users)│
├─────────────────────────────────────┤
│  id (PK)                            │
│  name                               │
│  short_name                         │
│  logo_url                           │
│  swift_code                         │
│  routing_number                     │
│  country_code                       │
│  institution_type                   │
│  is_active                          │
└─────────────────────────────────────┘
          ▲
          │ 1:N relationship
          │ (ON DELETE RESTRICT)
          │
┌─────────────────────────────────────┐
│  accounts                           │
│  (Transactional Data - User-Owned)  │
├─────────────────────────────────────┤
│  id (PK)                            │
│  user_id (FK)                       │
│  financial_institution_id (FK) ◄────┘
│  account_name                       │
│  account_type                       │
│  currency                           │
│  opening_balance                    │
│  current_balance                    │
│  bank_name (REMOVED)                │ ← Remove this field
│  ...                                │
└─────────────────────────────────────┘
```

**Data Flow**:
1. User creates/updates account → selects institution from master list
2. API validates institution exists and is active
3. Account saved with `financial_institution_id` foreign key
4. Account queries automatically include institution details via eager loading
5. Institution deletion blocked if linked accounts exist (RESTRICT)

### 2.2 Technology Decisions

#### SQLAlchemy Relationship Configuration

**Purpose**: Define the one-to-many relationship between financial institutions and accounts

**Why this choice**:
- SQLAlchemy 2.0+ provides async-first ORM with excellent relationship handling
- `lazy='selectin'` prevents N+1 query problems in async contexts (recommended for async SQLAlchemy as per [SQLAlchemy 2.0 documentation](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html))
- Type-safe relationships using `Mapped[...]` type hints
- Already established in the codebase with proven patterns

**Version**: SQLAlchemy 2.0+ (current project dependency)

**Implementation Pattern**:
```python
# In Account model
financial_institution: Mapped["FinancialInstitution"] = relationship(
    "FinancialInstitution",
    foreign_keys=[financial_institution_id],
    lazy="selectin",  # Async-safe eager loading
)

# In FinancialInstitution model
accounts: Mapped[list["Account"]] = relationship(
    "Account",
    back_populates="financial_institution",
    lazy="select",  # Institutions rarely need to list all accounts
)
```

**Alternatives considered**:
- `lazy='joined'`: Would use JOIN instead of separate SELECT, but can cause cartesian products with multiple eager loads
- `lazy='raise'`: Would require explicit loading everywhere, too verbose for frequently accessed data
- Raw SQL: Rejected due to loss of type safety and ORM benefits

#### Foreign Key ON DELETE RESTRICT

**Purpose**: Prevent deletion of institutions that have linked accounts

**Why this choice**:
- Protects data integrity by preventing orphaned account records
- Forces explicit handling of account reassignment before institution deletion
- Aligns with [PostgreSQL best practices](https://www.postgresql.org/docs/current/ddl-constraints.html) for independent entity relationships
- Accounts and institutions represent independent objects that shouldn't cascade delete

**Rationale**: According to [database constraint best practices](https://dba.stackexchange.com/questions/254605), if two tables represent independent objects (accounts exist independently of institution master data), then RESTRICT is more appropriate. An application that wants to delete both must be explicit and run separate operations.

**Alternatives considered**:
- `ON DELETE CASCADE`: Would auto-delete all accounts when institution deleted - dangerous for transactional data
- `ON DELETE SET NULL`: Would create NULL institution references - violates mandatory requirement
- `ON DELETE SET DEFAULT`: Would require a "default" institution - adds unnecessary complexity

### 2.3 File Structure

```
src/
├── models/
│   ├── account.py                    # Modified: Add financial_institution_id, remove bank_name
│   └── financial_institution.py      # Modified: Add accounts relationship
├── schemas/
│   ├── account.py                    # Modified: Update validation schemas
│   └── financial_institution.py      # No changes needed
├── repositories/
│   ├── account_repository.py         # Modified: Add institution filtering
│   └── financial_institution_repository.py  # No changes needed
├── services/
│   ├── account_service.py            # Modified: Add institution validation
│   └── financial_institution_service.py     # No changes needed
├── api/routes/
│   ├── accounts.py                   # Modified: Update request/response schemas
│   └── financial_institutions.py     # No changes needed
alembic/versions/
└── YYYYMMDD_HHMMSS_link_accounts_to_institutions.py  # New migration
tests/
├── integration/
│   ├── test_account_routes.py        # Modified: Add institution tests
│   └── test_financial_institution_routes.py  # No changes needed
└── unit/
    └── repositories/
        └── test_account_repository.py  # Modified: Add institution filtering tests
```

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Database Schema Changes

**Files Involved**:
- `alembic/versions/YYYYMMDD_HHMMSS_link_accounts_to_institutions.py`
- `src/models/account.py`
- `src/models/financial_institution.py`

**Purpose**: Modify the accounts table to replace free-text bank_name with foreign key to financial_institutions

**Implementation Requirements**:

1. **Alembic Migration**:
   - Create new migration file with descriptive name
   - Step 1: DELETE all existing accounts (development data only - safe because no production data exists)
   - Step 2: ADD COLUMN `financial_institution_id UUID NOT NULL`
   - Step 3: ADD FOREIGN KEY constraint with ON DELETE RESTRICT
   - Step 4: CREATE INDEX on `financial_institution_id`
   - Step 5: DROP COLUMN `bank_name`
   - All changes in single transaction for atomicity

   ```python
   def upgrade():
       # Step 1: Clean slate - delete existing test data
       op.execute("DELETE FROM accounts")

       # Step 2: Add new column (NOT NULL from start)
       op.add_column(
           'accounts',
           sa.Column('financial_institution_id', postgresql.UUID(as_uuid=True), nullable=False)
       )

       # Step 3: Add foreign key with RESTRICT
       op.create_foreign_key(
           'fk_accounts_financial_institution',
           'accounts',
           'financial_institutions',
           ['financial_institution_id'],
           ['id'],
           ondelete='RESTRICT'
       )

       # Step 4: Add index for query performance
       op.create_index(
           'idx_accounts_financial_institution_id',
           'accounts',
           ['financial_institution_id']
       )

       # Step 5: Remove old column
       op.drop_column('accounts', 'bank_name')

   def downgrade():
       # Reverse all changes
       op.add_column('accounts', sa.Column('bank_name', sa.String(100), nullable=True))
       op.drop_index('idx_accounts_financial_institution_id', table_name='accounts')
       op.drop_constraint('fk_accounts_financial_institution', 'accounts', type_='foreignkey')
       op.drop_column('accounts', 'financial_institution_id')
   ```

2. **SQLAlchemy Model Updates**:

   **Account Model** (`src/models/account.py`):
   ```python
   # Add new field (around line 130, after user_id)
   financial_institution_id: Mapped[uuid.UUID] = mapped_column(
       UUID(as_uuid=True),
       ForeignKey("financial_institutions.id", ondelete="RESTRICT"),
       nullable=False,
       index=True,
       comment="Financial institution this account belongs to (mandatory)",
   )

   # Remove bank_name field (currently around line 181-185)
   # DELETE THESE LINES:
   # bank_name: Mapped[str | None] = mapped_column(
   #     String(100),
   #     nullable=True,
   #     comment="Name of the financial institution",
   # )

   # Add relationship (around line 210, after owner relationship)
   financial_institution: Mapped["FinancialInstitution"] = relationship(
       "FinancialInstitution",
       foreign_keys=[financial_institution_id],
       lazy="selectin",  # Async-safe eager loading
       back_populates="accounts",
   )

   # Update __repr__ method (around line 230)
   def __repr__(self) -> str:
       """String representation of Account."""
       # Remove bank_info variable
       return (
           f"Account(id={self.id}, name={self.account_name}, "
           f"type={self.account_type.value}, balance={self.current_balance} {self.currency}, "
           f"institution={self.financial_institution.short_name})"
       )
   ```

   **FinancialInstitution Model** (`src/models/financial_institution.py`):
   ```python
   # Add relationship (around line 140, after is_active field)
   accounts: Mapped[list["Account"]] = relationship(
       "Account",
       back_populates="financial_institution",
       lazy="select",  # Don't eager load accounts from institution side
   )
   ```

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Account creation without institution → Return 400 with clear error message
   - [ ] Handle case: Invalid institution_id UUID format → Return 422 validation error
   - [ ] Handle case: Institution ID doesn't exist → Return 404 "Institution not found"
   - [ ] Handle case: Institution is inactive (is_active=false) → Return 400 "Institution is not active"
   - [ ] Handle case: Attempt to delete institution with linked accounts → Return 409 "Cannot delete institution with linked accounts"
   - [ ] Handle case: Account update removing institution → Return 400 "Institution is required"
   - [ ] Handle case: Migration runs multiple times → Idempotent (safe to re-run)

4. **Dependencies**:
   - Internal: Requires financial_institutions table to exist and be seeded
   - External: PostgreSQL with UUID support, SQLAlchemy 2.0+

5. **Testing Requirements**:
   - [ ] Unit test: Migration upgrade creates column, FK, index, removes bank_name
   - [ ] Unit test: Migration downgrade reverses all changes
   - [ ] Unit test: Migration is idempotent (can run twice safely)
   - [ ] Unit test: Cannot insert account without financial_institution_id
   - [ ] Unit test: Cannot insert account with NULL financial_institution_id
   - [ ] Unit test: Cannot insert account with invalid institution_id
   - [ ] Unit test: Foreign key constraint enforces referential integrity
   - [ ] Unit test: ON DELETE RESTRICT prevents institution deletion with accounts
   - [ ] Integration test: Create account with valid institution succeeds
   - [ ] Integration test: bank_name column is gone from table

**Acceptance Criteria**:
- [ ] `financial_institution_id` column exists in accounts table (UUID, NOT NULL)
- [ ] Foreign key constraint exists with ON DELETE RESTRICT
- [ ] Index exists on `financial_institution_id`
- [ ] `bank_name` column completely removed from accounts table
- [ ] Migration runs successfully without errors
- [ ] Migration is reversible (downgrade works)
- [ ] All existing accounts deleted (development data only)
- [ ] Cannot create account without institution reference

**Implementation Notes**:
- This is a **destructive migration** - only safe because no production data exists
- In production, would need data migration to map bank_name to institution_id
- Review Alembic autogenerate output carefully - it may not detect all changes
- Test migration on development database copy first
- Ensure financial_institutions table has seed data before running migration

---

#### Component: Pydantic Schema Updates

**Files Involved**:
- `src/schemas/account.py`
- `src/schemas/financial_institution.py` (read-only, for reference)

**Purpose**: Update API request/response schemas to handle mandatory institution field

**Implementation Requirements**:

1. **Core Schema Changes**:

   **AccountBase** (base schema):
   ```python
   # Remove bank_name field (around line 52-57)
   # DELETE THESE LINES:
   # bank_name: str | None = Field(
   #     default=None,
   #     max_length=100,
   #     description="Name of the financial institution",
   #     examples=["Chase Bank", "Bank of America", "Wells Fargo"],
   # )
   ```

   **AccountCreate** (creation schema):
   ```python
   # Add new REQUIRED field (around line 98, before opening_balance)
   financial_institution_id: uuid.UUID = Field(
       description="Financial institution ID (required, must reference active institution)",
       examples=["550e8400-e29b-41d4-a716-446655440000"],
   )

   # Add validator for institution_id format
   @field_validator("financial_institution_id")
   @classmethod
   def validate_financial_institution_id(cls, value: uuid.UUID) -> uuid.UUID:
       """
       Validate financial institution ID is a valid UUID.

       Business validation (exists, is_active) happens in service layer.
       """
       # UUID validation is automatic from type hint
       # Just ensure it's not nil UUID
       if value == uuid.UUID('00000000-0000-0000-0000-000000000000'):
           raise ValueError("Financial institution ID cannot be nil UUID")
       return value
   ```

   **AccountUpdate** (update schema):
   ```python
   # Add optional field for updating institution (around line 198)
   financial_institution_id: uuid.UUID | None = Field(
       default=None,
       description="New financial institution ID (optional, must reference active institution)",
       examples=["550e8400-e29b-41d4-a716-446655440000"],
   )

   # Add validator
   @field_validator("financial_institution_id")
   @classmethod
   def validate_financial_institution_id(cls, value: uuid.UUID | None) -> uuid.UUID | None:
       """Validate institution ID if provided."""
       if value is not None and value == uuid.UUID('00000000-0000-0000-0000-000000000000'):
           raise ValueError("Financial institution ID cannot be nil UUID")
       return value
   ```

   **AccountResponse** (response schema):
   ```python
   # Remove bank_name (currently around line 318)

   # Add institution details (around line 305, after user_id)
   financial_institution_id: uuid.UUID = Field(
       description="Financial institution ID"
   )

   # Add nested institution object (optional - for rich responses)
   # This requires importing FinancialInstitutionResponse
   from src.schemas.financial_institution import FinancialInstitutionResponse

   financial_institution: FinancialInstitutionResponse = Field(
       description="Financial institution details (name, logo, etc.)"
   )
   ```

   **AccountListItem** (list response):
   ```python
   # Remove bank_name (around line 358)

   # Add institution reference (around line 350)
   financial_institution_id: uuid.UUID

   # Optionally add minimal institution info for UI
   financial_institution_name: str = Field(
       description="Institution display name for UI"
   )
   financial_institution_logo: str | None = Field(
       description="Institution logo URL for UI"
   )
   ```

   **AccountFilterParams** (filtering):
   ```python
   # Add new filter (around line 375, after account_type)
   financial_institution_id: uuid.UUID | None = Field(
       default=None,
       description="Filter by financial institution",
   )
   ```

2. **Data Handling**:
   - Input validation: Pydantic automatically validates UUID format
   - Business validation: Service layer checks institution exists and is_active
   - Output format: Include institution details in responses via relationship
   - State management: Institution is immutable after account creation (design decision for data integrity)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: financial_institution_id missing on create → Pydantic raises 422 validation error
   - [ ] Handle case: financial_institution_id is null string → Pydantic raises 422 validation error
   - [ ] Handle case: financial_institution_id is invalid UUID → Pydantic raises 422 validation error
   - [ ] Handle case: financial_institution_id is nil UUID (all zeros) → Custom validator raises ValueError
   - [ ] Handle case: Nested institution object missing from response → Set default or raise error in service

4. **Dependencies**:
   - Internal: Requires FinancialInstitutionResponse schema for nested responses
   - External: Pydantic v2.x with UUID support

5. **Testing Requirements**:
   - [ ] Unit test: AccountCreate with valid institution_id passes validation
   - [ ] Unit test: AccountCreate without institution_id raises ValidationError
   - [ ] Unit test: AccountCreate with nil UUID raises ValidationError
   - [ ] Unit test: AccountCreate with invalid UUID format raises ValidationError
   - [ ] Unit test: AccountUpdate with valid institution_id passes validation
   - [ ] Unit test: AccountUpdate with nil UUID raises ValidationError
   - [ ] Unit test: AccountResponse includes financial_institution field
   - [ ] Unit test: AccountListItem includes institution_name and logo
   - [ ] Unit test: AccountFilterParams with institution_id filter works

**Acceptance Criteria**:
- [ ] `financial_institution_id` is REQUIRED field in AccountCreate schema
- [ ] `financial_institution_id` is optional field in AccountUpdate schema
- [ ] `bank_name` field completely removed from all account schemas
- [ ] AccountResponse includes nested institution details
- [ ] AccountListItem includes institution name and logo for UI
- [ ] Validation errors are clear and actionable
- [ ] All schema validators have docstrings

**Implementation Notes**:
- Consider making institution_id **immutable** after creation (not in AccountUpdate) for data integrity
- Include nested institution object in responses to reduce API calls
- Use `Field(..., examples=[...])` for OpenAPI documentation
- Ensure error messages guide users to provide valid institution IDs

---

#### Component: Repository Layer Updates

**Files Involved**:
- `src/repositories/account_repository.py`
- `src/repositories/financial_institution_repository.py` (read-only, for reference)

**Purpose**: Add database operations for institution-filtered account queries

**Implementation Requirements**:

1. **Core Repository Methods**:

   **Update `get_by_user` method** (around line 80):
   ```python
   async def get_by_user(
       self,
       user_id: uuid.UUID,
       skip: int = 0,
       limit: int = 20,
       is_active: bool | None = None,
       account_type: AccountType | None = None,
       financial_institution_id: uuid.UUID | None = None,  # NEW parameter
   ) -> list[Account]:
       """
       Get all accounts owned by user with optional filters.

       Includes eager loading of financial_institution relationship.

       Args:
           user_id: User ID to filter by
           skip: Number of records to skip (pagination)
           limit: Maximum number of records to return
           is_active: Filter by active status (None = all)
           account_type: Filter by account type (None = all)
           financial_institution_id: Filter by financial institution (None = all)

       Returns:
           List of Account instances with eager-loaded institution
       """
       stmt = (
           select(Account)
           .where(Account.user_id == user_id)
           .options(selectinload(Account.financial_institution))  # Eager load
       )

       if is_active is not None:
           stmt = stmt.where(Account.is_active == is_active)

       if account_type is not None:
           stmt = stmt.where(Account.account_type == account_type)

       # NEW: Filter by institution
       if financial_institution_id is not None:
           stmt = stmt.where(Account.financial_institution_id == financial_institution_id)

       stmt = stmt.offset(skip).limit(limit).order_by(Account.created_at.desc())

       result = await self.session.execute(stmt)
       return list(result.scalars().all())
   ```

   **Update `get_shared_with_user` method** (around line 120):
   ```python
   async def get_shared_with_user(
       self,
       user_id: uuid.UUID,
       is_active: bool | None = None,
       account_type: AccountType | None = None,
       financial_institution_id: uuid.UUID | None = None,  # NEW parameter
   ) -> list[Account]:
       """
       Get accounts shared with user (via account_shares).

       Args:
           user_id: User ID to find shared accounts for
           is_active: Filter by active status (None = all)
           account_type: Filter by account type (None = all)
           financial_institution_id: Filter by institution (None = all)

       Returns:
           List of Account instances shared with user
       """
       stmt = (
           select(Account)
           .join(AccountShare, Account.id == AccountShare.account_id)
           .where(AccountShare.user_id == user_id)
           .options(selectinload(Account.financial_institution))  # Eager load
       )

       if is_active is not None:
           stmt = stmt.where(Account.is_active == is_active)

       if account_type is not None:
           stmt = stmt.where(Account.account_type == account_type)

       # NEW: Filter by institution
       if financial_institution_id is not None:
           stmt = stmt.where(Account.financial_institution_id == financial_institution_id)

       stmt = stmt.order_by(Account.created_at.desc())

       result = await self.session.execute(stmt)
       return list(result.scalars().all())
   ```

   **Add new method for institution validation**:
   ```python
   async def validate_institution_active(
       self,
       institution_id: uuid.UUID,
   ) -> bool:
       """
       Check if financial institution exists and is active.

       Args:
           institution_id: Institution ID to validate

       Returns:
           True if institution exists and is_active, False otherwise
       """
       from src.models.financial_institution import FinancialInstitution

       stmt = select(FinancialInstitution.is_active).where(
           FinancialInstitution.id == institution_id
       )

       result = await self.session.execute(stmt)
       is_active = result.scalar_one_or_none()

       # Returns None if not found, False if found but inactive, True if active
       return is_active is True
   ```

2. **Eager Loading Strategy**:
   - Use `selectinload(Account.financial_institution)` in all account queries
   - Prevents N+1 query problem when accessing institution details
   - Async-safe loading strategy (recommended pattern for SQLAlchemy async)

3. **Edge Cases & Error Handling**:
   - [ ] Handle case: Query with NULL institution filter → Return all accounts (None = no filter)
   - [ ] Handle case: Query with invalid institution_id → Return empty list (no matches)
   - [ ] Handle case: Institution exists but is_active=false → Validation returns False
   - [ ] Handle case: Eager loading fails → Return accounts without institution (graceful degradation)
   - [ ] Handle case: Multiple filters combined → All filters apply (AND logic)

4. **Dependencies**:
   - Internal: Requires Account and FinancialInstitution models with relationship defined
   - External: SQLAlchemy 2.0+ async, asyncpg driver

5. **Testing Requirements**:
   - [ ] Unit test: get_by_user with institution filter returns correct accounts
   - [ ] Unit test: get_by_user without institution filter returns all accounts
   - [ ] Unit test: get_shared_with_user with institution filter works
   - [ ] Unit test: validate_institution_active returns True for active institution
   - [ ] Unit test: validate_institution_active returns False for inactive institution
   - [ ] Unit test: validate_institution_active returns False for non-existent institution
   - [ ] Unit test: Eager loading includes institution in query results
   - [ ] Unit test: Multiple filters (is_active + account_type + institution) work together
   - [ ] Integration test: Query with institution filter returns expected results

**Acceptance Criteria**:
- [ ] All account queries include `financial_institution_id` filter parameter
- [ ] Queries eager-load institution relationship to prevent N+1
- [ ] Institution validation method exists and works correctly
- [ ] Filters work individually and in combination
- [ ] No additional queries when accessing account.financial_institution
- [ ] Repository methods have updated docstrings

**Implementation Notes**:
- Use `selectinload()` not `joinedload()` for one-to-many relationships in async context
- Keep institution validation in repository layer (data access concern)
- Consider adding count methods with institution filtering for pagination
- Ensure queries maintain existing soft-delete filtering from BaseRepository

---

#### Component: Service Layer Updates

**Files Involved**:
- `src/services/account_service.py`
- `src/services/financial_institution_service.py` (read-only, for reference)

**Purpose**: Add business logic for mandatory institution validation and account management

**Implementation Requirements**:

1. **Update `create_account` method** (around line 71):
   ```python
   async def create_account(
       self,
       user_id: uuid.UUID,
       account_name: str,
       account_type: AccountType,
       currency: str,
       opening_balance: Decimal,
       financial_institution_id: uuid.UUID,  # NEW REQUIRED parameter
       current_user: User,
       bank_name: str | None = None,  # REMOVE this parameter
       iban: str | None = None,
       color_hex: str = "#818E8F",
       icon_url: HttpUrl | None = None,
       notes: str | None = None,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None,
   ) -> Account:
       """
       Create new financial account for user.

       Args:
           user_id: ID of user who will own the account
           account_name: Descriptive account name (unique per user)
           account_type: Type of account
           currency: ISO 4217 currency code
           opening_balance: Initial balance
           financial_institution_id: Financial institution ID (REQUIRED)
           current_user: Authenticated user (for audit)
           iban: IBAN number (optional, will be encrypted)
           color_hex: Hex color for UI
           icon_url: Account icon URL
           notes: User notes
           request_id: Request ID for correlation
           ip_address: Client IP for audit
           user_agent: Client user agent for audit

       Returns:
           Created Account instance

       Raises:
           AlreadyExistsError: Account name already exists
           NotFoundError: Institution not found
           ValidationError: Institution is inactive
       """
       # Validate account name uniqueness (existing logic)
       if await self.account_repo.exists_by_name(user_id, account_name):
           logger.warning(...)
           raise AlreadyExistsError(...)

       # Validate currency format (existing logic)
       if not (len(currency) == 3 and currency.isalpha() and currency.isupper()):
           logger.warning(...)
           raise ValueError(...)

       # NEW: Validate financial institution exists and is active
       is_valid = await self.account_repo.validate_institution_active(
           financial_institution_id
       )
       if not is_valid:
           logger.warning(
               f"User {user_id} attempted to create account with invalid/inactive "
               f"institution: {financial_institution_id}"
           )
           raise ValidationError(
               "Financial institution not found or is not active. "
               "Please select a different institution."
           )

       # Process IBAN (existing logic)
       encrypted_iban = None
       iban_last_four = None
       if iban:
           try:
               encrypted_iban = self.encryption_service.encrypt(iban)
               iban_last_four = iban[-4:] if len(iban) >= 4 else iban
               logger.info("IBAN encrypted successfully")
           except Exception as e:
               logger.error(f"IBAN encryption failed: {e}")
               raise EncryptionError("Failed to encrypt IBAN") from e

       # Create account
       account = await self.account_repo.create(
           user_id=user_id,
           account_name=account_name,
           account_type=account_type,
           currency=currency,
           opening_balance=opening_balance,
           current_balance=opening_balance,
           financial_institution_id=financial_institution_id,  # NEW field
           is_active=True,
           color_hex=color_hex,
           icon_url=icon_url,
           bank_name=bank_name,  # REMOVE this line
           iban=encrypted_iban,
           iban_last_four=iban_last_four,
           notes=notes,
           created_by=current_user.id,
           updated_by=current_user.id,
       )

       logger.info(
           f"Created account {account.id} ({account.account_name}) "
           f"for user {user_id} at institution {financial_institution_id}"
       )

       # Update audit log to include institution
       await self.audit_service.log_event(
           user_id=current_user.id,
           action=AuditAction.CREATE,
           entity_type="account",
           entity_id=account.id,
           description=f"Created account '{account.account_name}' at {account.financial_institution.short_name}",
           extra_metadata={
               "account_name": account.account_name,
               "account_type": account.account_type.value,
               "currency": account.currency,
               "opening_balance": str(opening_balance),
               "financial_institution_id": str(financial_institution_id),  # NEW
               "financial_institution_name": account.financial_institution.short_name,  # NEW
           },
           ip_address=ip_address,
           user_agent=user_agent,
           request_id=request_id,
       )

       return account
   ```

2. **Update `update_account` method** (around line 319):
   ```python
   async def update_account(
       self,
       account_id: uuid.UUID,
       current_user: User,
       account_name: str | None = None,
       is_active: bool | None = None,
       financial_institution_id: uuid.UUID | None = None,  # NEW parameter
       color_hex: str | None = None,
       icon_url: HttpUrl | None = None,
       notes: str | None = None,
       request_id: str | None = None,
       ip_address: str | None = None,
       user_agent: str | None = None,
   ) -> Account:
       """
       Update account details.

       Updateable fields: account_name, is_active, financial_institution_id,
                          color_hex, icon_url, notes
       Immutable fields: currency, balances, account_type, iban

       Args:
           account_id: Account ID to update
           current_user: Authenticated user
           account_name: New account name (optional)
           is_active: New active status (optional)
           financial_institution_id: New institution ID (optional)
           color_hex: New color (optional)
           icon_url: New icon (optional)
           notes: New notes (optional)
           request_id: Request ID for correlation
           ip_address: Client IP for audit
           user_agent: Client user agent for audit

       Returns:
           Updated Account instance

       Raises:
           NotFoundError: Account not found or no access
           AlreadyExistsError: New account name already exists
           ValidationError: New institution is inactive
       """
       # Get account and check permission (existing logic)
       account = await self.get_account(account_id, current_user, request_id)

       # Check ownership (existing logic)
       if account.user_id != current_user.id:
           logger.warning(...)
           raise NotFoundError("Account")

       # Track changes (existing logic)
       changes = {}

       # Update account name (existing logic)
       if account_name is not None and account_name != account.account_name:
           if await self.account_repo.exists_by_name(
               account.user_id, account_name, exclude_id=account_id
           ):
               raise AlreadyExistsError(...)
           changes["account_name"] = {"old": account.account_name, "new": account_name}
           account.account_name = account_name

       # Update is_active (existing logic)
       if is_active is not None and is_active != account.is_active:
           changes["is_active"] = {"old": account.is_active, "new": is_active}
           account.is_active = is_active

       # NEW: Update financial institution
       if (
           financial_institution_id is not None
           and financial_institution_id != account.financial_institution_id
       ):
           # Validate new institution exists and is active
           is_valid = await self.account_repo.validate_institution_active(
               financial_institution_id
           )
           if not is_valid:
               logger.warning(
                   f"User {current_user.id} attempted to update account {account_id} "
                   f"with invalid/inactive institution: {financial_institution_id}"
               )
               raise ValidationError(
                   "Financial institution not found or is not active. "
                   "Please select a different institution."
               )

           changes["financial_institution_id"] = {
               "old": str(account.financial_institution_id),
               "new": str(financial_institution_id),
           }
           account.financial_institution_id = financial_institution_id

       # Update other fields (existing logic: color_hex, icon_url, notes)
       # ... existing code ...

       # If no changes, return as-is (existing logic)
       if not changes:
           return account

       # Update audit fields and save (existing logic)
       account.updated_by = current_user.id
       account = await self.account_repo.update(account)

       logger.info(f"Updated account {account.id}: {changes}")

       # Log audit event (existing logic with changes)
       await self.audit_service.log_event(
           user_id=current_user.id,
           action=AuditAction.UPDATE,
           entity_type="account",
           entity_id=account.id,
           description=f"Updated account '{account.account_name}'",
           extra_metadata={"changes": changes},
           ip_address=ip_address,
           user_agent=user_agent,
           request_id=request_id,
       )

       return account
   ```

3. **Update `list_accounts` method** (around line 242):
   ```python
   async def list_accounts(
       self,
       user_id: uuid.UUID,
       current_user: User,
       skip: int = 0,
       limit: int = 20,
       is_active: bool | None = None,
       account_type: AccountType | None = None,
       financial_institution_id: uuid.UUID | None = None,  # NEW parameter
   ) -> list[Account]:
       """
       List all accounts for user with pagination and filtering.

       Args:
           user_id: User ID
           current_user: Authenticated user
           skip: Pagination skip
           limit: Pagination limit
           is_active: Filter by active status
           account_type: Filter by account type
           financial_institution_id: Filter by institution (NEW)

       Returns:
           List of Account instances

       Raises:
           PermissionError: User can only list own accounts
       """
       # Permission check (existing logic)
       if user_id != current_user.id and not current_user.is_admin:
           raise PermissionError("You can only list your own accounts")

       # Enforce max limit (existing logic)
       if limit > 100:
           limit = 100

       # Get owned accounts with NEW institution filter
       owned_accounts = await self.account_repo.get_by_user(
           user_id=user_id,
           skip=skip,
           limit=limit,
           is_active=is_active,
           account_type=account_type,
           financial_institution_id=financial_institution_id,  # NEW
       )

       # Get shared accounts with NEW institution filter
       shared_accounts = await self.account_repo.get_shared_with_user(
           user_id=user_id,
           is_active=is_active,
           account_type=account_type,
           financial_institution_id=financial_institution_id,  # NEW
       )

       # Combine and deduplicate (existing logic)
       # ... existing code ...

       return all_accounts[skip : skip + limit] if skip > 0 else all_accounts[:limit]
   ```

4. **Edge Cases & Error Handling**:
   - [ ] Validate: financial_institution_id cannot be nil UUID
   - [ ] Validate: Institution must exist in database
   - [ ] Validate: Institution must be active (is_active=true)
   - [ ] Error: Institution not found → Raise NotFoundError with helpful message
   - [ ] Error: Institution inactive → Raise ValidationError with suggestion to select different institution
   - [ ] Error: Attempt to set institution_id to NULL → Raise ValidationError (field is mandatory)

5. **Dependencies**:
   - Internal: Requires AccountRepository with validate_institution_active method
   - Internal: Requires FinancialInstitution model for eager-loaded data access
   - External: Async SQLAlchemy session

6. **Testing Requirements**:
   - [ ] Unit test: create_account with valid institution succeeds
   - [ ] Unit test: create_account without institution raises ValidationError
   - [ ] Unit test: create_account with inactive institution raises ValidationError
   - [ ] Unit test: create_account with non-existent institution raises ValidationError
   - [ ] Unit test: update_account with valid new institution succeeds
   - [ ] Unit test: update_account with inactive institution raises ValidationError
   - [ ] Unit test: list_accounts with institution filter returns correct accounts
   - [ ] Unit test: list_accounts without institution filter returns all accounts
   - [ ] Integration test: Creating account logs institution in audit trail
   - [ ] Integration test: Updating institution logs change in audit trail

**Acceptance Criteria**:
- [ ] create_account requires financial_institution_id parameter
- [ ] create_account validates institution exists and is active
- [ ] update_account allows changing institution (with validation)
- [ ] list_accounts supports filtering by institution
- [ ] Audit logs include institution information
- [ ] Clear error messages guide users to select valid institutions
- [ ] bank_name parameter completely removed from methods

**Implementation Notes**:
- Institution validation happens in service layer (business logic concern)
- Use repository method for validation to keep SQL in repository layer
- Consider caching active institution IDs in Redis for performance
- Audit logs should include both institution ID and name for traceability
- Remove all references to `bank_name` parameter throughout service file

---

#### Component: API Route Updates

**Files Involved**:
- `src/api/routes/accounts.py`

**Purpose**: Update API endpoints to handle mandatory institution field in requests/responses

**Implementation Requirements**:

1. **Update POST /api/v1/accounts endpoint** (around line 74):
   ```python
   @router.post(
       "",
       response_model=AccountResponse,
       status_code=status.HTTP_201_CREATED,
       summary="Create new account",
       description="""
       Create a new financial account for the authenticated user.

       The account name must be unique per user (case-insensitive).
       Financial institution must be selected from active institutions.
       Currency is immutable after creation.

       **Permission:** Authenticated user
       **Audit:** Creates audit log entry with account and institution details
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
                           "account_type": "checking",
                           "currency": "USD",
                           "financial_institution_id": "123e4567-e89b-12d3-a456-426614174000",
                           "financial_institution": {
                               "id": "123e4567-e89b-12d3-a456-426614174000",
                               "name": "JPMorgan Chase Bank, N.A.",
                               "short_name": "Chase",
                               "logo_url": "https://example.com/chase-logo.png",
                               "institution_type": "bank",
                               "country_code": "US"
                           },
                           "opening_balance": "1000.00",
                           "current_balance": "1000.00",
                           "is_active": true,
                           "created_at": "2025-11-29T00:00:00Z",
                           "updated_at": "2025-11-29T00:00:00Z",
                       }
                   }
               },
           },
           400: {"description": "Institution not found or inactive"},
           401: {"description": "Not authenticated"},
           422: {"description": "Validation error (missing institution_id, invalid UUID, etc.)"},
       },
   )
   async def create_account(
       request: Request,
       account_data: AccountCreate,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service),
   ) -> AccountResponse:
       """
       Create new account for authenticated user.

       Request body:
           - account_name: Account name (1-100 chars, unique per user)
           - account_type: Type (checking, savings, credit_card, etc.)
           - currency: ISO 4217 code (USD, EUR, GBP, etc.)
           - financial_institution_id: Institution UUID (REQUIRED, must be active)
           - opening_balance: Initial balance (can be negative)
           - iban: IBAN number (optional, encrypted)
           - color_hex: Hex color for UI (optional, default #818E8F)
           - icon_url: Account icon URL (optional)
           - notes: Personal notes (optional)

       Returns:
           AccountResponse with created account details including institution info

       Requires:
           - Valid access token
           - Active user account
           - Valid financial_institution_id referencing active institution
       """
       account = await account_service.create_account(
           user_id=current_user.id,
           account_name=account_data.account_name,
           account_type=account_data.account_type,
           currency=account_data.currency,
           opening_balance=account_data.opening_balance,
           financial_institution_id=account_data.financial_institution_id,  # NEW
           current_user=current_user,
           bank_name=account_data.bank_name,  # REMOVE this line
           iban=account_data.iban,
           color_hex=account_data.color_hex,
           icon_url=account_data.icon_url,
           notes=account_data.notes,
           request_id=getattr(request.state, "request_id", None),
           ip_address=request.client.host if request.client else None,
           user_agent=request.headers.get("user-agent"),
       )

       return AccountResponse.model_validate(account)
   ```

2. **Update PATCH /api/v1/accounts/{account_id} endpoint** (around line 180):
   ```python
   @router.patch(
       "/{account_id}",
       response_model=AccountResponse,
       summary="Update account",
       description="""
       Update account details.

       Updateable fields:
       - account_name (must be unique per user)
       - is_active (active/inactive status)
       - financial_institution_id (change institution, must be active)
       - color_hex (UI color)
       - icon_url (account icon)
       - notes (personal notes)

       Immutable fields:
       - currency (set at creation)
       - account_type (set at creation)
       - balances (updated via transactions)
       - iban (set at creation)

       **Permission:** Account owner only
       **Audit:** Logs all changes including institution changes
       """,
       responses={
           200: {"description": "Account updated successfully"},
           400: {"description": "New institution not found or inactive"},
           401: {"description": "Not authenticated"},
           404: {"description": "Account not found or no access"},
           422: {"description": "Validation error"},
       },
   )
   async def update_account(
       request: Request,
       account_id: uuid.UUID,
       account_data: AccountUpdate,
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service),
   ) -> AccountResponse:
       """
       Update account details.

       Only the account owner can update. Changes are logged in audit trail.

       Request body (all fields optional):
           - account_name: New account name
           - is_active: New active status
           - financial_institution_id: New institution (must be active)
           - color_hex: New hex color
           - icon_url: New icon URL
           - notes: New notes

       Returns:
           AccountResponse with updated account details
       """
       account = await account_service.update_account(
           account_id=account_id,
           current_user=current_user,
           account_name=account_data.account_name,
           is_active=account_data.is_active,
           financial_institution_id=account_data.financial_institution_id,  # NEW
           color_hex=account_data.color_hex,
           icon_url=account_data.icon_url,
           notes=account_data.notes,
           request_id=getattr(request.state, "request_id", None),
           ip_address=request.client.host if request.client else None,
           user_agent=request.headers.get("user-agent"),
       )

       return AccountResponse.model_validate(account)
   ```

3. **Update GET /api/v1/accounts endpoint** (around line 130):
   ```python
   @router.get(
       "",
       response_model=list[AccountListItem],
       summary="List user's accounts",
       description="""
       Get all accounts owned by or shared with the authenticated user.

       Supports pagination and filtering by:
       - is_active (active/inactive accounts)
       - account_type (checking, savings, etc.)
       - financial_institution_id (filter by institution)

       Results include institution name and logo for UI display.

       **Permission:** User can only list own accounts
       **Returns:** Owned accounts + shared accounts (deduplicated)
       """,
       responses={
           200: {"description": "List of accounts"},
           401: {"description": "Not authenticated"},
           403: {"description": "Cannot list other user's accounts"},
       },
   )
   async def list_accounts(
       current_user: User = Depends(require_active_user),
       account_service: AccountService = Depends(get_account_service),
       skip: int = Query(0, ge=0, description="Number of records to skip"),
       limit: int = Query(20, ge=1, le=100, description="Max records to return"),
       is_active: bool | None = Query(None, description="Filter by active status"),
       account_type: AccountType | None = Query(None, description="Filter by account type"),
       financial_institution_id: uuid.UUID | None = Query(  # NEW parameter
           None, description="Filter by financial institution"
       ),
   ) -> list[AccountListItem]:
       """
       List all accounts for authenticated user.

       Includes both owned accounts and accounts shared with user.
       Results are paginated and can be filtered.

       Query parameters:
           - skip: Number of records to skip (default 0)
           - limit: Max records to return (default 20, max 100)
           - is_active: Filter by active status (true/false/null for all)
           - account_type: Filter by account type (null for all)
           - financial_institution_id: Filter by institution (null for all)

       Returns:
           List of AccountListItem with institution details for UI
       """
       accounts = await account_service.list_user_accounts(
           user_id=current_user.id,
           current_user=current_user,
           skip=skip,
           limit=limit,
           is_active=is_active,
           account_type=account_type,
           financial_institution_id=financial_institution_id,  # NEW
       )

       return [AccountListItem.model_validate(acc) for acc in accounts]
   ```

4. **Edge Cases & Error Handling**:
   - [ ] Handle: Missing financial_institution_id in create → 422 validation error (Pydantic)
   - [ ] Handle: Invalid UUID format for institution_id → 422 validation error (Pydantic)
   - [ ] Handle: Institution doesn't exist → 400 with "Institution not found" message
   - [ ] Handle: Institution is inactive → 400 with "Institution is not active" message
   - [ ] Handle: Filter by non-existent institution_id → Return empty list (no error)
   - [ ] Handle: Response serialization with nested institution → Pydantic handles automatically

5. **Dependencies**:
   - Internal: AccountService with updated method signatures
   - Internal: AccountCreate, AccountUpdate, AccountResponse schemas with institution fields
   - External: FastAPI dependency injection

6. **Testing Requirements**:
   - [ ] Integration test: POST /accounts with valid institution_id succeeds (201)
   - [ ] Integration test: POST /accounts without institution_id fails (422)
   - [ ] Integration test: POST /accounts with invalid institution_id fails (400)
   - [ ] Integration test: POST /accounts with inactive institution fails (400)
   - [ ] Integration test: PATCH /accounts/{id} with new institution_id succeeds (200)
   - [ ] Integration test: PATCH /accounts/{id} with invalid institution fails (400)
   - [ ] Integration test: GET /accounts with institution filter returns correct accounts
   - [ ] Integration test: GET /accounts returns institution details in response
   - [ ] Integration test: Response includes nested institution object
   - [ ] E2E test: Create account → verify institution shown in response

**Acceptance Criteria**:
- [ ] POST /accounts requires financial_institution_id in request body
- [ ] PATCH /accounts accepts optional financial_institution_id for updates
- [ ] GET /accounts supports financial_institution_id query parameter
- [ ] All responses include institution details (name, logo, etc.)
- [ ] OpenAPI documentation shows institution_id as required field
- [ ] Error responses provide clear guidance on institution selection
- [ ] bank_name field removed from all request examples

**Implementation Notes**:
- Update OpenAPI response examples to show nested institution object
- Ensure error messages guide users to select active institutions
- Consider adding endpoint GET /accounts/group-by-institution for analytics
- Document institution_id as required in OpenAPI schema
- Remove all references to bank_name from route documentation

---

### 3.2 Testing Strategy

#### Unit Tests

**Repository Tests** (`tests/unit/repositories/test_account_repository.py`):
```python
# Test institution filtering
async def test_get_by_user_filters_by_institution(account_repository, test_user, test_institution):
    # Create accounts with different institutions
    acc1 = await account_repository.create(user_id=test_user.id, institution_id=test_institution.id, ...)
    acc2 = await account_repository.create(user_id=test_user.id, institution_id=other_institution.id, ...)

    # Filter by institution
    accounts = await account_repository.get_by_user(
        user_id=test_user.id,
        financial_institution_id=test_institution.id
    )

    assert len(accounts) == 1
    assert accounts[0].id == acc1.id

async def test_validate_institution_active_returns_true_for_active(account_repository, active_institution):
    result = await account_repository.validate_institution_active(active_institution.id)
    assert result is True

async def test_validate_institution_active_returns_false_for_inactive(account_repository, inactive_institution):
    result = await account_repository.validate_institution_active(inactive_institution.id)
    assert result is False

async def test_validate_institution_active_returns_false_for_nonexistent(account_repository):
    fake_id = uuid.uuid4()
    result = await account_repository.validate_institution_active(fake_id)
    assert result is False
```

**Service Tests** (`tests/unit/services/test_account_service.py`):
```python
async def test_create_account_validates_institution_exists(account_service, test_user, mocker):
    # Mock repository to return False for validation
    mocker.patch.object(
        account_service.account_repo,
        'validate_institution_active',
        return_value=False
    )

    with pytest.raises(ValidationError, match="not found or is not active"):
        await account_service.create_account(
            user_id=test_user.id,
            financial_institution_id=uuid.uuid4(),
            account_name="Test Account",
            account_type=AccountType.checking,
            currency="USD",
            opening_balance=Decimal("0.00"),
            current_user=test_user,
        )

async def test_create_account_with_valid_institution_succeeds(account_service, test_user, active_institution):
    account = await account_service.create_account(
        user_id=test_user.id,
        financial_institution_id=active_institution.id,
        account_name="Test Account",
        account_type=AccountType.checking,
        currency="USD",
        opening_balance=Decimal("1000.00"),
        current_user=test_user,
    )

    assert account.financial_institution_id == active_institution.id
    assert account.financial_institution.short_name == active_institution.short_name

async def test_update_account_changes_institution(account_service, test_account, test_user, new_institution):
    updated = await account_service.update_account(
        account_id=test_account.id,
        current_user=test_user,
        financial_institution_id=new_institution.id,
    )

    assert updated.financial_institution_id == new_institution.id
```

#### Integration Tests

**Account Routes Tests** (`tests/integration/test_account_routes.py`):
```python
async def test_create_account_with_institution_succeeds(async_client, test_user_token, active_institution):
    """Test creating account with valid institution ID."""
    response = await async_client.post(
        "/api/v1/accounts",
        json={
            "account_name": "Chase Checking",
            "account_type": "checking",
            "currency": "USD",
            "opening_balance": "1000.00",
            "financial_institution_id": str(active_institution.id),
        },
        headers={"Authorization": f"Bearer {test_user_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["financial_institution_id"] == str(active_institution.id)
    assert data["financial_institution"]["short_name"] == active_institution.short_name
    assert "bank_name" not in data  # Field should not exist

async def test_create_account_without_institution_fails(async_client, test_user_token):
    """Test creating account without institution ID fails with 422."""
    response = await async_client.post(
        "/api/v1/accounts",
        json={
            "account_name": "Test Account",
            "account_type": "checking",
            "currency": "USD",
            "opening_balance": "0.00",
            # Missing financial_institution_id
        },
        headers={"Authorization": f"Bearer {test_user_token}"},
    )

    assert response.status_code == 422
    error = response.json()
    assert "financial_institution_id" in str(error).lower()

async def test_create_account_with_inactive_institution_fails(async_client, test_user_token, inactive_institution):
    """Test creating account with inactive institution fails with 400."""
    response = await async_client.post(
        "/api/v1/accounts",
        json={
            "account_name": "Test Account",
            "account_type": "checking",
            "currency": "USD",
            "opening_balance": "0.00",
            "financial_institution_id": str(inactive_institution.id),
        },
        headers={"Authorization": f"Bearer {test_user_token}"},
    )

    assert response.status_code == 400
    error = response.json()
    assert "not active" in error["detail"].lower()

async def test_list_accounts_filters_by_institution(async_client, test_user_token, test_accounts):
    """Test filtering accounts by financial institution."""
    institution_id = test_accounts[0].financial_institution_id

    response = await async_client.get(
        f"/api/v1/accounts?financial_institution_id={institution_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(acc["financial_institution_id"] == str(institution_id) for acc in data)

async def test_update_account_institution_succeeds(async_client, test_user_token, test_account, new_institution):
    """Test updating account to different institution."""
    response = await async_client.patch(
        f"/api/v1/accounts/{test_account.id}",
        json={"financial_institution_id": str(new_institution.id)},
        headers={"Authorization": f"Bearer {test_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["financial_institution_id"] == str(new_institution.id)
```

#### Migration Tests

**Database Migration Tests** (`tests/integration/test_migrations.py`):
```python
async def test_migration_adds_financial_institution_id_column(db_engine):
    """Test migration adds financial_institution_id column."""
    # Run migration
    alembic_upgrade("head")

    # Check column exists
    inspector = inspect(db_engine)
    columns = [col["name"] for col in inspector.get_columns("accounts")]

    assert "financial_institution_id" in columns
    assert "bank_name" not in columns

async def test_migration_creates_foreign_key_constraint(db_engine):
    """Test migration creates FK constraint with ON DELETE RESTRICT."""
    alembic_upgrade("head")

    inspector = inspect(db_engine)
    fks = inspector.get_foreign_keys("accounts")

    fk = next((fk for fk in fks if fk["constrained_columns"] == ["financial_institution_id"]), None)
    assert fk is not None
    assert fk["referred_table"] == "financial_institutions"
    assert fk["referred_columns"] == ["id"]
    assert fk["options"]["ondelete"] == "RESTRICT"

async def test_migration_creates_index(db_engine):
    """Test migration creates index on financial_institution_id."""
    alembic_upgrade("head")

    inspector = inspect(db_engine)
    indexes = inspector.get_indexes("accounts")

    index = next((idx for idx in indexes if "financial_institution_id" in idx["column_names"]), None)
    assert index is not None

async def test_cannot_insert_account_without_institution(async_session):
    """Test NOT NULL constraint prevents inserting account without institution."""
    alembic_upgrade("head")

    # Attempt to insert account without institution
    with pytest.raises(IntegrityError, match="financial_institution_id"):
        account = Account(
            user_id=test_user.id,
            account_name="Test",
            account_type=AccountType.checking,
            currency="USD",
            opening_balance=Decimal("0.00"),
            current_balance=Decimal("0.00"),
            # Missing financial_institution_id
        )
        async_session.add(account)
        await async_session.commit()

async def test_cannot_delete_institution_with_accounts(async_session, test_account, test_institution):
    """Test ON DELETE RESTRICT prevents deleting institution with accounts."""
    alembic_upgrade("head")

    # Attempt to delete institution
    with pytest.raises(IntegrityError, match="RESTRICT"):
        await async_session.delete(test_institution)
        await async_session.commit()
```

#### Test Fixtures

**Add to `tests/conftest.py`**:
```python
@pytest.fixture
async def active_institution(async_session) -> FinancialInstitution:
    """Create active financial institution for testing."""
    institution = FinancialInstitution(
        name="JPMorgan Chase Bank, N.A.",
        short_name="Chase",
        country_code="US",
        institution_type=InstitutionType.bank,
        logo_url="https://example.com/chase-logo.png",
        is_active=True,
    )
    async_session.add(institution)
    await async_session.commit()
    await async_session.refresh(institution)
    return institution

@pytest.fixture
async def inactive_institution(async_session) -> FinancialInstitution:
    """Create inactive financial institution for testing."""
    institution = FinancialInstitution(
        name="Defunct Bank Corp",
        short_name="Defunct Bank",
        country_code="US",
        institution_type=InstitutionType.bank,
        is_active=False,
    )
    async_session.add(institution)
    await async_session.commit()
    await async_session.refresh(institution)
    return institution

@pytest.fixture
async def test_account(async_session, test_user, active_institution) -> Account:
    """Create test account linked to institution."""
    account = Account(
        user_id=test_user.id,
        financial_institution_id=active_institution.id,
        account_name="Test Account",
        account_type=AccountType.checking,
        currency="USD",
        opening_balance=Decimal("1000.00"),
        current_balance=Decimal("1000.00"),
        is_active=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    async_session.add(account)
    await async_session.commit()
    await async_session.refresh(account)
    return account
```

---

## 4. Implementation Roadmap

### Phase 1: Database & Model Changes (Priority: P0, Size: S, Duration: 2 days)

**Goal**: Establish the database foundation with foreign key relationship, ensuring zero accounts can exist without a valid institution reference

**Scope**:
- ✅ Include: Database migration, SQLAlchemy model updates, basic validation
- ❌ Exclude: API changes, service logic updates, comprehensive testing

**Components to Implement**:
- [ ] Database migration: Add `financial_institution_id`, remove `bank_name`
- [ ] Update Account model: Add foreign key column and relationship
- [ ] Update FinancialInstitution model: Add accounts relationship
- [ ] Create migration tests: Verify schema changes

**Detailed Tasks**:

1. [ ] Create Alembic migration
   - Generate migration: `uv run alembic revision --autogenerate -m "link accounts to institutions"`
   - Review autogenerated SQL carefully
   - Modify migration to include all 5 steps (DELETE, ADD COLUMN, ADD FK, ADD INDEX, DROP COLUMN)
   - Add idempotency checks
   - Test upgrade/downgrade locally

2. [ ] Update SQLAlchemy models
   - Modify `src/models/account.py`: Add `financial_institution_id` column
   - Add relationship: `financial_institution: Mapped["FinancialInstitution"]`
   - Remove `bank_name` column completely
   - Update `__repr__` method to use institution.short_name
   - Modify `src/models/financial_institution.py`: Add `accounts` relationship

3. [ ] Run migration on development database
   - Backup database first: `pg_dump emerald_db > backup_$(date +%Y%m%d).sql`
   - Run migration: `uv run alembic upgrade head`
   - Verify changes: `psql -U emerald_user -d emerald_db -c "\d accounts"`
   - Check foreign key: `psql -U emerald_user -d emerald_db -c "\d+ accounts"`

4. [ ] Write migration tests
   - Test column exists and is NOT NULL
   - Test FK constraint exists with ON DELETE RESTRICT
   - Test index created
   - Test bank_name column removed
   - Test migration rollback works

**Dependencies**:
- Requires: financial_institutions table exists and is seeded (from feat-01)
- Blocks: Cannot implement API/service changes until models are updated

**Validation Criteria** (Phase complete when):
- [ ] Migration runs successfully without errors
- [ ] `financial_institution_id` column exists (UUID, NOT NULL, has FK, has index)
- [ ] `bank_name` column does not exist
- [ ] Cannot create account without institution (IntegrityError)
- [ ] Cannot delete institution with linked accounts (IntegrityError)
- [ ] Migration tests pass
- [ ] Rollback migration works correctly

**Risk Factors**:
- Alembic autogenerate may miss foreign key or index → Mitigation: Manually review and add to migration
- Migration may fail if existing accounts exist → Mitigation: DELETE statement at beginning (safe in dev)
- SQLAlchemy relationships may cause circular import → Mitigation: Use string references for forward declarations

**Estimated Effort**: 2 days (1 developer)

---

### Phase 2: Service & Repository Layer (Priority: P0, Size: M, Duration: 3 days)

**Goal**: Implement business logic for mandatory institution validation and enable institution-based filtering

**Scope**:
- ✅ Include: Repository filtering, service validation, institution existence checks
- ❌ Exclude: API endpoint updates (next phase), frontend changes

**Components to Implement**:
- [ ] Repository: Add institution filtering to queries
- [ ] Repository: Add institution validation method
- [ ] Service: Update create_account with institution validation
- [ ] Service: Update update_account to support institution changes
- [ ] Service: Update list_accounts with institution filter

**Detailed Tasks**:

1. [ ] Update AccountRepository (`src/repositories/account_repository.py`)
   - Add `financial_institution_id` parameter to `get_by_user()`
   - Add `financial_institution_id` parameter to `get_shared_with_user()`
   - Add `selectinload(Account.financial_institution)` to all queries
   - Create new method: `validate_institution_active(institution_id) -> bool`
   - Write unit tests for new filtering logic

2. [ ] Update AccountService (`src/services/account_service.py`)
   - Update `create_account()` signature: Add `financial_institution_id` parameter, remove `bank_name`
   - Add institution validation before account creation (call `validate_institution_active`)
   - Raise `ValidationError` if institution not found or inactive
   - Update `update_account()`: Add `financial_institution_id` parameter
   - Add institution validation for updates
   - Update `list_accounts()`: Add `financial_institution_id` filter parameter
   - Update audit logs to include institution ID and name
   - Remove all references to `bank_name` parameter

3. [ ] Write service tests
   - Test create_account with valid institution succeeds
   - Test create_account without institution raises ValidationError
   - Test create_account with inactive institution raises ValidationError
   - Test update_account changes institution successfully
   - Test update_account with inactive institution raises ValidationError
   - Test list_accounts filters by institution correctly
   - Test audit logs include institution information

4. [ ] Update error messages
   - Ensure ValidationError messages guide users to select active institutions
   - Provide helpful error messages: "Institution not found or is not active. Please select a different institution."

**Dependencies**:
- Requires: Phase 1 complete (database migration applied)
- Blocks: Phase 3 (cannot update API routes until service methods are ready)

**Validation Criteria** (Phase complete when):
- [ ] Repository methods support institution filtering
- [ ] Queries eager-load institution relationship (no N+1 queries)
- [ ] Service validates institution exists and is_active before creating account
- [ ] Service prevents creating account with invalid/inactive institution
- [ ] Service allows updating account institution
- [ ] All service/repository tests pass
- [ ] Code coverage ≥ 80% for new code

**Risk Factors**:
- Eager loading may cause performance issues → Mitigation: Use selectinload (async-safe)
- Validation query may be slow → Mitigation: Consider caching active institution IDs in Redis
- Circular dependency between Account and Institution → Mitigation: Already handled via lazy imports

**Estimated Effort**: 3 days (1 developer)

---

### Phase 3: API & Schema Updates (Priority: P0, Size: M, Duration: 2 days)

**Goal**: Expose institution functionality through API endpoints with proper validation and documentation

**Scope**:
- ✅ Include: Pydantic schema updates, API route changes, OpenAPI documentation
- ❌ Exclude: Frontend implementation (separate project)

**Components to Implement**:
- [ ] Pydantic schemas: Add institution fields, remove bank_name
- [ ] API routes: Update request/response handling
- [ ] OpenAPI docs: Update examples and descriptions

**Detailed Tasks**:

1. [ ] Update Pydantic schemas (`src/schemas/account.py`)
   - `AccountBase`: Remove `bank_name` field
   - `AccountCreate`: Add REQUIRED `financial_institution_id` field, add validator
   - `AccountUpdate`: Add optional `financial_institution_id` field
   - `AccountResponse`: Remove `bank_name`, add `financial_institution_id` and nested `financial_institution` object
   - `AccountListItem`: Remove `bank_name`, add institution name and logo for UI
   - `AccountFilterParams`: Add `financial_institution_id` filter
   - Import `FinancialInstitutionResponse` for nested responses

2. [ ] Update API routes (`src/api/routes/accounts.py`)
   - `POST /accounts`: Add `financial_institution_id` to request, update response example
   - `PATCH /accounts/{id}`: Add `financial_institution_id` to updateable fields
   - `GET /accounts`: Add `financial_institution_id` query parameter
   - Update OpenAPI descriptions to mention mandatory institution requirement
   - Update response examples to show nested institution object
   - Remove all references to `bank_name`

3. [ ] Write integration tests (`tests/integration/test_account_routes.py`)
   - Test POST /accounts with valid institution (201 Created)
   - Test POST /accounts without institution (422 Validation Error)
   - Test POST /accounts with inactive institution (400 Bad Request)
   - Test PATCH /accounts/{id} with new institution (200 OK)
   - Test PATCH /accounts/{id} with invalid institution (400 Bad Request)
   - Test GET /accounts with institution filter (200 OK, filtered results)
   - Test responses include nested institution details
   - Test bank_name field not in responses

4. [ ] Update OpenAPI documentation
   - Mark `financial_institution_id` as required in POST schema
   - Add examples showing institution selection
   - Document error responses (400 for invalid institution, 422 for missing)
   - Update descriptions to guide users

**Dependencies**:
- Requires: Phase 2 complete (service layer ready)
- Blocks: None (final phase)

**Validation Criteria** (Phase complete when):
- [ ] All API tests pass (create, update, list, filter)
- [ ] Pydantic validates institution_id is required on create
- [ ] API responses include nested institution details
- [ ] OpenAPI documentation accurate and helpful
- [ ] Error responses provide clear guidance
- [ ] Test coverage ≥ 80% for new code
- [ ] Swagger UI (/docs) shows updated schemas correctly

**Risk Factors**:
- Nested institution in response may cause serialization issues → Mitigation: Use Pydantic's model_validate with from_attributes
- API response size may increase with nested data → Mitigation: Acceptable trade-off, reduces API calls
- OpenAPI examples may not update → Mitigation: Manually verify Swagger UI

**Estimated Effort**: 2 days (1 developer)

---

### Phase 4: Testing & Documentation (Priority: P1, Size: S, Duration: 2 days)

**Goal**: Achieve 80%+ test coverage and comprehensive documentation for future maintainers

**Scope**:
- ✅ Include: Comprehensive test suite, migration documentation, API documentation
- ❌ Exclude: Performance testing (future enhancement), load testing

**Components to Implement**:
- [ ] Complete test coverage (unit, integration, migration)
- [ ] Update project documentation
- [ ] Verify all acceptance criteria met

**Detailed Tasks**:

1. [ ] Complete test suite
   - Ensure unit tests cover all edge cases
   - Ensure integration tests cover all API endpoints
   - Add E2E test: Create account → List accounts → Update institution → Verify change
   - Run coverage report: `uv run pytest tests/ --cov=src --cov-report=term-missing`
   - Fill gaps to reach 80%+ coverage

2. [ ] Update documentation
   - Update `CLAUDE.md`: Document new mandatory institution requirement
   - Update API documentation: Add examples of institution selection
   - Document migration: Add notes about destructive migration (dev-only safe)
   - Update README if needed

3. [ ] Verify acceptance criteria
   - Run full test suite: `uv run pytest tests/`
   - Verify all migration tests pass
   - Verify all API tests pass
   - Check database schema manually
   - Test API via Swagger UI
   - Verify audit logs include institution

4. [ ] Code quality checks
   - Run Ruff formatter: `uv run ruff format .`
   - Run Ruff linter: `uv run ruff check --fix .`
   - Run MyPy: `uv run mypy src/`
   - Fix any type errors or lint issues

**Dependencies**:
- Requires: Phases 1-3 complete
- Blocks: None (final phase)

**Validation Criteria** (Phase complete when):
- [ ] Test coverage ≥ 80% for all changed code
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All migration tests pass
- [ ] Documentation updated and accurate
- [ ] Code quality checks pass (Ruff, MyPy)
- [ ] Manual testing via Swagger UI succeeds
- [ ] All acceptance criteria from feature description met

**Risk Factors**:
- Coverage may not reach 80% → Mitigation: Add missing tests for edge cases
- Documentation may be incomplete → Mitigation: Review all changed files for docstrings

**Estimated Effort**: 2 days (1 developer)

---

### 4.2 Implementation Sequence

```
Phase 1: Database & Models (P0, 2 days)
  ↓ (Migration must be applied first)
Phase 2: Service & Repository (P0, 3 days)
  ↓ (Business logic must exist before API uses it)
Phase 3: API & Schemas (P0, 2 days)
  ↓ (Implementation complete, now validate)
Phase 4: Testing & Docs (P1, 2 days)
```

**Total Duration**: 9 days (1.5 weeks for 1 developer)

**Rationale for ordering**:
- **Phase 1 first**: Database schema is foundation - no code works without it
- **Phase 2 depends on Phase 1**: Service layer needs database columns to exist
- **Phase 3 depends on Phase 2**: API routes call service methods, must exist first
- **Phase 4 last**: Testing and documentation validate all previous work

**Critical Path**: Phases 1 → 2 → 3 are sequential (cannot parallelize)

**Quick Wins**:
- After Phase 1: Database enforces referential integrity (prevents bad data immediately)
- After Phase 2: Service layer prevents creating accounts with invalid institutions
- After Phase 3: Full feature available via API

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution that solves the problem?**
  - Yes. Using a foreign key is the standard database pattern for relationships. Alternatives (embedding JSON, separate mapping table) are more complex.

- [x] **Have we avoided premature optimization?**
  - Yes. Eager loading is necessary (not premature) to prevent N+1 queries. No caching implemented yet (wait for performance data).

- [x] **Does this align with existing patterns in the codebase?**
  - Yes. Follows existing patterns: foreign keys (user_id in accounts), relationships (account.owner), soft deletes, audit logging.

- [x] **Can we deliver value in smaller increments?**
  - Yes. Phased approach allows database changes first, then service layer, then API. Each phase delivers value.

- [x] **Are we solving the actual problem vs. a perceived problem?**
  - Yes. Free-text bank_name causes real data inconsistency ("Chase" vs "chase bank"). Foreign key solves this directly.

### Alternatives Considered

**Alternative 1: Keep bank_name and add institution_id as optional**
- **Description**: Allow both free-text and structured institution data
- **Why not chosen**:
  - Creates data inconsistency (some accounts use free-text, others use FK)
  - Requires complex validation: "if institution_id set, ignore bank_name"
  - Doesn't solve the core problem of standardization
  - Migration to eventual mandatory FK would be harder later

**Alternative 2: Use many-to-many relationship (accounts can have multiple institutions)**
- **Description**: Account could belong to multiple institutions (e.g., Chase and Visa for co-branded card)
- **Why not chosen**:
  - Adds complexity without clear business need
  - Most accounts belong to single institution
  - Can revisit if requirement emerges in future
  - YAGNI principle: Don't build what you don't need

**Alternative 3: Embed institution data in accounts table (JSON column)**
- **Description**: Store institution details as JSONB in accounts table
- **Why not chosen**:
  - No data normalization - institution changes require updating all accounts
  - No referential integrity enforcement
  - Harder to query and filter
  - Violates database normalization principles
  - Not standard relational database design

**Rationale**: The proposed foreign key approach is the standard, proven, simple solution that provides data integrity, supports filtering/analytics, and aligns with existing codebase patterns.

---

## 6. References & Related Documents

### Internal Documentation
- `.claude/standards/backend.md`: Backend development standards (3-layer architecture)
- `.claude/standards/database.md`: Database design standards (foreign keys, migrations)
- `.features/implementations/feat-01-financial-institutions.md`: Financial institutions master data implementation
- `CLAUDE.md`: Project overview and architecture

### External Resources

**SQLAlchemy & Async Patterns**:
- [SQLAlchemy 2.0 Basic Relationship Patterns](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html) - Official documentation for relationship configuration
- [How to access relationships with async SQLAlchemy](https://stackoverflow.com/questions/70104873/how-to-access-relationships-with-async-sqlalchemy) - Async relationship patterns and selectinload usage
- [SQLAlchemy 2.0 Foreign Key Relationships](https://www.codearmo.com/python-tutorial/sql-alchemy-foreign-keys-and-relationships) - Foreign key setup guide

**PostgreSQL Foreign Key Constraints**:
- [PostgreSQL Foreign Key Constraints Documentation](https://www.postgresql.org/docs/current/ddl-constraints.html) - Official PostgreSQL constraint documentation
- [ON DELETE RESTRICT vs CASCADE Best Practices](https://dba.stackexchange.com/questions/254605) - When to use RESTRICT vs CASCADE
- [Cascade Deletes in Supabase/PostgreSQL](https://supabase.com/docs/guides/database/postgres/cascade-deletes) - Practical guide to cascade behavior

**FastAPI & Pydantic**:
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/) - Schema validation patterns
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) - Dependency injection patterns

**Database Design Principles**:
- [Database Normalization Best Practices](https://www.restack.io/p/postgresql-cascading-delete-answer-best-practices) - Normalization and referential integrity
- [PostgreSQL Foreign Key Performance](https://www.dbvis.com/thetable/postgres-on-delete-cascade-a-guide/) - Performance considerations for foreign keys

### Related Design Documents
- Feature 2.2: Convert account_type to master data (similar FK pattern)
- Feature 2.3: Payment methods (will also link to institutions)
- Feature 2.6: Link transactions to payment methods (cascading FK relationships)

---

## Summary

This implementation plan provides a comprehensive blueprint for linking accounts to financial institutions through a mandatory foreign key relationship. The phased approach ensures safe, incremental delivery with validation at each stage:

1. **Phase 1** establishes database foundation with schema changes
2. **Phase 2** implements business logic and validation
3. **Phase 3** exposes functionality through API
4. **Phase 4** validates quality through testing and documentation

The solution follows established patterns, prioritizes data integrity, and enables rich institution-based features while maintaining simplicity and avoiding over-engineering. All changes are reversible, well-tested, and aligned with project standards.

**Key Success Metrics**:
- Zero accounts without valid institution references (enforced by NOT NULL + FK)
- 100% data standardization (no more free-text bank names)
- Improved user experience (logos, standardized names, better filtering)
- Enhanced analytics capabilities (institution-based reporting)
