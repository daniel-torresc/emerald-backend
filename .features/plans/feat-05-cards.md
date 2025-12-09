# Implementation Plan: Cards Management

**Feature ID**: feat-05-cards
**Phase**: 2 - Integration
**Priority**: High
**Estimated Effort**: 4-5 developer days
**Dependencies**: Feature 1.1 (Financial Institutions Master Data), Accounts feature

---

## 1. Executive Summary

### Overview

This feature introduces a `cards` entity that allows users to manage their credit and debit cards within the system. Each card MUST be associated with an account (the account it's linked to or draws from). Cards can store relevant details such as last 4 digits, card network, expiration date, and credit limits (for credit cards). This feature also establishes the relationship between transactions and cards, allowing users to track which card was used for each transaction.

Cards are **user-owned transactional data**, meaning each card belongs to a specific user through their account association. This follows the same pattern as other user-owned entities in the codebase.

### Primary Objectives

1. **Card Management**: Enable users to create and manage their credit and debit cards
2. **Account Association**: Every card MUST be linked to an account (required relationship)
3. **Card Identification**: Safely store card details (last 4 digits only - never full numbers)
4. **Credit Limit Tracking**: Allow users to monitor credit limits for spending analysis
5. **Transaction Integration**: Link transactions to the card used for payment

### Expected Outcomes

- **Users** can create, view, update, and delete their cards through the API
- **Cards** store network, expiration date, last 4 digits, and credit limits
- **Every card** is linked to exactly one account (required)
- **Transactions** can optionally reference the card used
- **Soft Delete** preserves historical data while allowing users to "remove" cards
- **Audit Trail** maintains complete history of all card changes

### Success Criteria

- `cards` table created with all required columns, constraints, and indexes
- `CardType` enum defined with two values: `credit_card`, `debit_card`
- Complete CRUD API for cards
- `card_id` foreign key added to `transactions` table
- Users can only access cards linked to their own accounts
- All validation rules enforced (last 4 digits format, expiry date coupling, positive credit limit)
- Account association is REQUIRED (not optional)
- 80%+ test coverage with comprehensive integration tests
- All state changes audited

---

## 2. Technical Architecture

### 2.1 System Design Overview

This feature introduces a **user-owned card entity** that has a REQUIRED relationship to accounts. The card ownership is derived from account ownership - if you own the account, you own the cards linked to it.

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (src/api/routes/cards.py)                        │
│  - List user's cards (authenticated users)                  │
│  - Get card by ID (authenticated users)                     │
│  - Create card (authenticated users)                        │
│  - Update card (authenticated users)                        │
│  - Delete card (authenticated users)                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer (src/services/card_service.py)               │
│  - Business logic for card management                       │
│  - Account ownership validation (REQUIRED)                  │
│  - Financial institution existence check (optional)         │
│  - Validation rules (expiry coupling, credit limit, etc.)   │
│  - Audit logging for all state changes                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Repository Layer (src/repositories/card_repository.py)     │
│  - Database operations (CRUD)                               │
│  - Filtering by user (via account ownership)                │
│  - Pagination and sorting                                   │
│  - Eager loading of relationships                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Database (PostgreSQL)                                      │
│  - cards table (user-owned via account)                     │
│  - card_type enum (credit_card, debit_card)                 │
│  - FK to accounts (REQUIRED), financial_institutions        │
│  - transactions.card_id FK (optional)                       │
└─────────────────────────────────────────────────────────────┘
```

**Key Characteristics**:
- **Account-owned**: Every card MUST belong to exactly one account
- **User access via account**: User owns cards through account ownership
- **Soft delete**: Uses `deleted_at` timestamp for data retention
- **Type enumeration**: PostgreSQL enum for card types (credit/debit)
- **Transaction linkage**: Transactions can reference the card used

### 2.2 Data Model

```
┌──────────────┐       ┌──────────────┐       ┌──────────────────────┐
│    users     │       │   accounts   │       │        cards         │
├──────────────┤       ├──────────────┤       ├──────────────────────┤
│ id (PK)      │◄──────│ user_id (FK) │       │ id (PK)              │
│ ...          │       │ id (PK)      │◄──────│ account_id (FK) [REQ]│
└──────────────┘       │ ...          │       │ card_type            │
                       └──────────────┘       │ name                 │
                              ▲               │ last_four_digits     │
                              │               │ card_network         │
                              │               │ expiry_month         │
┌──────────────────────┐      │               │ expiry_year          │
│ financial_institutions│      │               │ credit_limit         │
├──────────────────────┤      │               │ financial_inst_id(FK)│
│ id (PK)              │◄─────┼───────────────│ deleted_at           │
│ ...                  │      │               │ ...                  │
└──────────────────────┘      │               └──────────────────────┘
                              │                         ▲
                              │                         │ (optional)
                       ┌──────┴───────┐                 │
                       │ transactions │─────────────────┘
                       ├──────────────┤
                       │ id (PK)      │
                       │ account_id   │
                       │ card_id (FK) │  ← NEW: optional reference to card
                       │ ...          │
                       └──────────────┘
```

### 2.3 Technology Decisions

#### **CardType as PostgreSQL Enum**

**Purpose**: Type-safe classification of cards
**Why this choice**:
- Only 2 fixed values: `credit_card`, `debit_card`
- Follows existing pattern (`TransactionType`, `InstitutionType` enums)
- Database-level type safety
- Better query performance than string comparison

**Values**: `credit_card`, `debit_card`

#### **Required Account Association**

**Purpose**: Cards MUST belong to an account
**Why this choice**:
- Credit cards are linked to credit accounts
- Debit cards draw from checking/savings accounts
- Ownership derived from account ownership (simpler authorization)
- Makes business sense - cards don't exist independently

**Implementation**: `account_id` is NOT NULL with RESTRICT on delete

#### **Soft Delete Pattern (SoftDeleteMixin)**

**Purpose**: Preserve historical data for compliance and transaction references
**Why this choice**:
- Cards are referenced by transactions
- Historical transactions need to maintain reference to original card
- GDPR/SOX compliance requires data retention
- Matches existing patterns for user-owned data

#### **Transaction Card Reference**

**Purpose**: Track which card was used for a transaction
**Why this choice**:
- Optional FK - not all transactions use cards
- SET NULL on card delete - preserve transaction, clear card reference
- Enables spending analysis by card

### 2.4 File Structure

```
src/
├── models/
│   ├── enums.py                    # MODIFIED: Add CardType enum
│   ├── card.py                     # NEW: SQLAlchemy model
│   └── transaction.py              # MODIFIED: Add card_id FK
│
├── schemas/
│   ├── card.py                     # NEW: Pydantic schemas
│   └── transaction.py              # MODIFIED: Add card_id field
│
├── repositories/
│   └── card_repository.py          # NEW: Database operations
│
├── services/
│   └── card_service.py             # NEW: Business logic
│
├── api/
│   ├── routes/
│   │   └── cards.py                # NEW: API endpoints
│   └── dependencies.py             # MODIFIED: Add service factory
│
└── main.py                         # MODIFIED: Register new router

alembic/
└── versions/
    └── XXXX_add_cards_table.py     # NEW: Cards table + transaction FK

tests/
├── integration/
│   └── test_card_routes.py         # NEW: API integration tests
└── unit/
    └── test_card_service.py        # NEW: Business logic tests
```

---

## 3. Implementation Specification

### 3.1 Component Breakdown

#### Component: CardType Enum

**Files Involved**:
- `src/models/enums.py`

**Purpose**: Define the card type classification as a PostgreSQL enum.

**Implementation**:
```python
class CardType(str, enum.Enum):
    """Card type classification."""
    credit_card = "credit_card"
    debit_card = "debit_card"

    @classmethod
    def to_dict_list(cls) -> list[dict[str, str]]:
        """Return list of dicts with 'key' and 'label' for API responses."""
        return [
            {"key": item.value, "label": item.value.replace("_", " ").title()}
            for item in cls
        ]
```

**Testing Requirements**:
- [ ] Unit test: Both values defined
- [ ] Unit test: to_dict_list() returns correct format

---

#### Component: Card Model

**Files Involved**:
- `src/models/card.py`
- `src/models/__init__.py` (add export)

**Purpose**: Define the database table structure for cards.

**Column Definitions**:
```python
class Card(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """User card (credit or debit) linked to an account."""
    __tablename__ = "cards"

    # Primary Key (from Base)
    id: Mapped[uuid.UUID]  # UUID primary key

    # REQUIRED Foreign Key - every card must belong to an account
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Optional Foreign Key - issuing institution
    financial_institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Card Type (REQUIRED)
    card_type: Mapped[CardType] = mapped_column(
        SQLEnum(CardType, name="card_type", create_constraint=True),
        nullable=False,
        index=True,
    )

    # Display name (REQUIRED)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Card identification (all optional)
    last_four_digits: Mapped[str | None] = mapped_column(String(4), nullable=True)
    card_network: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expiry_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expiry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Credit limit (typically for credit cards only)
    credit_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[account_id],
        lazy="selectin",
    )

    financial_institution: Mapped["FinancialInstitution | None"] = relationship(
        "FinancialInstitution",
        foreign_keys=[financial_institution_id],
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(expiry_month IS NULL) OR (expiry_month >= 1 AND expiry_month <= 12)",
            name="ck_cards_expiry_month_range"
        ),
        CheckConstraint(
            "(last_four_digits IS NULL) OR (last_four_digits ~ '^[0-9]{4}$')",
            name="ck_cards_last_four_digits_format"
        ),
        CheckConstraint(
            "(credit_limit IS NULL) OR (credit_limit > 0)",
            name="ck_cards_credit_limit_positive"
        ),
    )

    def __repr__(self) -> str:
        return f"Card(id={self.id}, name={self.name}, type={self.card_type.value})"
```

**Key Points**:
- `account_id` is NOT NULL with RESTRICT - cannot delete account with cards
- `financial_institution_id` is nullable with SET NULL
- User ownership derived from account ownership
- No direct `user_id` column needed

---

#### Component: Transaction Model Update

**Files Involved**:
- `src/models/transaction.py`

**Purpose**: Add optional card reference to transactions.

**Changes**:
```python
# Add to Transaction model

# Optional Foreign Key - card used for this transaction
card_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("cards.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)

# Add relationship
card: Mapped["Card | None"] = relationship(
    "Card",
    foreign_keys=[card_id],
    lazy="selectin",
)
```

---

#### Component: Card Repository

**Files Involved**:
- `src/repositories/card_repository.py`

**Purpose**: Database operations for cards with user-scoped access via account ownership.

**Method Implementations**:
```python
class CardRepository(BaseRepository[Card]):
    def __init__(self, session: AsyncSession):
        super().__init__(Card, session)

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        card_type: CardType | None = None,
        account_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Card]:
        """Get all cards for a user (via account ownership)."""
        query = (
            select(Card)
            .join(Account, Card.account_id == Account.id)
            .where(Account.user_id == user_id)
            .options(
                selectinload(Card.account),
                selectinload(Card.financial_institution),
            )
        )

        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        if card_type is not None:
            query = query.where(Card.card_type == card_type)

        if account_id is not None:
            query = query.where(Card.account_id == account_id)

        query = query.offset(skip).limit(limit).order_by(Card.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id_for_user(
        self,
        card_id: uuid.UUID,
        user_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Card | None:
        """Get a card if user owns the associated account."""
        query = (
            select(Card)
            .join(Account, Card.account_id == Account.id)
            .where(Card.id == card_id, Account.user_id == user_id)
            .options(
                selectinload(Card.account),
                selectinload(Card.financial_institution),
            )
        )

        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_account(
        self,
        account_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> list[Card]:
        """Get all cards for a specific account."""
        query = (
            select(Card)
            .where(Card.account_id == account_id)
            .options(
                selectinload(Card.financial_institution),
            )
        )

        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        query = query.order_by(Card.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())
```

---

#### Component: Card Schemas

**Files Involved**:
- `src/schemas/card.py`

**Schema Definitions**:
```python
class CardBase(BaseModel):
    """Base schema with common fields."""
    name: str = Field(min_length=1, max_length=100)
    card_type: CardType
    last_four_digits: str | None = Field(default=None, pattern=r"^[0-9]{4}$")
    card_network: str | None = Field(default=None, max_length=50)
    expiry_month: int | None = Field(default=None, ge=1, le=12)
    expiry_year: int | None = Field(default=None)
    credit_limit: Decimal | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=500)


class CardCreate(CardBase):
    """Schema for POST /api/v1/cards."""
    account_id: uuid.UUID  # REQUIRED
    financial_institution_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_expiry_coupling(self) -> "CardCreate":
        """Ensure expiry_month and expiry_year are both provided or both null."""
        if (self.expiry_month is None) != (self.expiry_year is None):
            raise ValueError(
                "Both expiry_month and expiry_year must be provided together, or both omitted"
            )
        return self

    @field_validator("expiry_year")
    @classmethod
    def validate_expiry_year(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 2000 or value > 2100:
            raise ValueError("Expiry year must be between 2000 and 2100")
        return value


class CardUpdate(BaseModel):
    """Schema for PATCH /api/v1/cards/{id}."""
    # card_type and account_id NOT included (immutable)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    last_four_digits: str | None = Field(default=None, pattern=r"^[0-9]{4}$")
    card_network: str | None = Field(default=None, max_length=50)
    expiry_month: int | None = Field(default=None, ge=1, le=12)
    expiry_year: int | None = Field(default=None)
    credit_limit: Decimal | None = Field(default=None, gt=0)
    financial_institution_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=500)


class CardResponse(BaseModel):
    """Schema for GET responses."""
    id: uuid.UUID
    name: str
    card_type: CardType
    last_four_digits: str | None
    card_network: str | None
    expiry_month: int | None
    expiry_year: int | None
    credit_limit: Decimal | None
    notes: str | None
    account: AccountListItem  # Always present (required relationship)
    financial_institution: FinancialInstitutionListItem | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CardListItem(BaseModel):
    """Schema for list endpoints."""
    id: uuid.UUID
    name: str
    card_type: CardType
    last_four_digits: str | None
    card_network: str | None
    account: AccountListItem
    financial_institution: FinancialInstitutionListItem | None

    model_config = ConfigDict(from_attributes=True)
```

---

#### Component: Transaction Schema Update

**Files Involved**:
- `src/schemas/transaction.py`

**Changes**:
```python
# Add to TransactionCreate
card_id: uuid.UUID | None = None

# Add to TransactionUpdate
card_id: uuid.UUID | None = None

# Add to TransactionResponse
card: CardListItem | None = None
```

---

#### Component: Card Service

**Files Involved**:
- `src/services/card_service.py`

**Implementation**:
```python
class CardService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.card_repo = CardRepository(session)
        self.account_repo = AccountRepository(session)
        self.financial_institution_repo = FinancialInstitutionRepository(session)
        self.audit_service = AuditService(session)

    async def create_card(
        self,
        data: CardCreate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CardResponse:
        """Create a new card linked to user's account."""

        # 1. Validate account ownership (REQUIRED)
        account = await self.account_repo.get_by_id(data.account_id)
        if not account:
            raise NotFoundError("Account")
        if account.user_id != current_user.id:
            raise AuthorizationError("Account does not belong to you")

        # 2. Validate financial institution (if provided)
        if data.financial_institution_id:
            institution = await self.financial_institution_repo.get_by_id(
                data.financial_institution_id
            )
            if not institution:
                raise NotFoundError("Financial institution")
            if not institution.is_active:
                raise ValidationError("Financial institution is inactive")

        # 3. Create card
        card = await self.card_repo.create(
            account_id=data.account_id,
            financial_institution_id=data.financial_institution_id,
            card_type=data.card_type,
            name=data.name,
            last_four_digits=data.last_four_digits,
            card_network=data.card_network,
            expiry_month=data.expiry_month,
            expiry_year=data.expiry_year,
            credit_limit=data.credit_limit,
            notes=data.notes,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        # 4. Audit log
        await self.audit_service.log_action(
            db=self.session,
            user_id=current_user.id,
            action=AuditAction.CREATE,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return CardResponse.model_validate(card)

    async def get_card(
        self,
        card_id: uuid.UUID,
        current_user: User,
    ) -> CardResponse:
        """Get a card by ID (must own the account)."""
        card = await self.card_repo.get_by_id_for_user(card_id, current_user.id)
        if not card:
            raise NotFoundError("Card")
        return CardResponse.model_validate(card)

    async def list_cards(
        self,
        current_user: User,
        card_type: CardType | None = None,
        account_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CardListItem]:
        """List all cards for the current user."""
        # If filtering by account, verify ownership
        if account_id:
            account = await self.account_repo.get_by_id(account_id)
            if not account or account.user_id != current_user.id:
                raise AuthorizationError("Account does not belong to you")

        cards = await self.card_repo.get_by_user(
            user_id=current_user.id,
            card_type=card_type,
            account_id=account_id,
            include_deleted=include_deleted,
            skip=skip,
            limit=limit,
        )
        return [CardListItem.model_validate(card) for card in cards]

    async def update_card(
        self,
        card_id: uuid.UUID,
        data: CardUpdate,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CardResponse:
        """Update an existing card."""
        card = await self.card_repo.get_by_id_for_user(card_id, current_user.id)
        if not card:
            raise NotFoundError("Card")

        # Validate new financial institution if provided
        if data.financial_institution_id:
            institution = await self.financial_institution_repo.get_by_id(
                data.financial_institution_id
            )
            if not institution:
                raise NotFoundError("Financial institution")
            if not institution.is_active:
                raise ValidationError("Financial institution is inactive")

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = current_user.id

        card = await self.card_repo.update(card, **update_data)

        await self.audit_service.log_action(
            db=self.session,
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return CardResponse.model_validate(card)

    async def delete_card(
        self,
        card_id: uuid.UUID,
        current_user: User,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Soft-delete a card."""
        card = await self.card_repo.get_by_id_for_user(card_id, current_user.id)
        if not card:
            raise NotFoundError("Card")

        await self.card_repo.soft_delete(card)

        await self.audit_service.log_action(
            db=self.session,
            user_id=current_user.id,
            action=AuditAction.DELETE,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )
```

---

#### Component: Card API Routes

**Files Involved**:
- `src/api/routes/cards.py`

**Endpoints**:
```python
router = APIRouter(prefix="/cards", tags=["Cards"])

# GET /api/v1/cards - List user's cards
@router.get("", response_model=list[CardListItem])
async def list_cards(
    card_type: CardType | None = Query(default=None),
    account_id: uuid.UUID | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(require_active_user),
    service: CardService = Depends(get_card_service),
) -> list[CardListItem]:
    """List all cards for the authenticated user."""

# GET /api/v1/cards/{card_id} - Get card by ID
@router.get("/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    service: CardService = Depends(get_card_service),
) -> CardResponse:
    """Get a specific card."""

# POST /api/v1/cards - Create card
@router.post("", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    request: Request,
    data: CardCreate,
    current_user: User = Depends(require_active_user),
    service: CardService = Depends(get_card_service),
) -> CardResponse:
    """Create a new card linked to an account."""

# PATCH /api/v1/cards/{card_id} - Update card
@router.patch("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: uuid.UUID,
    data: CardUpdate,
    request: Request,
    current_user: User = Depends(require_active_user),
    service: CardService = Depends(get_card_service),
) -> CardResponse:
    """Update an existing card."""

# DELETE /api/v1/cards/{card_id} - Soft delete card
@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_active_user),
    service: CardService = Depends(get_card_service),
) -> None:
    """Soft-delete a card."""
```

---

#### Component: Database Migration

**Files Involved**:
- `alembic/versions/XXXX_add_cards_table.py`

**Migration Steps**:

1. **Create card_type enum**:
```sql
CREATE TYPE card_type AS ENUM ('credit_card', 'debit_card');
```

2. **Create cards table**:
```sql
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    financial_institution_id UUID REFERENCES financial_institutions(id) ON DELETE SET NULL,
    card_type card_type NOT NULL,
    name VARCHAR(100) NOT NULL,
    last_four_digits VARCHAR(4),
    card_network VARCHAR(50),
    expiry_month INTEGER,
    expiry_year INTEGER,
    credit_limit NUMERIC(15,2),
    notes VARCHAR(500),
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Constraints
ALTER TABLE cards ADD CONSTRAINT ck_cards_expiry_month_range
    CHECK ((expiry_month IS NULL) OR (expiry_month >= 1 AND expiry_month <= 12));

ALTER TABLE cards ADD CONSTRAINT ck_cards_last_four_digits_format
    CHECK ((last_four_digits IS NULL) OR (last_four_digits ~ '^[0-9]{4}$'));

ALTER TABLE cards ADD CONSTRAINT ck_cards_credit_limit_positive
    CHECK ((credit_limit IS NULL) OR (credit_limit > 0));

-- Indexes
CREATE INDEX ix_cards_account_id ON cards(account_id);
CREATE INDEX ix_cards_financial_institution_id ON cards(financial_institution_id);
CREATE INDEX ix_cards_card_type ON cards(card_type);
CREATE INDEX ix_cards_deleted_at ON cards(deleted_at);
```

3. **Add card_id to transactions**:
```sql
ALTER TABLE transactions
ADD COLUMN card_id UUID REFERENCES cards(id) ON DELETE SET NULL;

CREATE INDEX ix_transactions_card_id ON transactions(card_id);
```

4. **Downgrade**:
```python
def downgrade():
    # Remove card_id from transactions
    op.drop_column('transactions', 'card_id')

    # Drop cards table
    op.drop_table('cards')

    # Drop enum
    card_type_enum = sa.Enum(name='card_type')
    card_type_enum.drop(op.get_bind())
```

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Complete Cards Feature (Size: M, Priority: P0)

**Goal**: Deliver a complete cards management system with transaction integration.

**Scope**:
- **Include**: Cards CRUD, account association (required), transaction card reference, soft delete, validation, authorization, audit logging
- **Exclude**: Card spending analytics, card statement import

**Detailed Tasks**:

**Task Group 1: Database Layer (6 hours)**
- [ ] Add `CardType` enum to `src/models/enums.py`
- [ ] Create `src/models/card.py` with SQLAlchemy model
- [ ] Add `card_id` FK to `src/models/transaction.py`
- [ ] Export from `src/models/__init__.py`
- [ ] Create Alembic migration
- [ ] Test migration upgrade/downgrade

**Task Group 2: Repository Layer (3 hours)**
- [ ] Create `src/repositories/card_repository.py`
- [ ] Implement user-scoped queries (via account ownership)
- [ ] Export from `src/repositories/__init__.py`
- [ ] Write unit tests

**Task Group 3: Schema Layer (2 hours)**
- [ ] Create `src/schemas/card.py`
- [ ] Update `src/schemas/transaction.py` with card_id
- [ ] Export from `src/schemas/__init__.py`
- [ ] Write validation tests

**Task Group 4: Service Layer (4 hours)**
- [ ] Create `src/services/card_service.py`
- [ ] Implement account ownership validation
- [ ] Export from `src/services/__init__.py`
- [ ] Write unit tests

**Task Group 5: API Routes (3 hours)**
- [ ] Create `src/api/routes/cards.py`
- [ ] Add service factory to `src/api/dependencies.py`
- [ ] Register router in `src/main.py`
- [ ] Add metadata endpoint for card types

**Task Group 6: Integration Tests (6 hours)**
- [ ] Create `tests/integration/test_card_routes.py`
- [ ] Test all CRUD operations
- [ ] Test account ownership validation
- [ ] Test transaction-card relationship
- [ ] Test authorization (cannot access other user's cards)
- [ ] Test validation rules

**Task Group 7: Code Quality (2 hours)**
- [ ] Run ruff format/check
- [ ] Run mypy
- [ ] Ensure 80%+ coverage
- [ ] Verify Swagger documentation

**Estimated Effort**:
- **Total**: 26 hours (4-5 developer days)

### 4.2 Implementation Sequence

```
Database Layer (6h)
    │
    ▼
Repository Layer (3h)
    │
    ▼
Schema Layer (2h)
    │
    ▼
Service Layer (4h)
    │
    ▼
API Routes (3h)
    │
    ▼
Integration Tests (6h)
    │
    ▼
Code Quality (2h)
```

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] **Is this the SIMPLEST solution?**
  - Yes. Single `cards` table with required account link. No complex payment method hierarchies.

- [x] **Have we avoided premature optimization?**
  - Yes. Simple indexes, no caching, no denormalization.

- [x] **Does this align with existing patterns?**
  - Yes. Follows `accounts` pattern for user-owned data with soft delete.

- [x] **Are we solving the actual problem?**
  - Yes. Users need to track which card was used for transactions.

### Alternatives Considered

**Alternative 1: Cards without required account link**
- **Why NOT chosen**: Cards don't exist independently - they're always tied to accounts

**Alternative 2: Separate credit_cards and debit_cards tables**
- **Why NOT chosen**: Over-engineered, both have same fields, single table simpler

**Alternative 3: Embed card info in transactions**
- **Why NOT chosen**: Same card used for multiple transactions, normalization better

---

## 6. Security Considerations

### Data Security

- **Last 4 digits ONLY** - never store full card numbers
- **NEVER store CVV/CVC** - these must never touch the database
- **Check constraint enforces format**: `CHECK (last_four_digits ~ '^[0-9]{4}$')`

### Authorization

- Cards accessed through account ownership
- User owns account → User owns cards on that account
- Service layer validates account ownership on every operation

---

## 7. Acceptance Testing Checklist

### Database

- [ ] Migration runs successfully
- [ ] card_type enum created with 2 values
- [ ] cards table created with all columns
- [ ] transactions.card_id column added
- [ ] All constraints enforced
- [ ] RESTRICT prevents deleting accounts with cards
- [ ] SET NULL on card delete preserves transactions

### API

- [ ] List cards returns only user's cards (via account ownership)
- [ ] Create card requires valid account_id owned by user
- [ ] Create card with other user's account returns 403
- [ ] Get card by ID works for owned cards
- [ ] Get other user's card returns 404 (not 403 for security)
- [ ] Update card works for owned cards
- [ ] Delete card soft-deletes
- [ ] Transaction can reference card_id
- [ ] Transaction card_id set to NULL when card deleted

### Validation

- [ ] account_id is required
- [ ] Empty name rejected
- [ ] Invalid last_four_digits rejected
- [ ] Expiry coupling enforced
- [ ] Negative credit_limit rejected

---

## Appendix A: SQL Schema

```sql
-- Create card_type enum
CREATE TYPE card_type AS ENUM ('credit_card', 'debit_card');

-- Create cards table
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    financial_institution_id UUID,
    card_type card_type NOT NULL,
    name VARCHAR(100) NOT NULL,
    last_four_digits VARCHAR(4),
    card_network VARCHAR(50),
    expiry_month INTEGER,
    expiry_year INTEGER,
    credit_limit NUMERIC(15,2),
    notes VARCHAR(500),
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_cards_account_id
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cards_financial_institution_id
        FOREIGN KEY (financial_institution_id) REFERENCES financial_institutions(id) ON DELETE SET NULL,

    CONSTRAINT ck_cards_expiry_month_range
        CHECK ((expiry_month IS NULL) OR (expiry_month >= 1 AND expiry_month <= 12)),
    CONSTRAINT ck_cards_last_four_digits_format
        CHECK ((last_four_digits IS NULL) OR (last_four_digits ~ '^[0-9]{4}$')),
    CONSTRAINT ck_cards_credit_limit_positive
        CHECK ((credit_limit IS NULL) OR (credit_limit > 0))
);

-- Indexes
CREATE INDEX ix_cards_account_id ON cards(account_id);
CREATE INDEX ix_cards_financial_institution_id ON cards(financial_institution_id);
CREATE INDEX ix_cards_card_type ON cards(card_type);
CREATE INDEX ix_cards_deleted_at ON cards(deleted_at);

-- Add card_id to transactions
ALTER TABLE transactions
ADD COLUMN card_id UUID REFERENCES cards(id) ON DELETE SET NULL;

CREATE INDEX ix_transactions_card_id ON transactions(card_id);
```

---

## Appendix B: API Examples

### Create Credit Card

```bash
POST /api/v1/cards
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Chase Sapphire Reserve",
  "card_type": "credit_card",
  "account_id": "550e8400-e29b-41d4-a716-446655440010",
  "last_four_digits": "4242",
  "card_network": "Visa",
  "expiry_month": 12,
  "expiry_year": 2027,
  "credit_limit": 25000.00,
  "financial_institution_id": "550e8400-e29b-41d4-a716-446655440001"
}

# Response: 201 Created
{
  "id": "550e8400-e29b-41d4-a716-446655440100",
  "name": "Chase Sapphire Reserve",
  "card_type": "credit_card",
  "last_four_digits": "4242",
  "card_network": "Visa",
  "expiry_month": 12,
  "expiry_year": 2027,
  "credit_limit": "25000.00",
  "notes": null,
  "account": {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "account_name": "Chase Credit Card Account",
    "currency": "USD"
  },
  "financial_institution": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "short_name": "Chase"
  },
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Create Debit Card

```bash
POST /api/v1/cards
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Chase Checking Debit",
  "card_type": "debit_card",
  "account_id": "550e8400-e29b-41d4-a716-446655440011",
  "last_four_digits": "1234",
  "card_network": "Visa",
  "expiry_month": 6,
  "expiry_year": 2026
}

# Response: 201 Created
```

### List Cards

```bash
GET /api/v1/cards?card_type=credit_card
Authorization: Bearer <access_token>

# Response: 200 OK
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440100",
    "name": "Chase Sapphire Reserve",
    "card_type": "credit_card",
    "last_four_digits": "4242",
    "card_network": "Visa",
    "account": {...},
    "financial_institution": {...}
  }
]
```

### Create Transaction with Card

```bash
POST /api/v1/transactions
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "account_id": "550e8400-e29b-41d4-a716-446655440010",
  "card_id": "550e8400-e29b-41d4-a716-446655440100",
  "amount": -150.00,
  "description": "Restaurant dinner",
  "transaction_type": "expense",
  "transaction_date": "2025-01-15"
}
```

---

**End of Implementation Plan**
