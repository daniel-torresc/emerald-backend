# Feature 2.1: Link Accounts to Financial Institutions

**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: Feature 1.1 (Financial Institutions Master Data)
**Estimated Effort**: 1.5 weeks

---

## Overview

Enable users to associate their accounts with financial institutions from the master data table. This replaces the free-text `bank_name` field with a **mandatory** structured reference to the `financial_institutions` table, providing standardized institution data and enabling features like bank logos, institution-based filtering, and better analytics.

---

## Business Context

**Problem**: Currently, accounts have a free-text `bank_name` field:
- Inconsistent data: "Chase", "chase bank", "JPMorgan Chase" for the same bank
- No standardization across users
- No bank logos or institutional metadata
- Difficult to aggregate accounts by institution
- No support for SWIFT codes or routing numbers

**Solution**: Add a **mandatory** foreign key relationship from accounts to financial_institutions, requiring all accounts to reference standardized institution data.

---

## Functional Requirements

### Account Changes

#### 1. Add Financial Institution Link (MANDATORY)
- Add **mandatory** `financial_institution_id` field to accounts table
- Field is **NOT NULL** (all accounts MUST have an institution)
- Links to `financial_institutions.id`
- Users **must** select institution when creating account
- Users can update institution on existing accounts

#### 2. Remove Bank Name Field
- **IMMEDIATE REMOVAL**: Remove `bank_name` field after adding `financial_institution_id`
- Do not keep both fields temporarily
- Clean cutover from old to new system

---

## User Capabilities After Implementation

### Account Creation
- **Select Financial Institution (REQUIRED)**: When creating an account, users MUST select a financial institution from the master list
- **Search Institutions**: Users can search for institutions by name
- **Filter by Country**: Users can filter institutions by country
- **Filter by Type**: Users can filter institutions by type (bank, credit union, etc.)
- **Cannot Skip**: Institution selection is mandatory for account creation

### Account Management
- **View Institution Details**: See institution name, logo, website for all accounts
- **Update Institution**: Change which institution an account is linked to
- **Institution Metadata**: See SWIFT code, routing number if available

### Account Display
- **Bank Logos**: Display institution logos next to account names
- **Institution Names**: Show standardized institution names
- **Visual Grouping**: Group accounts by institution in UI

### Reporting & Analytics
- **Filter by Institution**: Filter account lists by financial institution
- **Group by Institution**: See all accounts at a specific institution
- **Institution Summary**: View total balances across all accounts at an institution
- **Multi-Institution Overview**: See which institutions user banks with

---

## Data Model Requirements

### Modify Table: `accounts`

**Add Column**:
```
financial_institution_id   UUID NOT NULL (FK to financial_institutions.id)
```

**Remove Column**:
```
bank_name   VARCHAR(100) NULL  ← REMOVE THIS IMMEDIATELY
```

**Add Index**:
- Index on `financial_institution_id` (for filtering and joins)

**Add Foreign Key**:
- `financial_institution_id` → `financial_institutions.id`
- ON DELETE RESTRICT (prevent deleting institutions with linked accounts)

**Add Relationship**:
- One-to-many: One financial institution can have many accounts
- Many-to-one: Each account belongs to exactly one institution

---

## Migration Requirements

### Migration Strategy

**CRITICAL**: Since the field is mandatory (NOT NULL) and there is no production data, we will:
1. Delete all existing accounts (development/test data only)
2. Add the `financial_institution_id` column as NOT NULL immediately
3. Remove the `bank_name` column
4. Start fresh with clean data

**NOTE**: This approach is ONLY valid because there is no production data. In a production environment, a data migration strategy would be required.

### Migration Steps

**Step 1: Delete All Existing Accounts**
```sql
-- Delete all existing accounts (test data only)
DELETE FROM accounts;
```

**Step 2: Add Column (NOT NULL from the start)**
```sql
-- Add NOT NULL column with foreign key
ALTER TABLE accounts
ADD COLUMN financial_institution_id UUID NOT NULL;
```

**Step 3: Add Foreign Key and Index**
```sql
-- Add foreign key (RESTRICT to prevent deleting institutions with accounts)
ALTER TABLE accounts
ADD CONSTRAINT fk_accounts_financial_institution
FOREIGN KEY (financial_institution_id)
REFERENCES financial_institutions(id)
ON DELETE RESTRICT;

-- Add index for performance
CREATE INDEX idx_accounts_financial_institution_id
ON accounts(financial_institution_id);
```

**Step 4: Remove Old Column**
```sql
ALTER TABLE accounts
DROP COLUMN bank_name;
```

---

## API Requirements

### Modified Endpoints

**1. Create Account** (Updated - REQUIRED FIELD)
```
POST /api/v1/accounts
```
- **REQUIRED** `financial_institution_id` field in request body
- Validate institution exists
- Validate institution is active (is_active = true)
- Return institution details in response
- Return 400 if institution_id missing or invalid

**Request Body**:
```json
{
  "name": "Checking Account",
  "account_type": "CHECKING",
  "financial_institution_id": "uuid-here",  // REQUIRED
  "balance": 1000.00
}
```

**2. Update Account** (Updated)
```
PATCH /api/v1/accounts/{id}
```
- Allow updating `financial_institution_id`
- **CANNOT** set to NULL (field is mandatory)
- Validate institution exists if changed
- Validate institution is active

**3. Get Account** (Updated)
```
GET /api/v1/accounts/{id}
```
- Include institution details in response:
  - Institution ID, name, short_name, logo_url, institution_type
  - Embedded or as nested object
- Always returns institution (never NULL)

**4. List Accounts** (Updated)
```
GET /api/v1/accounts
```
- Include institution details for each account
- Add filtering by `financial_institution_id`
- Add grouping by institution (optional query parameter)
- Return institution metadata for display

---

## Validation Rules

### Financial Institution ID Validation
- **REQUIRED** field for account creation
- Must be valid UUID format
- Must reference an existing institution in database
- Institution must be active (is_active = true)
- **CANNOT** be NULL or empty

### Business Rules
- Users can select any active institution
- Users are not restricted to institutions in their country
- Multiple accounts can link to same institution
- **Cannot delete** an institution that has linked accounts (ON DELETE RESTRICT)
- Users must select different institution before deleting current one

---

## User Interface Requirements

### Account Creation Form
- **REQUIRED** "Financial Institution" dropdown/autocomplete
- Field marked as required with asterisk (*)
- Show institution logo preview when selected
- Include search/filter functionality:
  - Search by name
  - Filter by country
  - Filter by type
- **No "None" or "Skip" option** - selection is mandatory
- Show validation error if not selected

### Account List/Detail View
- Display institution logo next to account name
- Show institution name below account name
- Click institution to see all accounts at that institution

### Account Edit Form
- Allow changing institution to different active institution
- **Cannot remove** institution (no clear/remove button)
- Same search/filter functionality as creation
- Show current institution as pre-selected

### Institution Filter
- Add filter option in account list: "Institution"
- Multi-select institutions
- No "Unlinked accounts" option (all accounts have institutions)

---

## Testing Requirements

### Data Integrity Tests
- Verify foreign key constraint works
- Verify ON DELETE RESTRICT behavior
- Verify NOT NULL constraint on financial_institution_id
- Verify bank_name column removed
- Verify cannot insert account without institution

### Migration Tests
- Verify all existing accounts deleted during migration
- Verify no NULL values in financial_institution_id
- Verify bank_name field is gone
- Verify migration is idempotent
- Verify new accounts can be created after migration

### API Tests
- Test creating account with valid institution (success)
- Test creating account without institution (400 error)
- Test creating account with invalid institution ID (404 error)
- Test creating account with inactive institution (400 error)
- Test updating account to change institution (success)
- Test updating account to remove institution (400 error)
- Test updating account with invalid institution (404 error)
- Test listing accounts with institution details
- Test filtering accounts by institution
- Test deleting institution with linked accounts (403/409 error)

### Business Logic Tests
- Test multiple accounts can link to same institution
- Test cannot delete institution with linked accounts
- Test displaying institution logo/name
- Test searching institutions in account form

---

## Success Criteria

1. ✅ `financial_institution_id` column added as NOT NULL
2. ✅ `bank_name` column removed from accounts table
3. ✅ Foreign key with ON DELETE RESTRICT created
4. ✅ Index on `financial_institution_id` created
5. ✅ All existing accounts deleted during migration
6. ✅ API endpoints enforce mandatory institution requirement
7. ✅ Users cannot create accounts without selecting institution
8. ✅ Users can update institution on existing accounts
9. ✅ Institution details always displayed in UI
10. ✅ Filtering and grouping by institution works
11. ✅ Cannot delete institutions with linked accounts
12. ✅ All tests passing
13. ✅ No NULL values in financial_institution_id

---

## Rollback Plan

If issues arise:
1. Alter `financial_institution_id` to allow NULL
2. Re-add `bank_name` column to accounts
3. Copy institution names back to bank_name
4. Allow time for troubleshooting
5. Remove `financial_institution_id` if necessary
6. Restore previous functionality

---

## Future Enhancements (Out of Scope)

- Auto-suggest institution based on account name
- Import account data from financial institution (open banking)
- Sync account balance with institution API
- Display institution routing numbers in account details
- Institution-specific account features
- Allow users to create custom institutions (beyond master data)
- Bulk update institutions for multiple accounts

---

## Notes

- **MANDATORY FIELD**: All accounts MUST have a financial institution
- **NO PRODUCTION DATA**: This migration deletes all existing accounts - only safe in development
- **ON DELETE RESTRICT**: Prevents accidental deletion of institutions with accounts
- **Data Integrity**: No orphaned accounts, all accounts have valid institution references
- Institution logos enhance visual account organization
- Standardized institution data improves analytics and reporting
- Clean slate approach ensures all accounts have proper institution links from the start
