# Feature 2.2: Convert Accounts to Use Account Types Table

**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: Feature 1.2 (Account Types Master Data)
**Estimated Effort**: 1 week

---

## Overview

Migrate accounts from using a hardcoded `AccountType` enum (checking, savings, investment, other) to using the flexible `account_types` table. This enables users to create custom account types and provides a foundation for specialized account categories.

---

## Business Context

**Problem**: Accounts currently use a hardcoded enum for account_type:
- Limited to 4 values: checking, savings, investment, other
- Cannot add new types without code changes
- No support for specialized accounts (HSA, 529, Crypto, etc.)
- Many accounts forced into "other" category

**Solution**: Replace the enum field with a foreign key to the `account_types` table, enabling both system-defined and user-defined account types.

---

## Functional Requirements

### Account Changes

#### 1. Replace Account Type Field
- Remove `account_type` enum column
- Add `account_type_id` UUID foreign key column
- Link to `account_types.id`
- Field is required (NOT NULL)
- Must reference a valid account type

#### 2. Migrate Existing Data
- Map existing enum values to account_types table entries:
  - `checking` → account_types where key='checking'
  - `savings` → account_types where key='savings'
  - `investment` → account_types where key='investment'
  - `other` → account_types where key='other'
- Update all existing accounts with correct account_type_id

---

## User Capabilities After Implementation

### Account Creation
- **Select Account Type**: Choose from system types + user's custom types
- **See Type Descriptions**: View helpful descriptions for each type
- **See Type Icons**: Visual icons for each account type
- **Filter Types**: Filter by system vs custom types
- **Search Types**: Search for account type by name

### Custom Account Type Management
- **Create Custom Types**: Add specialized account types (HSA, 529, Crypto, etc.)
- **Edit Custom Types**: Modify name, description, icon of own types
- **Deactivate Types**: Hide unused types without deleting
- **Reorder Types**: Control display order in dropdowns

### Account Management
- **Change Account Type**: Update type on existing accounts
- **View Type Metadata**: See type name, description, icon
- **Type-Based Filtering**: Filter accounts by type
- **Type-Based Grouping**: Group accounts by type in UI

### Reporting & Analytics
- **Filter by Type**: Filter account lists by account type
- **Group by Type**: See all accounts of a specific type
- **Type Summary**: View total balances by account type
- **Custom Type Analytics**: See balances across custom types

---

## Data Model Requirements

### Modify Table: `accounts`

**Add Column**:
```
account_type_id   UUID NOT NULL (FK to account_types.id)
```

**Remove Column**:
```
account_type   ENUM(checking, savings, investment, other)  ← REMOVE THIS
```

**Add Index**:
- Index on `account_type_id` (for filtering and joins)

**Add Foreign Key**:
- `account_type_id` → `account_types.id`
- ON DELETE RESTRICT (cannot delete type if accounts use it)

**Add Relationship**:
- One-to-many: One account type can classify many accounts
- Many-to-one: Each account has exactly one account type

---

## Migration Requirements

### Prerequisites
- Feature 1.2 must be complete (account_types table exists)
- System account types must be seeded (checking, savings, investment, other)

### Migration Steps

**Step 1: Add New Column**
1. Add `account_type_id UUID NULL` to accounts table (nullable initially)
2. Add foreign key constraint (ON DELETE RESTRICT)
3. Add index

**Step 2: Migrate Data**
1. For each existing account:
   - Read current `account_type` enum value
   - Find matching system account type by key
   - Set `account_type_id` to matching account type's ID

2. Mapping:
```sql
UPDATE accounts
SET account_type_id = (
  SELECT id FROM account_types
  WHERE key = accounts.account_type AND is_system = true
);
```

**Step 3: Verify Migration**
1. Verify all accounts have `account_type_id` set
2. Verify no orphaned references
3. Verify counts match:
   - Count of accounts with enum='checking' = count with account_type.key='checking'

**Step 4: Make Required**
1. Change `account_type_id` to NOT NULL
2. Verify constraint enforced

**Step 5: Remove Old Column**
1. Drop `account_type` enum column
2. Drop `AccountType` enum type from database

---

## API Requirements

### Modified Endpoints

**1. Create Account** (Updated)
```
POST /api/v1/accounts
```
- Change `account_type` field to `account_type_id`
- Accept UUID instead of enum string
- Validate account type exists
- Validate user owns custom type (if custom) or type is system type
- Return account type details in response

**2. Update Account** (Updated)
```
PATCH /api/v1/accounts/{id}
```
- Allow updating `account_type_id`
- Validate account type exists
- Validate user owns custom type or type is system type
- Prevent changing to deleted/inactive types

**3. Get Account** (Updated)
```
GET /api/v1/accounts/{id}
```
- Include account type details in response:
  - Type ID, key, name, description, icon, is_system
  - Embedded or as nested object

**4. List Accounts** (Updated)
```
GET /api/v1/accounts
```
- Include account type details for each account
- Add filtering by `account_type_id`
- Add grouping by account type (optional query parameter)
- Return account type metadata for display

---

## Validation Rules

### Account Type ID Validation
- Must be valid UUID format
- Must reference an existing account type
- Account type must be active (is_active = true)
- Account type must be either:
  - System type (is_system = true), OR
  - Custom type owned by current user (user_id = current_user.id)
- Cannot be NULL (required field)

### Business Rules
- Users can select any system account type
- Users can select their own custom account types
- Users cannot select other users' custom account types
- Cannot delete account type if accounts reference it (ON DELETE RESTRICT)
- Can deactivate account type (but existing accounts keep reference)

---

## Backward Compatibility

### For API Clients

**Breaking Changes**:
- `account_type` field removed from request/response
- `account_type_id` field added to request/response
- Clients must update to use UUIDs instead of enum strings

**Migration Guide for Clients**:
1. Stop sending `account_type` enum string
2. Start sending `account_type_id` UUID
3. Map old enum values to system account type IDs:
   - "checking" → GET /api/v1/account-types?key=checking (system)
   - "savings" → GET /api/v1/account-types?key=savings (system)
   - etc.

**Response Format Change**:
```json
// OLD
{
  "id": "...",
  "account_name": "My Checking",
  "account_type": "checking"
}

// NEW
{
  "id": "...",
  "account_name": "My Checking",
  "account_type_id": "uuid-here",
  "account_type": {
    "id": "uuid-here",
    "key": "checking",
    "name": "Checking Account",
    "icon": "💳"
  }
}
```

---

## Testing Requirements

### Data Integrity Tests
- Verify foreign key constraint works
- Verify ON DELETE RESTRICT behavior
- Verify NOT NULL constraint on account_type_id
- Verify account_type enum column removed
- Verify AccountType enum removed from database

### Migration Tests
- Verify all accounts migrated successfully
- Verify enum value mapping correct:
  - All "checking" accounts → checking account_type_id
  - All "savings" accounts → savings account_type_id
  - All "investment" accounts → investment account_type_id
  - All "other" accounts → other account_type_id
- Verify no accounts have NULL account_type_id
- Verify account counts match pre/post migration

### API Tests
- Test creating account with system type
- Test creating account with custom type
- Test creating account with other user's custom type (should fail)
- Test updating account type to different system type
- Test updating account type to custom type
- Test listing accounts with type details
- Test filtering accounts by type
- Test validation: invalid type ID
- Test validation: inactive type
- Test validation: NULL type (should fail)

### Business Logic Tests
- Test cannot delete account type in use
- Test can deactivate account type in use
- Test custom types only visible to owner
- Test system types visible to all users

---

## Success Criteria

1. ✅ `account_type_id` column added to accounts table (NOT NULL)
2. ✅ `account_type` enum column removed from accounts table
3. ✅ `AccountType` enum removed from database
4. ✅ Foreign key and index created
5. ✅ All existing accounts migrated successfully
6. ✅ Migration mapping verified correct
7. ✅ API endpoints updated to use account_type_id
8. ✅ Users can create accounts with system and custom types
9. ✅ Account type details displayed in UI
10. ✅ Filtering and grouping by type works
11. ✅ All tests passing
12. ✅ API clients updated and tested

---

## Rollback Plan

If issues arise during migration:
1. Stop migration process
2. Re-add `account_type` enum column
3. Copy data from account_type_id back to account_type enum
4. Remove account_type_id column
5. Re-add AccountType enum to database
6. Restore API to use enum

---

## Future Enhancements (Out of Scope)

- Bulk re-categorize accounts by type
- Account type suggestions based on account name
- Account type templates with default settings
- Account type analytics dashboard
- Import/export account type configurations

---

## Notes

- This is a BREAKING CHANGE for API clients
- Coordinate with frontend/mobile teams for simultaneous deployment
- Provide clear migration guide for API clients
- Test migration on copy of production data first
- Consider staged rollout if possible
- Monitor for errors after deployment
- Have rollback plan ready
