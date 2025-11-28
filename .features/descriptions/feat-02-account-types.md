# Feature 1.2: Account Types Master Data

**Phase**: 1 - Foundation
**Priority**: High
**Dependencies**: None
**Estimated Effort**: 1 week

---

## Overview

Convert account types from a fixed enum (checking, savings, investment, other) to a flexible master data table managed by administrators. This enables admins to add specialized account types like HSA, 529 Plans, Crypto Wallets, etc., without requiring code changes.

---

## Business Context

**Problem**: Currently, account types are hardcoded as an enum with only 4 values:
- Limited to checking, savings, investment, other
- Cannot add new types without code deployment
- No support for different account types (HSA, 529, FSA, Crypto, etc.)
- No ability to customize type metadata (icons, descriptions)
- Users forced to use "other" for many legitimate account types

**Solution**: Create a flexible account_types master data table managed by administrators. All account types are available globally to all users, but only admins can create, update, or deactivate them.

---

## Functional Requirements

### Data to Store

The system must store the following information for each account type:

#### 1. Identification
- **Key** (required)
  - Unique identifier for the account type
  - Lowercase, alphanumeric with underscores
  - Examples: "checking", "savings", "hsa", "crypto_wallet"
  - Used programmatically and in URLs
  - Maximum 50 characters

- **Name** (required)
  - Display name shown to users
  - Examples: "Checking Account", "Health Savings Account", "Crypto Wallet"
  - Maximum 100 characters

- **Description** (optional)
  - Detailed description of the account type
  - Helps users understand when to use this type
  - Maximum 500 characters

#### 2. Visual Identity
- **Icon** (optional)
  - Icon URL for UI display
  - Maximum 500 characters

#### 3. Status & Ordering
- **Is Active** (required)
  - Boolean flag indicating if type is available for selection
  - Allows deactivating types without deletion
  - Default: true

- **Sort Order** (required)
  - Integer for controlling display order in UI
  - Lower numbers appear first
  - Default: 0

#### 4. Timestamps
- **Created At** (automatic)
  - When the account type was created

- **Updated At** (automatic)
  - When the account type was last modified

---

## Data Model Requirements

### Table: `account_types`

**Columns**:
```
id                    UUID (Primary Key)
key                   VARCHAR(50) NOT NULL UNIQUE
name                  VARCHAR(100) NOT NULL
description           VARCHAR(500) NULL
icon_url              VARCHAR(500) NULL
is_active             BOOLEAN NOT NULL DEFAULT true
sort_order            INTEGER NOT NULL DEFAULT 0
created_at            TIMESTAMP NOT NULL
updated_at            TIMESTAMP NOT NULL
```

**Indexes**:
- Primary key on `id`
- Unique index on `key` (for lookup and uniqueness)
- Index on `is_active` (for filtering active types)

**Constraints**:
- `key` must be unique globally
- `key` must match pattern `^[a-z0-9_]+$`

**Foreign Keys**:
- None

---

## System Account Types (Seed Data)

The following 4 system account types should be created during migration:

### 1. Checking
```
key: "checking"
name: "Checking Account"
description: "Standard checking account for daily transactions and bill payments"
is_active: true
sort_order: 1
```

### 2. Savings
```
key: "savings"
name: "Savings Account"
description: "Savings account for building emergency funds and long-term savings"
is_active: true
sort_order: 2
```

### 3. Investment
```
key: "investment"
name: "Investment Account"
description: "Investment and brokerage accounts for stocks, bonds, and mutual funds"
is_active: true
sort_order: 3
```

### 4. Other
```
key: "other"
name: "Other"
description: "Other financial accounts not covered by standard types"
is_active: true
sort_order: 99
```

---

## Capabilities After Implementation

**Regular User Capabilities**:
- View all active account types when creating/editing accounts
- Select from available account types

**Administrator Capabilities**:
- Create new account types available to all users
- Update account type metadata (name, description, icon_url, sort order)
- Deactivate account types (mark as inactive)
- Cannot delete account types that are in use by accounts

---

## API Requirements

### Endpoints Needed

**1. List Account Types** (Authenticated)
```
GET /api/v1/account-types
```
- List all account types
- Support filtering:
  - By is_active (only active types, default: true)
- Return types sorted by sort_order
- Return: id, key, name, description, icon_url, is_active, sort_order
- Available to all authenticated users

**2. Get Account Type Details** (Authenticated)
```
GET /api/v1/account-types/{id}
```
- Get detailed information about a specific account type
- Return all fields
- Available to all authenticated users

**3. Create Account Type** (Admin Only)
```
POST /api/v1/account-types
```
- Create a new account type available to all users
- Validate key uniqueness globally
- Requires admin privileges

**4. Update Account Type** (Admin Only)
```
PATCH /api/v1/account-types/{id}
```
- Update any account type
- Can update: name, description, icon, is_active, sort_order
- Cannot update: key (immutable)
- Requires admin privileges

**5. Delete Account Type** (Admin Only)
```
DELETE /api/v1/account-types/{id}
```
- Delete an account type
- Cannot delete if type is in use by any accounts
- Return error if accounts still reference this type
- Requires admin privileges

---

## Validation Rules

### Key Validation
- Format: Lowercase letters, numbers, underscores only
- Pattern: `^[a-z0-9_]+$`
- Length: 1-50 characters
- Required
- Must be globally unique
- Immutable (cannot be changed after creation)

### Name Validation
- Length: 1-100 characters
- Required
- Trimmed of leading/trailing whitespace

### Description Validation
- Length: 0-500 characters
- Optional
- Trimmed of leading/trailing whitespace

### Icon Validation
- Length: max 500 characters
- Optional
- URL to the icon image

### Sort Order Validation
- Must be integer
- Can be negative
- Default: 0

---

## Business Rules

### Account Type Management
- All account types are available to all users (global master data)
- Only administrators can create, update, or delete account types
- Regular users can only view and select from available account types

### Deletion Rules
- Account types cannot be deleted if in use by any accounts
- Instead of deletion, administrators should deactivate (set is_active = false)
- Deactivated types are hidden from selection but remain in the database

### Key Uniqueness Rules
- All account type keys must be globally unique
- Keys are immutable once created

---

## Migration Requirements

### Database Changes
1. Create `account_types` table with all columns, indexes, and constraints
2. Create seed script to populate 4 system account types
3. Verify seed data created successfully

### No Data Migration Needed
- This is a new table
- Accounts table not modified in this feature
- No existing account data to migrate (happens in Feature 2.2)

---

## Testing Requirements

### Data Integrity Tests
- Verify key uniqueness globally
- Verify key format validation (lowercase, alphanumeric, underscore)
- Verify key immutability

### Seed Data Tests
- Verify all 4 default account types created during migration
- Verify default types have correct keys, names, and metadata

### API Tests - Authenticated Users
- Test listing all account types
- Test listing only active account types
- Test getting account type details by ID
- Test regular users cannot create account types (403 Forbidden)
- Test regular users cannot update account types (403 Forbidden)
- Test regular users cannot delete account types (403 Forbidden)

### API Tests - Administrators
- Test admin can create new account type
- Test admin can update account type metadata
- Test admin can deactivate account type (is_active = false)
- Test admin can delete account type (when not in use)
- Test admin cannot delete account type in use by accounts
- Test admin cannot create duplicate key
- Test key validation (lowercase, alphanumeric, underscore)
- Test admin cannot modify key after creation

### Business Logic Tests
- Test cannot delete account type if accounts reference it
- Test deactivating account type (is_active = false)
- Test sort_order affects listing order

---

## Success Criteria

1. ✅ `account_types` table created with all columns, indexes, and constraints
2. ✅ Migration successfully creates 4 default account types
3. ✅ All uniqueness constraints working correctly
4. ✅ All API endpoints implemented and tested
5. ✅ Administrators can create, update, and delete account types
6. ✅ Regular users can only view account types
7. ✅ All validation rules enforced
8. ✅ All tests passing (80%+ coverage)
9. ✅ No breaking changes to existing functionality

---

## Future Enhancements (Out of Scope)

- Account type categories/grouping
- Icon picker UI component
- Account type usage statistics (how many accounts use each type)
- Bulk account type operations
- Account type templates/suggestions for common financial account types

---

## Notes

- This feature does NOT modify the accounts table
- Accounts still use the old enum in this feature
- Migration from enum to table happens in Feature 2.2 (or Feature 3)
- This is foundational master data infrastructure
- Account types are global and managed exclusively by administrators
- All users can view and select from available account types when creating accounts
