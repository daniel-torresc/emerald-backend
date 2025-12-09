# Feature 2.3: Cards Management

**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: Feature 1.1 (Financial Institutions Master Data), Accounts feature
**Estimated Effort**: 1 week

---

## Overview

Provide users with the ability to manage their credit and debit cards within the system. Each card MUST be associated with an account (the account it's linked to or draws from). Cards can store relevant details such as last 4 digits, card network, expiration date, and credit limits (for credit cards). This feature also establishes the relationship between transactions and cards, allowing users to track which card was used for each transaction.

---

## Business Context

**Problem**: Users need a way to define and manage their credit and debit cards for transaction tracking:
- No central repository for tracking credit and debit cards
- No ability to store card identification details (last 4 digits, network, expiration)
- No mechanism to track credit card limits for better spending management
- No way to associate cards with their issuing financial institutions
- No ability to link transactions to the specific card used

**Solution**: Create a `cards` entity that allows users to register and manage their credit and debit cards with complete details, required association to accounts, optional association to financial institutions, and integration with transactions to track which card was used.

---

## Functional Requirements

### Core Data Attributes

Each card must capture the following information:

#### 1. Ownership & Relationships
- **Account Association** (REQUIRED): Every card MUST be linked to an account. Credit cards link to credit card accounts, debit cards link to checking/savings accounts. Card ownership is derived from account ownership.
- **Financial Institution** (optional): The bank or institution that issued the card

#### 2. Card Identification
- **Card Type** (required): Categorize as credit card or debit card
- **Display Name** (required): User-friendly name for easy identification (e.g., "Chase Sapphire Reserve", "Work Amex")
- **Last Four Digits** (optional): Final 4 digits of card number for identification purposes only (never store full card numbers)

#### 3. Card-Specific Attributes
- **Card Network** (optional): The payment network (Visa, Mastercard, American Express, Discover, etc.)
- **Expiration Month** (optional): Month when card expires (1-12)
- **Expiration Year** (optional): Year when card expires (four-digit format)
- **Credit Limit** (optional): Maximum credit available (primarily for credit cards)

#### 4. Additional Information
- **User Notes** (optional): Free-text field for personal notes, reminders, or context about the card

#### 5. Lifecycle Management
- Support soft deletion (retain data but mark as inactive)
- Track creation and modification timestamps
- Maintain audit trail of who created and last modified the record

---

## Card Type Classification

The system must support the following card categories through a `CardType` enumeration:

- **credit_card**: Credit cards issued by financial institutions with credit limits, potential rewards programs, and monthly billing cycles
- **debit_card**: Debit cards directly linked to checking or savings accounts that withdraw funds immediately upon transaction

---

## User Capabilities

Users must be able to perform the following operations with their cards:

### Basic Operations
- **Create** new cards with all relevant details (account association required)
- **View** a complete list of all their cards
- **View** detailed information for any individual card including associated account and institution
- **Update** existing card details (name, expiration, credit limit, notes, etc.)
- **Delete** cards they no longer use (using soft delete to preserve historical data)

### Organization & Discovery
- **Filter** cards by type (show only credit cards or only debit cards)
- **Filter** cards by account
- **View** inactive or deleted cards when needed for historical reference

### Relationship Management
- **Associate** cards with financial institutions (specify which bank issued the card)
- **View** all related information (institution details, linked account) when viewing a card

### Transaction Integration
- **Link** transactions to the card used for payment
- **View** which card was used for any transaction

---

## Data Model Requirements

### Database Table: `cards`

A new table must be created to store all card data with the following structure:

**Required Columns**:
- `id`: UUID, primary key, uniquely identifies each card
- `account_id`: UUID, NOT NULL, foreign key to accounts table (REQUIRED - every card must belong to an account)
- `card_type`: Enum (CardType), not null, categorizes the card (credit_card or debit_card)
- `name`: String (max 100 characters), not null, user-defined display name
- `created_at`: Timestamp, not null, when the card was created
- `updated_at`: Timestamp, not null, when the card was last modified

**Optional Columns**:
- `financial_institution_id`: UUID, nullable, foreign key to financial_institutions table, identifies the issuing institution
- `last_four_digits`: String (exactly 4 characters), nullable, last 4 digits of card number
- `card_network`: String (max 50 characters), nullable, card network name (Visa, Mastercard, etc.)
- `expiry_month`: Integer, nullable, card expiration month (1-12)
- `expiry_year`: Integer, nullable, card expiration year (four-digit format)
- `credit_limit`: Decimal (15 digits, 2 decimal places), nullable, credit limit amount
- `notes`: String (max 500 characters), nullable, user's personal notes

**Soft Delete Columns**:
- `deleted_at`: Timestamp, nullable, marks when the card was soft-deleted

**Audit Trail Columns**:
- `created_by`: UUID, nullable, user who created the record
- `updated_by`: UUID, nullable, user who last updated the record

**Required Indexes** (for query performance):
- Primary key index on `id`
- Index on `account_id` (frequent filtering by account, required FK)
- Index on `financial_institution_id` (joining to institutions)
- Index on `card_type` (filtering by type)
- Index on `deleted_at` (filtering active vs deleted records)

**Data Integrity Constraints**:
- `expiry_month` must be NULL or between 1 and 12 (inclusive)
- `last_four_digits` must be NULL or exactly 4 numeric digits
- `credit_limit` must be NULL or greater than 0
- Foreign key `account_id` references `accounts.id` with RESTRICT on delete (cannot delete account with cards)
- Foreign key `financial_institution_id` references `financial_institutions.id` with SET NULL on delete

### Transaction Table Update

Add a new column to the existing `transactions` table:

- `card_id`: UUID, nullable, foreign key to cards table, identifies which card was used for the transaction
- Foreign key references `cards.id` with SET NULL on delete (preserve transaction if card is deleted)
- Index on `card_id` for query performance

---

## API Requirements

The system must expose RESTful API endpoints to manage cards:

### List All Cards
**Endpoint**: `GET /api/v1/cards`

**Purpose**: Retrieve all cards belonging to the authenticated user (via account ownership)

**Requirements**:
- Return only cards linked to accounts owned by the current user
- Include related account and financial institution details in the response
- Support filtering by card type (credit_card, debit_card)
- Support filtering by account_id
- Support filtering to show active, deleted, or all cards
- Implement pagination for users with many cards

### Get Single Card
**Endpoint**: `GET /api/v1/cards/{id}`

**Purpose**: Retrieve detailed information about a specific card

**Requirements**:
- Return full details for the specified card
- Include complete information about linked account and financial institution
- Ensure user can only access cards linked to their own accounts (authorization check)
- Return 404 if card doesn't exist or doesn't belong to user's accounts

### Create New Card
**Endpoint**: `POST /api/v1/cards`

**Purpose**: Create a new card for the authenticated user

**Requirements**:
- Accept all card attributes in request body
- Require account_id - card must be linked to an account
- Verify that the account belongs to the current authenticated user
- Verify that financial institution (if provided) exists and is active
- Validate all input fields according to validation rules
- Return the created card with generated ID and timestamps

### Update Existing Card
**Endpoint**: `PATCH /api/v1/cards/{id}`

**Purpose**: Modify details of an existing card

**Requirements**:
- Allow partial updates (only provided fields are updated)
- Prevent changing the account_id (card cannot be moved to different account)
- Prevent changing the card_type (immutable after creation)
- Ensure user can only update cards linked to their own accounts
- Validate all provided fields according to validation rules
- Update the updated_at timestamp automatically
- Return the updated card

### Delete Card
**Endpoint**: `DELETE /api/v1/cards/{id}`

**Purpose**: Remove a card from active use

**Requirements**:
- Perform soft delete (set deleted_at timestamp, don't physically remove record)
- Ensure user can only delete cards linked to their own accounts
- Transactions referencing this card will have card_id set to NULL (handled by database FK)
- Return 204 No Content on success

---

## Validation Rules

The system must enforce the following validation rules when creating or updating cards:

### Account Association
- **Required field**: account_id must be provided
- **Ownership verification**: Account must belong to the current authenticated user
- **Existence check**: Account must exist and not be deleted

### Display Name
- **Required field**: Cannot be empty or null
- **Length**: Must be between 1 and 100 characters
- **Formatting**: Trim leading and trailing whitespace before storage

### Last Four Digits
- **Optional field**: Can be null
- **Format**: Must be exactly 4 characters when provided
- **Content**: Must contain only numeric digits (0-9)
- **Security note**: This is for identification only, never store full card numbers

### Expiration Date
- **Coupling rule**: If expiration month is provided, expiration year must also be provided (and vice versa)
- **Month range**: Must be an integer between 1 and 12 (inclusive) when provided
- **Year format**: Must be a four-digit year between 2000 and 2100 when provided

### Credit Limit
- **Optional field**: Can be null
- **Value constraint**: Must be positive (greater than zero) when provided
- **Precision**: Store with 2 decimal places for currency accuracy

### Financial Institution Association
- **Optional field**: Can be null
- **Existence check**: If provided, the institution must exist in the financial_institutions table
- **Active status**: Institution should be active (not deleted)

### Card Type
- **Required field**: Cannot be null
- **Allowed values**: Must be one of the defined CardType enum values (credit_card, debit_card)
- **Immutability**: Cannot be changed after creation

---

## Testing Requirements

The feature must include comprehensive tests covering all aspects of card functionality:

### Database & Data Integrity Tests
- Verify foreign key relationship with accounts (REQUIRED, RESTRICT on delete)
- Verify foreign key relationship with financial_institutions (optional, SET NULL on delete)
- Verify soft delete functionality (deleted_at timestamp set, records still queryable)
- Verify expiry_month constraint (only accepts 1-12 or NULL)
- Verify last_four_digits constraint (only accepts 4 numeric digits or NULL)
- Verify credit_limit constraint (must be positive or NULL)
- Verify all indexes are created
- Verify card_id column added to transactions with SET NULL behavior

### API Endpoint Tests
- Test creating credit card with all fields
- Test creating debit card linked to checking account
- Test creating card without optional fields
- Test that account_id is required
- Test that account must belong to user (403 if not)
- Test updating card details (partial updates with PATCH)
- Test that account_id cannot be changed via update
- Test that card_type cannot be changed via update
- Test retrieving individual card by ID
- Test listing all cards for a user
- Test filtering cards by type
- Test filtering cards by account
- Test filtering active vs deleted cards
- Test soft deletion of cards
- Test authorization (users cannot access other users' cards via account ownership)

### Validation Tests
- Test name validation (required, length limits, whitespace trimming)
- Test last_four_digits validation (exactly 4 digits when provided)
- Test expiry date validation (month 1-12, year format, coupling rule)
- Test credit_limit validation (must be positive)
- Test that account must exist and belong to user
- Test that financial institution must exist and be active
- Test appropriate error messages for all validation failures

### Transaction Integration Tests
- Test creating transaction with card_id
- Test that transaction card_id becomes NULL when card is soft-deleted
- Test retrieving transaction includes card details

---

## Success Criteria

The feature is considered complete and successful when all of the following conditions are met:

1. **Database Schema**: The `cards` table exists with all required and optional columns, proper data types, all indexes, and all constraints
2. **Transaction Integration**: The `transactions` table has `card_id` column with proper FK and index
3. **Enumeration**: The `CardType` enum is defined with both card types (credit_card, debit_card)
4. **API Completeness**: All five RESTful endpoints are implemented and functional (list, get, create, update, delete)
5. **CRUD Operations**: Users can successfully create, read, update, and delete their cards through the API
6. **Required Account Link**: Every card must be linked to an account owned by the user
7. **Optional Fields**: Card-specific fields (network, expiry, last four digits, credit limit) work correctly when provided
8. **Relationships**: Cards can be linked to financial institutions, and these relationships are preserved correctly
9. **Soft Delete**: Deletion sets deleted_at timestamp without removing records
10. **Validation**: All validation rules are enforced and return appropriate error messages
11. **Authorization**: Users can only access cards linked to their own accounts
12. **Testing**: All unit and integration tests pass with 80%+ coverage

---

## Scope Boundaries

### Included in This Feature
- Complete CRUD operations for cards (credit and debit)
- Required account association
- Card-specific attribute tracking (expiry, network, last 4 digits, credit limits)
- Optional relationship to financial institutions
- Soft deletion with full audit trail
- User ownership via account relationship
- Transaction-card linking (add card_id to transactions)

### Explicitly Excluded from This Feature (Future Work)
- Other payment methods (cash, check, bank transfer, etc.)
- Card spending analytics and reports
- Multiple cards per account limits
- Card verification or validation with financial institutions
- Encryption of sensitive fields
- Card sharing between users
- Default card designation

---

## Important Notes

### Security Considerations
- **NEVER store full card numbers** - only last 4 digits for identification
- **NEVER store CVV/security codes** - these should never touch the database
- Last 4 digits are for user identification only, not for payment processing

### Data Retention
- Soft delete is used to preserve historical data and maintain referential integrity
- Deleted cards remain accessible for historical transaction records (though card_id on transaction becomes NULL)

### Account Relationship
- Cards CANNOT exist without an account
- Account deletion is BLOCKED if cards exist (RESTRICT)
- This ensures data integrity and proper ownership tracking
- Card ownership is derived from account ownership - no separate user_id needed on cards
