# Database Schema Improvements Proposal

**Date:** 2025-11-27
**Status:** Draft for Review
**Priority:** Phase 1 Implementation

---

## Overview

This document outlines the approved database schema improvements for the Emerald Finance Platform, focusing on enhanced financial tracking, flexible categorization through taxonomies, and better transaction metadata.

---

## 1. FINANCIAL INSTITUTIONS (HIGH PRIORITY)

### Purpose
Normalize bank/financial institution data to enable standardization, enrichment, and analytics.

### New Table: `financial_institutions`

```python
class FinancialInstitution(Base, TimestampMixin):
    """
    Financial institution (bank, credit union, brokerage, fintech) master data.

    Attributes:
        id: UUID primary key
        name: Official institution name (e.g., "JPMorgan Chase Bank, N.A.")
        short_name: Common/display name (e.g., "Chase")
        swift_code: BIC/SWIFT code for international transfers (nullable)
        routing_number: ABA routing number for US banks (nullable)
        country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "GB")
        institution_type: Type of institution (enum)
        logo_url: URL to institution logo (nullable)
        website_url: Official website URL (nullable)
        is_active: Whether institution is active/operational
        created_at: When record was created
        updated_at: When record was last updated
    """
    __tablename__ = "financial_institutions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    short_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Banking codes
    swift_code: Mapped[str | None] = mapped_column(String(11), nullable=True, index=True)
    routing_number: Mapped[str | None] = mapped_column(String(9), nullable=True, index=True)

    # Location & type
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    institution_type: Mapped[InstitutionType] = mapped_column(nullable=False, index=True)

    # Metadata
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Timestamps (from TimestampMixin)
    # created_at, updated_at

    __table_args__ = (
        # Unique constraint on SWIFT code (if provided)
        Index('ix_financial_institutions_swift', 'swift_code', unique=True, postgresql_where=text('swift_code IS NOT NULL')),
        # Unique constraint on routing number (if provided)
        Index('ix_financial_institutions_routing', 'routing_number', unique=True, postgresql_where=text('routing_number IS NOT NULL')),
    )

class InstitutionType(str, enum.Enum):
    """Types of financial institutions."""
    bank = "bank"
    credit_union = "credit_union"
    brokerage = "brokerage"
    fintech = "fintech"
    other = "other"
```

### Changes to `accounts` table

**Add:**
```python
financial_institution_id: Mapped[UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("financial_institutions.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)

# Relationship
financial_institution: Mapped["FinancialInstitution" | None] = relationship(
    "FinancialInstitution",
    lazy="selectin",
)
```

**Remove:**
```python
# DEPRECATED - will be migrated to financial_institution_id
bank_name: Mapped[str | None]  # Keep temporarily for migration
```

**Migration Strategy:**
1. Create `financial_institutions` table with seed data (top 100 US/international banks)
2. Add `financial_institution_id` column to `accounts` (nullable)
3. Run migration script to match `bank_name` → `financial_institution_id`
4. Keep `bank_name` for unmatched banks (manual cleanup)
5. Eventually deprecate `bank_name` field

---

## 2. PAYMENT METHODS / FINANCIAL INSTRUMENTS (HIGH PRIORITY)

### Purpose
Track which credit card, debit card, or payment instrument was used for each transaction.

### New Table: `payment_methods`

```python
class PaymentMethodType(str, enum.Enum):
    """Types of payment methods."""
    credit_card = "credit_card"
    debit_card = "debit_card"
    bank_transfer = "bank_transfer"
    digital_wallet = "digital_wallet"  # Apple Pay, Google Pay, PayPal
    cash = "cash"
    check = "check"
    other = "other"

class PaymentMethod(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    Payment method/financial instrument used for transactions.

    Represents physical or digital payment instruments (cards, wallets, etc.)
    that users can link to transactions for better tracking.

    Attributes:
        id: UUID primary key
        user_id: Owner of the payment method
        account_id: Linked account (optional - for debit cards linked to checking)
        financial_institution_id: Issuing institution (optional)
        method_type: Type of payment method
        name: User-defined name (e.g., "Chase Sapphire Reserve")
        last_four_digits: Last 4 digits for cards (for identification)
        card_network: Card network (Visa, Mastercard, Amex, etc.) - optional
        expiry_month: Card expiration month (1-12) - optional
        expiry_year: Card expiration year (YYYY) - optional
        credit_limit: Credit limit for credit cards - optional
        is_primary: Whether this is the user's primary payment method
        notes: User notes
        created_at, updated_at, deleted_at: Timestamps
        created_by, updated_by: Audit fields
    """
    __tablename__ = "payment_methods"

    # Ownership
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional links
    account_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked account (e.g., checking account for debit card)",
    )

    financial_institution_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Issuing bank/institution",
    )

    # Method details
    method_type: Mapped[PaymentMethodType] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Card-specific fields (nullable for non-card methods)
    last_four_digits: Mapped[str | None] = mapped_column(String(4), nullable=True)
    card_network: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Visa, Mastercard, Amex, Discover, etc."
    )
    expiry_month: Mapped[int | None] = mapped_column(nullable=True)
    expiry_year: Mapped[int | None] = mapped_column(nullable=True)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)

    # Metadata
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    account: Mapped["Account" | None] = relationship("Account", foreign_keys=[account_id], lazy="selectin")
    financial_institution: Mapped["FinancialInstitution" | None] = relationship(
        "FinancialInstitution",
        foreign_keys=[financial_institution_id],
        lazy="selectin",
    )

    __table_args__ = (
        # Ensure expiry_month is valid (1-12)
        CheckConstraint(
            "expiry_month IS NULL OR (expiry_month >= 1 AND expiry_month <= 12)",
            name="ck_payment_methods_expiry_month",
        ),
        # Unique constraint: one primary payment method per user
        Index(
            "ix_payment_methods_user_primary",
            "user_id",
            unique=True,
            postgresql_where=text("is_primary = true AND deleted_at IS NULL"),
        ),
    )
```

### Changes to `transactions` table

**Add:**
```python
payment_method_id: Mapped[UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("payment_methods.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    comment="Payment method/card used for this transaction",
)

# Relationship
payment_method: Mapped["PaymentMethod" | None] = relationship(
    "PaymentMethod",
    lazy="selectin",
)
```

**Use Cases:**
- User has a Chase Checking Account (account)
- User has a Chase Debit Card (payment_method linked to that account)
- User has a Chase Sapphire Credit Card (payment_method, separate account)
- Transaction: "Bought groceries with Chase Sapphire" → links to credit card account + payment_method

---

## 3. TAXONOMIES (HIGH PRIORITY)

### Purpose
Flexible, hierarchical categorization system that supports multiple independent classification schemes per user.

### New Table: `taxonomies`

```python
class Taxonomy(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    User-specific taxonomy (classification scheme) for transactions.

    Taxonomies are independent categorization systems. Examples:
    - "Categories": Sports, Home, Rent, Payroll
    - "Trips": Venezia 2024, Portugal 2025
    - "Projects": Kitchen Renovation, Car Repair

    Attributes:
        id: UUID primary key
        user_id: Owner of the taxonomy
        name: Taxonomy name (e.g., "Categories", "Trips")
        description: Optional description
        icon: Icon identifier or emoji
        is_system: Whether this is a predefined system taxonomy
        sort_order: Display order
        created_at, updated_at, deleted_at: Timestamps
        created_by, updated_by: Audit fields
    """
    __tablename__ = "taxonomies"

    # Ownership
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Taxonomy details
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # System vs custom
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True for predefined taxonomies (e.g., Categories)",
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    terms: Mapped[list["TaxonomyTerm"]] = relationship(
        "TaxonomyTerm",
        back_populates="taxonomy",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # Unique taxonomy name per user
        Index(
            "ix_taxonomies_user_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
```

### New Table: `taxonomy_terms`

```python
class TaxonomyTerm(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    Individual term/value within a taxonomy (hierarchical).

    Terms can have parent-child relationships for hierarchical categorization.
    Examples:
    - Taxonomy "Categories":
      - Home (parent)
        - Rent (child)
        - Utilities (child)
          - Electricity (grandchild)

    Attributes:
        id: UUID primary key
        taxonomy_id: Parent taxonomy
        parent_term_id: Parent term (for hierarchy) - nullable
        name: Term name (e.g., "Groceries", "Venezia 2024")
        description: Optional description
        icon: Icon identifier or emoji
        sort_order: Display order within parent
        created_at, updated_at, deleted_at: Timestamps
        created_by, updated_by: Audit fields
    """
    __tablename__ = "taxonomy_terms"

    # Relationships
    taxonomy_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_term_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomy_terms.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Parent term for hierarchical categorization",
    )

    # Term details
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Ordering
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)

    # Relationships
    taxonomy: Mapped["Taxonomy"] = relationship("Taxonomy", back_populates="terms", lazy="selectin")
    parent_term: Mapped["TaxonomyTerm" | None] = relationship(
        "TaxonomyTerm",
        remote_side="TaxonomyTerm.id",
        foreign_keys=[parent_term_id],
        lazy="selectin",
        back_populates="child_terms",
    )
    child_terms: Mapped[list["TaxonomyTerm"]] = relationship(
        "TaxonomyTerm",
        foreign_keys=[parent_term_id],
        lazy="selectin",
        back_populates="parent_term",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Unique term name per taxonomy
        Index(
            "ix_taxonomy_terms_taxonomy_name",
            "taxonomy_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Prevent self-reference
        CheckConstraint("id != parent_term_id", name="ck_taxonomy_terms_no_self_reference"),
    )
```

### New Table: `transaction_taxonomy_terms` (junction table)

```python
class TransactionTaxonomyTerm(Base, TimestampMixin):
    """
    Junction table linking transactions to taxonomy terms (many-to-many).

    A transaction can be classified by multiple taxonomies:
    - Transaction "Dinner in Venice"
      - Categories: Food > Restaurants
      - Trips: Venezia 2024
      - Projects: Honeymoon
    """
    __tablename__ = "transaction_taxonomy_terms"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    transaction_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    taxonomy_term_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomy_terms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction", lazy="selectin")
    taxonomy_term: Mapped["TaxonomyTerm"] = relationship("TaxonomyTerm", lazy="selectin")

    __table_args__ = (
        # Unique constraint: can't assign same term to transaction twice
        Index(
            "ix_transaction_taxonomy_terms_unique",
            "transaction_id",
            "taxonomy_term_id",
            unique=True,
        ),
    )
```

### Changes to `transactions` table

**Remove:**
```python
# DEPRECATED - replaced by transaction_taxonomy_terms
# Keep transaction_tags for backward compatibility during migration
```

**Add relationship:**
```python
taxonomy_terms: Mapped[list["TaxonomyTerm"]] = relationship(
    "TaxonomyTerm",
    secondary="transaction_taxonomy_terms",
    lazy="selectin",
)
```

---

## 4. BUDGETS (HIGH PRIORITY)

### Purpose
Track spending limits per taxonomy term with alerting.

### New Table: `budgets`

```python
class BudgetPeriod(str, enum.Enum):
    """Budget period types."""
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"
    custom = "custom"

class Budget(Base, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin):
    """
    Budget for tracking spending limits by taxonomy term.

    Budgets can be set for any taxonomy term (category, trip, project, etc.)
    and can be account-specific or across all accounts.

    Attributes:
        id: UUID primary key
        user_id: Budget owner
        taxonomy_term_id: Term to budget (e.g., "Groceries", "Venezia 2024")
        account_id: Optional account restriction
        name: Budget name
        amount: Budget limit amount
        currency: ISO 4217 currency code
        period: Budget period (monthly, yearly, custom, etc.)
        start_date: Budget start date
        end_date: Budget end date (nullable for recurring)
        alert_threshold: Alert when spending reaches this amount (nullable)
        rollover_unused: Whether to rollover unused budget to next period
        is_active: Whether budget is active
        created_at, updated_at, deleted_at: Timestamps
        created_by, updated_by: Audit fields
    """
    __tablename__ = "budgets"

    # Ownership
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What to budget
    taxonomy_term_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomy_terms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional account restriction
    account_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="If set, budget applies only to this account",
    )

    # Budget details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Period
    period: Mapped[BudgetPeriod] = mapped_column(nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="NULL for recurring budgets",
    )

    # Alerts
    alert_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Alert when spending reaches this amount",
    )

    # Settings
    rollover_unused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    taxonomy_term: Mapped["TaxonomyTerm"] = relationship("TaxonomyTerm", lazy="selectin")
    account: Mapped["Account" | None] = relationship("Account", lazy="selectin")

    __table_args__ = (
        # Currency must be valid ISO 4217 code
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_budgets_currency_format"),
        # Amount must be positive
        CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
        # Alert threshold must be <= amount
        CheckConstraint(
            "alert_threshold IS NULL OR alert_threshold <= amount",
            name="ck_budgets_alert_threshold",
        ),
    )
```

---

## 5. ACCOUNT TYPES AS TABLE (MEDIUM PRIORITY)

### Purpose
Allow custom account types with metadata (icons, descriptions).

### New Table: `account_types`

```python
class AccountTypeEntity(Base, TimestampMixin):
    """
    Account type master data (replaces AccountType enum).

    Supports both system-defined and user-defined account types.
    System types: checking, savings, investment, other
    Custom types: HSA, 529 Plan, Crypto Wallet, etc.

    Attributes:
        id: UUID primary key
        user_id: Owner for custom types, NULL for system types
        key: Unique identifier (e.g., "checking", "hsa", "crypto")
        name: Display name (e.g., "Health Savings Account")
        description: Optional description
        icon: Icon identifier or emoji
        is_system: Whether this is a system-defined type
        is_active: Whether type is available for selection
        sort_order: Display order
        created_at, updated_at: Timestamps
    """
    __tablename__ = "account_types"

    # Ownership (NULL for system types)
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL for system types, user_id for custom types",
    )

    # Type identification
    key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique identifier (e.g., 'checking', 'hsa')",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # System vs custom
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)

    __table_args__ = (
        # System types have unique keys globally
        Index(
            "ix_account_types_system_key",
            "key",
            unique=True,
            postgresql_where=text("is_system = true"),
        ),
        # Custom types have unique keys per user
        Index(
            "ix_account_types_user_key",
            "user_id",
            "key",
            unique=True,
            postgresql_where=text("is_system = false AND user_id IS NOT NULL"),
        ),
        # System types must have user_id = NULL
        CheckConstraint(
            "(is_system = true AND user_id IS NULL) OR (is_system = false AND user_id IS NOT NULL)",
            name="ck_account_types_system_user",
        ),
    )
```

### Changes to `accounts` table

**Replace:**
```python
# OLD (enum)
account_type: Mapped[AccountType] = mapped_column(nullable=False, index=True)

# NEW (foreign key)
account_type_id: Mapped[UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("account_types.id", ondelete="RESTRICT"),
    nullable=False,
    index=True,
)

# Relationship
account_type: Mapped["AccountTypeEntity"] = relationship(
    "AccountTypeEntity",
    lazy="selectin",
)
```

**Migration Strategy:**
1. Create `account_types` table with system types (checking, savings, investment, other)
2. Add `account_type_id` to `accounts` table
3. Migrate existing `account_type` enum values to references
4. Drop old `account_type` column
5. Drop `AccountType` enum from database

---

## 6. ENHANCED TRANSACTION FIELDS (HIGH PRIORITY)

### Changes to `transactions` table

**Add new fields:**
```python
# Concept fields (immutable original vs user-modified)
original_concept: Mapped[str] = mapped_column(
    String(500),
    nullable=False,
    comment="Original transaction description from bank/CSV (immutable)",
)

modified_concept: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
    comment="User's modified description (overrides original_concept for display)",
)

# Location
location_name: Mapped[str | None] = mapped_column(
    String(200),
    nullable=True,
    comment="Location where transaction occurred",
)

# Status
status: Mapped[TransactionStatus] = mapped_column(
    nullable=False,
    default=TransactionStatus.CLEARED,
    index=True,
)

# Notes (separate from description)
notes: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
    comment="User's private notes about the transaction",
)

# Payment method link (already covered in section 2)
payment_method_id: Mapped[UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("payment_methods.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
```

**New enum:**
```python
class TransactionStatus(str, enum.Enum):
    """Transaction status."""
    pending = "pending"  # Not yet cleared by bank
    cleared = "cleared"  # Cleared by bank (default)
    reconciled = "reconciled"  # User verified and reconciled
    void = "void"  # Voided/cancelled transaction
```

**Deprecate/Replace:**
```python
# OLD: description field
description: Mapped[str]  # REPLACE with original_concept

# OLD: user_notes field
user_notes: Mapped[str | None]  # REPLACE with notes
```

**Migration:**
1. Add new fields: `original_concept`, `modified_concept`, `location_name`, `status`, `notes`
2. Migrate data: `description` → `original_concept`
3. Migrate data: `user_notes` → `notes`
4. Drop old fields in future migration

---

## 7. REMOVE COLOR FIELDS (CLEANUP)

### Changes to existing tables

**`accounts` table - REMOVE:**
```python
color_hex: Mapped[str]  # REMOVE - not best practice
```

**`account_shares` table - no color field (OK)**

**Future tables - DO NOT ADD color_hex fields**

**Migration:**
1. Drop `color_hex` column from `accounts` table
2. UI should use predefined color schemes based on account type or user preferences (stored in user settings, not per-account)

---

## 8. REMOVE TransactionType ENUM (CLEANUP)

### Changes to `transactions` table

**Remove:**
```python
transaction_type: Mapped[TransactionType]  # REMOVE - not needed
```

**Rationale:**
- Transaction type (income/expense) can be inferred from amount sign
- Positive amount = income
- Negative amount = expense
- Transfer type can be identified by linked transaction or taxonomy

**Migration:**
1. Drop `transaction_type` column from `transactions` table
2. Update application logic to infer type from amount
3. If explicit type needed, use taxonomy term (e.g., "Type: Income" taxonomy)

---

## MIGRATION PLAN

### Phase 1: Core Entities (Week 1-2)
1. Create `financial_institutions` table + seed data
2. Create `payment_methods` table
3. Add FK to `accounts.financial_institution_id`
4. Add FK to `transactions.payment_method_id`
5. Migrate `accounts.bank_name` → `financial_institution_id`

### Phase 2: Taxonomies (Week 3-4)
1. Create `taxonomies` table
2. Create `taxonomy_terms` table
3. Create `transaction_taxonomy_terms` junction table
4. Seed default "Categories" taxonomy per user
5. Migrate `transaction_tags` → `taxonomy_terms`

### Phase 3: Budgets (Week 5)
1. Create `budgets` table
2. Build budget tracking logic in services

### Phase 4: Account Types (Week 6)
1. Create `account_types` table + seed system types
2. Add `accounts.account_type_id` FK
3. Migrate enum → FK
4. Drop old `account_type` column

### Phase 5: Enhanced Transactions (Week 7)
1. Add new transaction fields
2. Migrate existing data
3. Drop deprecated fields

### Phase 6: Cleanup (Week 8)
1. Drop `color_hex` from accounts
2. Drop `transaction_type` from transactions
3. Drop deprecated columns
4. Optimize indexes
5. Update documentation

---

## DATABASE STATISTICS (After Implementation)

### New Tables: 14 (+6 from current 8)
1. users
2. refresh_tokens
3. audit_logs
4. accounts
5. account_shares
6. transactions
7. transaction_tags (deprecated, keep for migration)
8. **financial_institutions** (NEW)
9. **payment_methods** (NEW)
10. **taxonomies** (NEW)
11. **taxonomy_terms** (NEW)
12. **transaction_taxonomy_terms** (NEW - junction)
13. **budgets** (NEW)
14. **account_types** (NEW)
15. alembic_version

### New Enums: 5 (+2)
1. AuditAction (22 values)
2. AuditStatus (3 values)
3. PermissionLevel (3 values)
4. **InstitutionType** (NEW - 5 values)
5. **PaymentMethodType** (NEW - 7 values)
6. **BudgetPeriod** (NEW - 6 values)
7. **TransactionStatus** (NEW - 4 values)

### Removed Enums: 1
- ~~AccountType~~ (converted to table)
- ~~TransactionType~~ (removed entirely)

---

## NEXT STEPS

1. **Review and approve** this proposal
2. **Prioritize** which phase to implement first
3. **Design API endpoints** for new entities
4. **Create Alembic migrations** for Phase 1
5. **Update Pydantic schemas** for new models
6. **Implement services** for business logic
7. **Write tests** for new functionality
8. **Update documentation**

---

**Questions for Review:**
1. Should we keep `merchant` as free text or normalize it later?
2. Do we need `payment_methods` table or is it overkill for MVP?
3. Should we implement all phases or start with Phase 1-2 only?
4. Any concerns about the taxonomy design?
