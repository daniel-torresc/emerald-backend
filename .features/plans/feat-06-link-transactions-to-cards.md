# Implementation Plan: Link Transactions to Cards

## 1. Executive Summary

This feature enables transactions to reference which card was used for payment, allowing users to track spending by credit or debit card. Building on the card management system (Feature 2.3), this feature adds the ability to:

1. **Associate cards with transactions** - Users can select a card when creating or editing transactions
2. **View card details on transactions** - Transaction responses include card information (name, last four digits, network, type)
3. **Filter transactions by card** - Users can filter transaction lists by specific card or card type (credit/debit)

The foundation is already in place: the `card_id` foreign key exists on the transactions table, the card relationship is defined on the Transaction model, and the Pydantic schemas already include `card_id` fields. The implementation focuses on wiring up the service layer, enhancing the repository filtering, and updating the response schema to include card details.

**Expected Outcomes:**
- Users can track which card was used for each transaction
- Transaction responses include full card details when a card is linked
- Transactions can be filtered by card_id or card_type for spending analysis
- All authorization checks enforce card ownership via account relationship

---

## 2. Technical Architecture

### 2.1 System Design Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API Layer (Routes)                           │
│   - Accept card_id in create/update requests (already in schema)    │
│   - Pass card_id to service layer                                   │
│   - Include card details in responses                               │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Service Layer (TransactionService)              │
│   - Validate card exists and not soft-deleted                       │
│   - Validate card ownership (user owns account that owns card)      │
│   - Set card_id on transaction model                                │
│   - Pass card filters to repository                                 │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 Repository Layer (TransactionRepository)            │
│   - Add card_id and card_type filters to search_transactions()     │
│   - Ensure card relationship is loaded on all queries               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
Create Transaction with Card:
  1. User sends POST with card_id
  2. Route passes card_id to TransactionService.create_transaction()
  3. Service validates card via CardRepository.get_by_id_for_user()
  4. Service creates Transaction with card_id set
  5. Repository saves and loads card relationship
  6. Response includes nested card details

Filter Transactions by Card:
  1. User sends GET with card_id or card_type query param
  2. Route passes filters to TransactionService.search_transactions()
  3. Service passes filters to TransactionRepository.search_transactions()
  4. Repository applies card filters to SQL query
  5. Response includes card details for each transaction
```

### 2.3 Technology Decisions

**Approach: Nested Card Object in Response**
- **Purpose**: Provide full card context without requiring additional API calls
- **Why**: Frontend needs card name, last 4 digits, network, and type for display
- **Implementation**: New `CardEmbedded` schema with essential card fields

**Card Ownership Validation Pattern**
- **Purpose**: Ensure users can only link cards they own
- **Why**: Cards have no direct user_id, ownership is through account
- **Implementation**: Use `CardRepository.get_by_id_for_user()` which already handles this

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: Transaction Schema Updates

**Files Involved:**
- `src/schemas/transaction.py`

**Purpose:** Add nested card details to transaction responses and card filters to search params

**Implementation Requirements:**

1. **Create CardEmbedded Schema** (new):
   - Minimal card representation for embedding in transaction responses
   - Fields: `id`, `name`, `card_type`, `last_four_digits`, `card_network`
   - Configure `from_attributes: True` for SQLAlchemy compatibility

2. **Update TransactionResponse**:
   - Add `card: CardEmbedded | None` field
   - Add `@field_validator` to convert Card model to CardEmbedded or None
   - Keep existing `card_id` field for backwards compatibility

3. **Update TransactionListItem**:
   - Add `card: CardEmbedded | None` field for list display
   - Same validator as TransactionResponse

4. **Update TransactionSearchParams**:
   - Add `card_id: uuid.UUID | None` filter field
   - Add `card_type: CardType | None` filter field (import from enums)

**Edge Cases & Error Handling:**
- [ ] Handle `card` being None (no card linked)
- [ ] Handle card relationship not loaded (defensive check)

**Testing Requirements:**
- [ ] Unit test: CardEmbedded schema validates from Card model
- [ ] Unit test: TransactionResponse handles None card
- [ ] Unit test: TransactionSearchParams accepts card_id filter
- [ ] Unit test: TransactionSearchParams accepts card_type filter

**Acceptance Criteria:**
- [ ] TransactionResponse includes `card` object with card details
- [ ] TransactionSearchParams accepts `card_id` and `card_type` filters
- [ ] Existing responses remain backwards compatible (card_id still present)

---

#### Component: Transaction Service Updates

**Files Involved:**
- `src/services/transaction_service.py`

**Purpose:** Add card_id parameter handling with ownership validation to create/update methods

**Implementation Requirements:**

1. **Update `create_transaction()` method**:
   - Add `card_id: uuid.UUID | None = None` parameter
   - Before creating transaction, if card_id provided:
     - Initialize CardRepository
     - Call `card_repo.get_by_id_for_user(card_id, current_user.id)`
     - Raise `NotFoundError("Card")` if not found (handles ownership + soft-delete)
   - Set `card_id` on Transaction model
   - Include `card_id` in audit log `new_values`

2. **Update `update_transaction()` method**:
   - Add `card_id: uuid.UUID | None` parameter (using sentinel for "not provided" vs "set to None")
   - Use `UNSET` pattern to distinguish "not updating card" from "clearing card"
   - If card_id is being set (not UNSET):
     - If new value is None: allow (clearing card association)
     - If new value is UUID: validate card exists and belongs to user
   - Track old/new card_id in audit log

3. **Update `search_transactions()` method**:
   - Add `card_id: uuid.UUID | None = None` parameter
   - Add `card_type: CardType | None = None` parameter
   - Pass these to repository's `search_transactions()`

4. **Add CardRepository dependency**:
   - Import CardRepository
   - Initialize in constructor: `self.card_repo = CardRepository(session)`

**Edge Cases & Error Handling:**
- [ ] Handle card_id=None on create (valid - cash transaction)
- [ ] Handle updating card_id from value to None (clearing card)
- [ ] Handle card_id pointing to soft-deleted card (rejected)
- [ ] Handle card_id pointing to another user's card (rejected via get_by_id_for_user)

**Dependencies:**
- Internal: CardRepository (for ownership validation)
- Internal: TransactionRepository (existing)

**Testing Requirements:**
- [ ] Unit test: Create transaction with valid card_id succeeds
- [ ] Unit test: Create transaction with invalid card_id fails with NotFoundError
- [ ] Unit test: Create transaction with another user's card_id fails
- [ ] Unit test: Create transaction with soft-deleted card fails
- [ ] Unit test: Create transaction without card_id succeeds (null)
- [ ] Unit test: Update transaction card_id to valid card succeeds
- [ ] Unit test: Update transaction card_id to None (clear) succeeds
- [ ] Unit test: Update transaction card_id to invalid card fails
- [ ] Unit test: Search with card_id filter returns matching transactions
- [ ] Unit test: Search with card_type filter returns matching transactions

**Acceptance Criteria:**
- [ ] `create_transaction()` accepts and validates card_id
- [ ] `update_transaction()` accepts card_id updates (including clearing)
- [ ] `search_transactions()` filters by card_id and card_type
- [ ] Invalid/unauthorized card_id raises appropriate errors
- [ ] Audit logs include card_id changes

**Implementation Notes:**
- Use Python's `dataclasses.field(default_factory=...)` or a sentinel value for UNSET pattern
- The CardRepository already has `get_by_id_for_user()` which checks user ownership

---

#### Component: Transaction Repository Updates

**Files Involved:**
- `src/repositories/transaction_repository.py`

**Purpose:** Add card_id and card_type filtering to search_transactions()

**Implementation Requirements:**

1. **Update `search_transactions()` signature**:
   - Add `card_id: uuid.UUID | None = None` parameter
   - Add `card_type: CardType | None = None` parameter

2. **Add card_id filter logic**:
   - If `card_id` is provided: add `Transaction.card_id == card_id` to filters

3. **Add card_type filter logic**:
   - If `card_type` is provided:
     - Join with Card table: `.join(Card, Transaction.card_id == Card.id)`
     - Add filter: `Card.card_type == card_type`
   - Consider: only apply join if card_type filter is used (performance)

4. **Ensure card relationship is loaded**:
   - Verify `selectinload(Transaction.card)` is in query options
   - Add if not present

**Edge Cases & Error Handling:**
- [ ] Handle card_type filter when transaction has no card (should exclude)
- [ ] Handle both card_id and card_type specified (both filters apply)
- [ ] Ensure soft-deleted cards are handled correctly in joins

**Testing Requirements:**
- [ ] Unit test: Filter by card_id returns only matching transactions
- [ ] Unit test: Filter by card_type returns only credit/debit card transactions
- [ ] Unit test: Filter by card_type excludes transactions without cards
- [ ] Unit test: Combined filters (card_id + other filters) work correctly
- [ ] Unit test: Pagination works with card filters

**Acceptance Criteria:**
- [ ] `search_transactions()` filters by card_id when provided
- [ ] `search_transactions()` filters by card_type when provided
- [ ] Card relationship is loaded on returned transactions

---

#### Component: Transaction Routes Updates

**Files Involved:**
- `src/api/routes/transactions.py`

**Purpose:** Pass card_id to service methods (schema already has field)

**Implementation Requirements:**

1. **Update `create_transaction()` route**:
   - Pass `transaction_data.card_id` to service method
   - No other changes needed (schema already has field)

2. **Update `update_transaction()` route**:
   - Pass `transaction_data.card_id` to service method
   - Handle UNSET pattern if service uses it

3. **Update `list_transactions()` route**:
   - Pass `search_params.card_id` to service method
   - Pass `search_params.card_type` to service method

**Edge Cases & Error Handling:**
- [ ] Handle validation errors from service (card not found, unauthorized)
- [ ] These are already handled by exception handlers

**Testing Requirements:**
- [ ] Integration test: Create transaction with card_id via API
- [ ] Integration test: Update transaction card_id via API
- [ ] Integration test: List transactions with card_id filter
- [ ] Integration test: List transactions with card_type filter
- [ ] Integration test: Response includes card details

**Acceptance Criteria:**
- [ ] All transaction endpoints support card_id
- [ ] Card details included in all transaction responses
- [ ] Filtering by card works through API

---

### 3.2 Detailed File Specifications

#### `src/schemas/transaction.py`

**Purpose:** Add CardEmbedded schema and update responses to include card details

**Changes:**

```python
# Add after imports
from src.models.enums import CardType

# Add new schema (before TransactionResponse)
class CardEmbedded(BaseModel):
    """Minimal card representation embedded in transaction responses."""
    id: uuid.UUID
    name: str
    card_type: CardType
    last_four_digits: str | None = None
    card_network: str | None = None

    model_config = {"from_attributes": True}

# Update TransactionResponse - add card field
class TransactionResponse(TransactionBase):
    # ... existing fields ...

    card: CardEmbedded | None = Field(
        default=None,
        description="Card details if card was used for this transaction",
    )

    @field_validator("card", mode="before")
    @classmethod
    def convert_card(cls, card) -> CardEmbedded | None:
        """Convert Card model to CardEmbedded or None."""
        if card is None:
            return None
        if hasattr(card, "id"):  # SQLAlchemy model
            return CardEmbedded.model_validate(card)
        return card

# Update TransactionSearchParams - add filters
class TransactionSearchParams(BaseModel):
    # ... existing fields ...

    card_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by specific card UUID",
    )

    card_type: CardType | None = Field(
        default=None,
        description="Filter by card type (credit_card or debit_card)",
    )
```

**Edge Cases:**
- When card is None: validator returns None
- When card relationship not loaded: hasattr check prevents AttributeError

**Tests:**
- [ ] Test: CardEmbedded validates from Card SQLAlchemy model
- [ ] Test: TransactionResponse.card is None when no card linked
- [ ] Test: TransactionResponse.card has CardEmbedded when card linked

---

#### `src/services/transaction_service.py`

**Purpose:** Add card_id parameter with validation to create/update/search methods

**Changes:**

```python
# Add import
from src.repositories.card_repository import CardRepository
from src.models.enums import CardType

# In __init__, add:
self.card_repo = CardRepository(session)

# Update create_transaction signature and add validation:
async def create_transaction(
    self,
    account_id: uuid.UUID,
    # ... existing params ...
    card_id: uuid.UUID | None = None,  # ADD THIS
    # ... remaining params ...
) -> Transaction:
    # After permission check, add card validation:
    if card_id is not None:
        card = await self.card_repo.get_by_id_for_user(
            card_id=card_id,
            user_id=current_user.id,
        )
        if card is None:
            logger.warning(f"Card {card_id} not found or unauthorized for user {current_user.id}")
            raise NotFoundError("Card")

    # In Transaction() constructor, add:
    transaction = Transaction(
        # ... existing fields ...
        card_id=card_id,  # ADD THIS
    )

    # In audit log new_values, add:
    new_values={
        # ... existing fields ...
        "card_id": str(card_id) if card_id else None,
    }

# Update update_transaction - similar pattern with UNSET handling

# Update search_transactions signature:
async def search_transactions(
    self,
    account_id: uuid.UUID,
    current_user: User,
    # ... existing params ...
    card_id: uuid.UUID | None = None,  # ADD
    card_type: CardType | None = None,  # ADD
    # ... remaining params ...
) -> tuple[list[Transaction], int]:
    # Pass to repository:
    return await self.transaction_repo.search_transactions(
        # ... existing params ...
        card_id=card_id,
        card_type=card_type,
    )
```

**Edge Cases:**
- card_id=None on create: valid, creates transaction without card
- card_id pointing to deleted card: get_by_id_for_user returns None (rejected)
- card_id pointing to another user's card: get_by_id_for_user returns None (rejected)

**Tests:**
- [ ] Test: Valid card_id sets card relationship
- [ ] Test: Invalid card_id raises NotFoundError
- [ ] Test: None card_id creates transaction without card

---

#### `src/repositories/transaction_repository.py`

**Purpose:** Add card filtering to search_transactions()

**Changes:**

```python
# Add import
from src.models.card import Card
from src.models.enums import CardType

# Update search_transactions signature:
async def search_transactions(
    self,
    account_id: uuid.UUID,
    # ... existing params ...
    card_id: uuid.UUID | None = None,  # ADD
    card_type: CardType | None = None,  # ADD
    # ... remaining params ...
) -> tuple[list[Transaction], int]:
    # Add to filters section:

    # Card ID filter
    if card_id is not None:
        filters.append(Transaction.card_id == card_id)

    # Card type filter (requires join)
    if card_type is not None:
        query = query.join(Card, Transaction.card_id == Card.id).where(
            Card.card_type == card_type
        )

    # Ensure card relationship is in selectinload options
    # (verify it's already there or add it)
```

**Edge Cases:**
- card_type filter on transaction without card: inner join excludes it (correct behavior)
- card_type + card_id together: both apply (AND logic)

**Tests:**
- [ ] Test: card_id filter returns exact match
- [ ] Test: card_type filter returns all matching type
- [ ] Test: card_type excludes cash transactions

---

#### `src/api/routes/transactions.py`

**Purpose:** Wire card_id through to service layer

**Changes:**

```python
# In create_transaction route:
transaction = await transaction_service.create_transaction(
    # ... existing params ...
    card_id=transaction_data.card_id,  # ADD THIS
    # ... remaining params ...
)

# In update_transaction route:
transaction = await transaction_service.update_transaction(
    # ... existing params ...
    card_id=transaction_data.card_id,  # ADD THIS
    # ... remaining params ...
)

# In list_transactions route:
transactions, total = await transaction_service.search_transactions(
    # ... existing params ...
    card_id=search_params.card_id,  # ADD THIS
    card_type=search_params.card_type,  # ADD THIS
    # ... remaining params ...
)
```

**Edge Cases:**
- Handled by service layer validation

**Tests:**
- [ ] Integration test: Full flow create with card
- [ ] Integration test: Full flow update card
- [ ] Integration test: Full flow filter by card

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Core Implementation (Size: M, Priority: P0)

**Goal:** Enable creating/updating transactions with card_id and include card details in responses

**Scope:**
- Add CardEmbedded schema and update TransactionResponse/TransactionListItem
- Add card_id parameter to TransactionService.create_transaction()
- Add card_id parameter to TransactionService.update_transaction()
- Update routes to pass card_id
- Write unit tests for service layer card validation
- Write integration tests for create/update with card

**Components to Implement:**
- [ ] CardEmbedded schema in `src/schemas/transaction.py`
- [ ] Update TransactionResponse with card field
- [ ] Update TransactionService.create_transaction() with card_id
- [ ] Update TransactionService.update_transaction() with card_id
- [ ] Update transaction routes to pass card_id

**Detailed Tasks:**

1. [ ] Update `src/schemas/transaction.py`:
   - Add CardEmbedded schema class
   - Add `card: CardEmbedded | None` to TransactionResponse
   - Add field_validator to convert Card model
   - Add same changes to TransactionListItem

2. [ ] Update `src/services/transaction_service.py`:
   - Import CardRepository
   - Initialize CardRepository in __init__
   - Add card_id parameter to create_transaction()
   - Add card validation logic (get_by_id_for_user)
   - Set card_id on Transaction model
   - Add card_id to audit log
   - Add card_id parameter to update_transaction()
   - Add card validation for updates

3. [ ] Update `src/api/routes/transactions.py`:
   - Pass transaction_data.card_id to create_transaction()
   - Pass transaction_data.card_id to update_transaction()

4. [ ] Write tests:
   - Unit tests for TransactionService card validation
   - Integration tests for API create/update with card

**Dependencies:**
- Requires: Feature 2.3 (Cards Management) - COMPLETED
- Blocks: Phase 2 (filtering)

**Validation Criteria:**
- [ ] Create transaction with valid card_id includes card in response
- [ ] Create transaction with invalid card_id returns 404
- [ ] Create transaction without card_id works (cash transaction)
- [ ] Update transaction card_id works
- [ ] Response includes full card details (name, last_four, network, type)
- [ ] Tests pass with 80%+ coverage

**Risk Factors:**
- Card relationship loading: Ensure selectinload is applied correctly
- Mitigation: Verify card relationship loading in existing queries

---

#### Phase 2: Filtering (Size: S, Priority: P0)

**Goal:** Enable filtering transactions by card_id and card_type

**Scope:**
- Add card_id and card_type to TransactionSearchParams
- Add card filters to TransactionRepository.search_transactions()
- Add card filter parameters to TransactionService.search_transactions()
- Update list_transactions route
- Write tests for filtering

**Components to Implement:**
- [ ] Update TransactionSearchParams with card_id, card_type
- [ ] Update TransactionRepository.search_transactions() with filters
- [ ] Update TransactionService.search_transactions() with filters
- [ ] Update list_transactions route

**Detailed Tasks:**

1. [ ] Update `src/schemas/transaction.py`:
   - Add card_id field to TransactionSearchParams
   - Add card_type field to TransactionSearchParams
   - Import CardType enum

2. [ ] Update `src/repositories/transaction_repository.py`:
   - Import Card model and CardType enum
   - Add card_id parameter to search_transactions()
   - Add card_type parameter to search_transactions()
   - Add card_id filter logic
   - Add card_type filter with join

3. [ ] Update `src/services/transaction_service.py`:
   - Add card_id parameter to search_transactions()
   - Add card_type parameter to search_transactions()
   - Pass to repository

4. [ ] Update `src/api/routes/transactions.py`:
   - Pass search_params.card_id to service
   - Pass search_params.card_type to service

5. [ ] Write tests:
   - Integration test: Filter by card_id
   - Integration test: Filter by card_type
   - Integration test: Combined filters with pagination

**Dependencies:**
- Requires: Phase 1 (core implementation)

**Validation Criteria:**
- [ ] Filter by card_id returns only matching transactions
- [ ] Filter by card_type returns only credit/debit card transactions
- [ ] Filter by card_type excludes transactions without cards
- [ ] Pagination works correctly with card filters
- [ ] Tests pass with 80%+ coverage

---

### 4.2 Implementation Sequence

```
Phase 1: Core (P0)
  - Schema updates (CardEmbedded, TransactionResponse)
  - Service updates (create/update with card_id)
  - Route updates (pass card_id)
  - Tests
     ↓
Phase 2: Filtering (P0)
  - Schema updates (TransactionSearchParams)
  - Repository updates (search filters)
  - Service/Route updates
  - Tests
```

**Rationale for ordering:**
- Phase 1 first: Establishes the core card-transaction link and response schema
- Phase 2 after: Filtering depends on the card relationship being functional

**Quick Wins:**
- CardEmbedded schema and TransactionResponse update can be done first for immediate response improvement

---

## 5. Simplicity & Design Validation

**Simplicity Checklist:**
- [x] Is this the SIMPLEST solution that solves the problem? Yes - leveraging existing card_id column and relationship
- [x] Have we avoided premature optimization? Yes - simple join for card_type filter
- [x] Does this align with existing patterns in the codebase? Yes - follows service validation pattern from CardService
- [x] Can we deliver value in smaller increments? Yes - Phase 1 delivers core linking, Phase 2 adds filtering
- [x] Are we solving the actual problem vs. a perceived problem? Yes - users need to track spending by card

**Alternatives Considered:**

1. **Alternative: Store card details directly on transaction (denormalized)**
   - Why not: Would duplicate data, make card updates complex, deviate from normalized design

2. **Alternative: Separate card-transaction linking table**
   - Why not: Overly complex, 1:N relationship already handled by FK on transaction

3. **Alternative: Return card_id only, require separate API call for card details**
   - Why not: Poor UX, extra network round trips for common use case

**Rationale:** The proposed approach uses the existing FK relationship, follows established patterns in the codebase, and provides card details inline for optimal frontend experience.

---

## 6. Testing Strategy

### 6.1 Unit Tests

**TransactionService Tests:**
```python
class TestTransactionServiceCardValidation:
    async def test_create_transaction_with_valid_card(self):
        # Create transaction with card_id
        # Assert card relationship is set
        # Assert response includes card

    async def test_create_transaction_with_invalid_card_raises_not_found(self):
        # Card doesn't exist
        # Assert NotFoundError raised

    async def test_create_transaction_with_other_users_card_raises_not_found(self):
        # Card belongs to different user
        # Assert NotFoundError raised

    async def test_create_transaction_with_soft_deleted_card_raises_not_found(self):
        # Card is soft-deleted
        # Assert NotFoundError raised

    async def test_create_transaction_without_card_succeeds(self):
        # card_id is None
        # Assert transaction created, card is None

    async def test_update_transaction_card_id(self):
        # Update card_id to new card
        # Assert card updated

    async def test_update_transaction_clear_card(self):
        # Update card_id to None
        # Assert card cleared
```

### 6.2 Integration Tests

**Transaction API Tests:**
```python
class TestTransactionCardIntegration:
    async def test_create_transaction_with_card(self):
        # POST with card_id
        # Assert 201, response has card details

    async def test_create_transaction_card_not_found(self):
        # POST with non-existent card_id
        # Assert 404

    async def test_update_transaction_card(self):
        # PUT with card_id
        # Assert 200, card updated

    async def test_update_transaction_clear_card(self):
        # PUT with card_id=null
        # Assert 200, card cleared

    async def test_list_transactions_filter_by_card_id(self):
        # GET with card_id query param
        # Assert only matching transactions returned

    async def test_list_transactions_filter_by_card_type(self):
        # GET with card_type query param
        # Assert only credit/debit card transactions

    async def test_list_transactions_with_card_details(self):
        # GET transactions
        # Assert each transaction has card details embedded
```

### 6.3 Edge Case Tests

```python
class TestTransactionCardEdgeCases:
    async def test_soft_deleted_card_sets_card_id_null(self):
        # When card is soft-deleted, existing transactions should have card_id=NULL
        # (Handled by FK SET NULL - verify behavior)

    async def test_filter_card_type_excludes_cash_transactions(self):
        # Transactions without cards should not appear in card_type filter results

    async def test_pagination_with_card_filters(self):
        # Ensure pagination works correctly with card filters
```

---

## 7. References & Related Documents

- **Feature 2.3 (Cards Management):** `.features/descriptions/feat-03-cards-management.md` - Establishes card model and API
- **Transaction Model:** `src/models/transaction.py:209-269` - card_id FK and card relationship
- **Card Repository:** `src/repositories/card_repository.py:105-145` - `get_by_id_for_user()` pattern
- **Card Service:** `src/services/card_service.py:84-90` - Ownership validation pattern
- **Transaction Service:** `src/services/transaction_service.py` - Existing create/update patterns
- **Backend Standards:** `.claude/standards/backend.md` - Code style and architecture guidelines
- **API Standards:** `.claude/standards/api.md` - Response format guidelines
