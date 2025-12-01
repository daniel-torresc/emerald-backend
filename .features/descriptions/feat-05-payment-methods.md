# Feature 2.3: Payment Methods for Transactions

**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: Feature 1.1 (Financial Institutions Master Data)
**Estimated Effort**: 2 weeks

---

## Overview

Create a payment methods system that allows users to track which financial instrument (credit card, debit card, digital wallet, cash, etc.) was used for each transaction. This enables better spending analysis, credit card tracking, and rewards optimization.

---

## Business Context

**Problem**: Currently, there's no way to track which payment method was used for transactions:
- Cannot track which credit card was used
- Cannot monitor credit card spending vs limits
- Cannot track card expiration dates
- Cannot analyze spending by payment method
- Cannot identify which cards earn rewards

**Solution**: Create a `payment_methods` table to store user's payment instruments, and link transactions to payment methods.

---

## Functional Requirements

### Payment Method Data

Store the following for each payment method:

#### 1. Ownership & Linking
- **User ID** (required): Owner of the payment method
- **Account ID** (optional): Linked account (e.g., debit card linked to checking account)
- **Financial Institution ID** (optional): Issuing bank/institution

#### 2. Method Details
- **Method Type** (required): credit_card, debit_card, bank_transfer, digital_wallet, cash, check, other
- **Name** (required): User-defined name (e.g., "Chase Sapphire Reserve", "Wallet Cash")
- **Last Four Digits** (optional): Last 4 digits of card number

#### 3. Card-Specific Information
- **Card Network** (optional): Visa, Mastercard, Amex, Discover, etc.
- **Expiry Month** (optional): 1-12
- **Expiry Year** (optional): YYYY format
- **Credit Limit** (optional): For credit cards, track credit limit

#### 4. Metadata
- **Is Primary** (required): Flag for default payment method
- **Notes** (optional): User's notes about the payment method

#### 5. Audit & Lifecycle
- Soft delete support
- Created at, updated at timestamps
- Created by, updated by audit fields

---

## Payment Method Types

Create enum: `PaymentMethodType`

**Values**:
- `credit_card`: Credit cards with credit limits and rewards
- `debit_card`: Debit cards linked to checking/savings accounts
- `bank_transfer`: Direct bank transfers, ACH, wire transfers
- `digital_wallet`: Apple Pay, Google Pay, PayPal, Venmo, Cash App
- `cash`: Physical cash transactions
- `check`: Paper checks
- `other`: Other payment methods

---

## User Capabilities

### Payment Method Management
- Create payment methods (cards, wallets, etc.)
- Edit payment method details
- Delete payment methods (soft delete)
- Set primary payment method
- View all payment methods
- View payment method details

### Card Tracking
- Track multiple credit/debit cards
- Store last 4 digits for identification
- Track card expiration dates
- Track credit limits for credit cards
- Link cards to issuing institutions
- Link debit cards to bank accounts

### Payment Method Organization
- Name payment methods descriptively
- Add notes to payment methods
- Mark frequently used method as primary
- Filter by payment method type
- View inactive/deleted methods

### Expiration Alerts
- See which cards are expiring soon
- Filter by expiration date
- Update expiration when card renewed

---

## Data Model Requirements

### New Table: `payment_methods`

**Columns**:
```
id                          UUID (Primary Key)
user_id                     UUID NOT NULL (FK to users)
account_id                  UUID NULL (FK to accounts)
financial_institution_id    UUID NULL (FK to financial_institutions)
method_type                 ENUM NOT NULL
name                        VARCHAR(100) NOT NULL
last_four_digits            VARCHAR(4) NULL
card_network                VARCHAR(50) NULL
expiry_month                INTEGER NULL
expiry_year                 INTEGER NULL
credit_limit                NUMERIC(15,2) NULL
is_primary                  BOOLEAN NOT NULL DEFAULT false
notes                       VARCHAR(500) NULL
created_at                  TIMESTAMP NOT NULL
updated_at                  TIMESTAMP NOT NULL
deleted_at                  TIMESTAMP NULL
created_by                  UUID NULL
updated_by                  UUID NULL
```

**Indexes**:
- Primary key on `id`
- Index on `user_id`
- Index on `account_id`
- Index on `financial_institution_id`
- Index on `method_type`
- Index on `deleted_at`
- Unique partial index on `user_id` WHERE `is_primary = true AND deleted_at IS NULL` (only one primary per user)

**Constraints**:
- CHECK: `expiry_month IS NULL OR (expiry_month >= 1 AND expiry_month <= 12)`
- CHECK: Card-related fields should be NULL for non-card types (optional, can be business logic)

**Foreign Keys**:
- `user_id` → `users.id` ON DELETE CASCADE
- `account_id` → `accounts.id` ON DELETE SET NULL
- `financial_institution_id` → `financial_institutions.id` ON DELETE SET NULL

---

## API Requirements

### Endpoints

**1. List Payment Methods**
```
GET /api/v1/payment-methods
```
- List user's payment methods
- Include linked account and institution details
- Filter by: method_type, is_primary, active/deleted
- Sort by: name, created_at, expiry_date

**2. Get Payment Method**
```
GET /api/v1/payment-methods/{id}
```
- Get detailed information
- Include linked account and institution

**3. Create Payment Method**
```
POST /api/v1/payment-methods
```
- Create new payment method
- Validate all fields
- Automatically set user_id to current user

**4. Update Payment Method**
```
PATCH /api/v1/payment-methods/{id}
```
- Update payment method details
- Can change primary status
- Cannot change user_id

**5. Delete Payment Method**
```
DELETE /api/v1/payment-methods/{id}
```
- Soft delete payment method
- Check if used by transactions (warn user)
- Remove from transactions (or set to NULL)

---

## Validation Rules

### Name Validation
- Required
- 1-100 characters
- Trimmed of whitespace

### Last Four Digits Validation
- Optional
- Exactly 4 characters if provided
- Numeric digits only
- Used for identification, not security

### Card Network Validation
- Optional
- Common values: Visa, Mastercard, Amex, Discover, Diners Club, JCB, UnionPay
- Free text to support any network

### Expiry Validation
- Both month and year optional
- If one provided, both should be provided (business rule)
- Month: 1-12
- Year: YYYY format, current year or future
- Alert if expiry date is in the past or within 60 days

### Credit Limit Validation
- Optional
- Must be positive if provided
- Typically for credit cards only

### Primary Method Validation
- Only one payment method can be primary per user
- If setting new primary, unset previous primary
- When deleting primary method, optionally prompt to set new primary

### Account Linking Validation
- Account must belong to current user
- Account should make sense for method type (e.g., debit card → checking account)

### Institution Linking Validation
- Institution must exist
- Institution should be active

---

## Business Rules

### Payment Method Types
- **Credit Card**: Should have credit_limit, card_network, expiry
- **Debit Card**: Should link to account_id, have card_network, expiry
- **Bank Transfer**: No card-specific fields needed
- **Digital Wallet**: No card-specific fields needed
- **Cash**: No card-specific fields needed
- **Check**: No card-specific fields needed

### Primary Payment Method
- User can have at most one primary payment method
- Primary method suggested as default in transaction creation
- If deleting primary method, prompt user to set new primary

### Card Expiration
- Alert users 60 days before card expires
- Allow updating expiration when card renewed
- Expired cards can still be referenced by historical transactions

---

## Testing Requirements

### Data Integrity Tests
- Verify foreign key constraints
- Verify unique primary payment method per user
- Verify soft delete functionality
- Verify expiry month validation (1-12)

### API Tests
- Test creating payment methods of each type
- Test updating payment method details
- Test setting/unsetting primary method
- Test soft deleting payment method
- Test filtering by method type
- Test expiration date validation
- Test linking to account and institution

### Business Logic Tests
- Test only one primary method per user
- Test deleting primary method behavior
- Test card expiration alerts
- Test credit limit tracking

---

## Success Criteria

1. ✅ `payment_methods` table created with all columns and indexes
2. ✅ `PaymentMethodType` enum created
3. ✅ All API endpoints implemented
4. ✅ Users can create, update, delete payment methods
5. ✅ Card-specific fields work correctly
6. ✅ Primary payment method logic works
7. ✅ Soft delete works correctly
8. ✅ All validation rules enforced
9. ✅ All tests passing

---

## Future Enhancements (Out of Scope)

- Payment method usage statistics
- Rewards tracking per card
- Automatic expiration alerts
- Card replacement tracking
- Multiple cards per account
- Payment method import from financial institutions

---

## Notes

- This feature does NOT link to transactions yet (Feature 2.4)
- Focus on payment method management and data quality
- Security: Never store full card numbers or CVV codes
- Last 4 digits are for identification only
- Encryption may be needed for sensitive fields in future
