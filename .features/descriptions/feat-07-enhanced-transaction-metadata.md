# Feature 2.5: Enhanced Transaction Metadata

**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: None
**Estimated Effort**: 1 week

---

## Overview

Add richer metadata fields to transactions for better tracking, organization, and reconciliation. This includes immutable original descriptions, user-editable descriptions, location tracking, transaction status, and enhanced notes.

---

## Business Context

**Problem**: Current transaction data model is limited:
- Cannot preserve original description from bank/CSV
- Editing description loses original data
- No location tracking
- No status tracking (pending vs cleared)
- Limited notes functionality

**Solution**: Add new fields to capture original data, user modifications, location, status, and enhanced notes.

---

## Functional Requirements

### New Transaction Fields

#### 1. Concept Fields (Description Management)
- **Original Concept** (required, immutable)
  - Original description from bank/CSV/API
  - Never changes after creation
  - Examples: "WHOLEFDS 1234 SEATTLE WA", "SQ *COFFEE SHOP"
  - Max 500 characters

- **Modified Concept** (optional, user-editable)
  - User's friendly description
  - Overrides original for display
  - Examples: "Whole Foods - Weekly Groceries", "Coffee Shop Downtown"
  - Max 500 characters

#### 2. Location
- **Location Name** (optional)
  - Where transaction occurred
  - Examples: "Whole Foods Downtown Seattle", "Starbucks - Pike Place"
  - Max 200 characters

#### 3. Status
- **Status** (required, enum)
  - `pending`: Not yet cleared by bank
  - `cleared`: Cleared by bank (default)
  - `reconciled`: User verified and reconciled
  - `void`: Voided/cancelled transaction

#### 4. Notes
- **Notes** (optional)
  - User's private notes about transaction
  - More detailed than description
  - Can include reasons, context, receipts references
  - Text field (no length limit)

---

## User Capabilities

### Transaction Creation
- Import with original concept from CSV/API
- Optionally provide friendly modified concept
- Mark as pending if not yet cleared
- Add location if known
- Add detailed notes

### Transaction Editing
- **View Original**: Always see original description from bank
- **Edit Display Name**: Change modified concept without losing original
- **Update Location**: Add or edit location
- **Change Status**: Mark as cleared, reconciled, or void
- **Add/Edit Notes**: Add context, reasons, receipt info

### Transaction Display
- Display modified concept if set, otherwise original concept
- Show original concept in tooltip/expandable section
- Show location below description
- Status badge (pending/cleared/reconciled/void)
- Notes section expandable

### Search & Filter
- Search both original and modified concepts
- Filter by status (pending, cleared, etc.)
- Search locations
- Search notes

### Reconciliation
- Filter for unreconciled transactions
- Bulk mark as reconciled
- Match original concepts to bank statements

---

## Data Model Requirements

### Modify Table: `transactions`

**Add Columns**:
```
original_concept   VARCHAR(500) NOT NULL
modified_concept   VARCHAR(500) NULL
location_name      VARCHAR(200) NULL
status             ENUM NOT NULL DEFAULT 'cleared'
notes              TEXT NULL
```

**Remove/Rename Columns**:
```
description   → original_concept (rename + migrate data)
user_notes    → notes (rename + migrate data)
```

**Add Indexes**:
- Index on `status` (for filtering)
- Optional: Full-text index on `original_concept` + `modified_concept` for search

**Add Enum**:
```
TransactionStatus: pending, cleared, reconciled, void
```

---

## Migration Requirements

### Step 1: Add New Columns
1. Add `original_concept VARCHAR(500) NULL` (nullable initially)
2. Add `modified_concept VARCHAR(500) NULL`
3. Add `location_name VARCHAR(200) NULL`
4. Add `status ENUM NOT NULL DEFAULT 'cleared'`
5. Add `notes TEXT NULL`

### Step 2: Migrate Existing Data
1. Copy `description` → `original_concept`
2. Copy `user_notes` → `notes`
3. Set all existing transactions to `status = 'cleared'`

### Step 3: Make Required & Cleanup
1. Change `original_concept` to NOT NULL
2. Drop `description` column
3. Drop `user_notes` column

---

## API Requirements

### Modified Endpoints

**1. Create Transaction** (Updated)
```
POST /api/v1/transactions
```
Request changes:
- `description` → `original_concept` (required)
- Add `modified_concept` (optional)
- Add `location_name` (optional)
- Add `status` (optional, default: 'cleared')
- Add `notes` (optional)

**2. Update Transaction** (Updated)
```
PATCH /api/v1/transactions/{id}
```
- Allow updating `modified_concept`
- Allow updating `location_name`
- Allow updating `status`
- Allow updating `notes`
- CANNOT update `original_concept` (immutable)

**3. Get/List Transactions** (Updated)
```
GET /api/v1/transactions
```
Response changes:
- Return `original_concept`
- Return `modified_concept`
- Return `display_concept` (modified if set, otherwise original)
- Return `location_name`
- Return `status`
- Return `notes`

**4. Import Transactions** (Updated)
- Map CSV "description" → `original_concept`
- Allow optional `modified_concept` in import
- Set appropriate status (pending/cleared)

---

## Display Logic

### Concept Display Priority
```
IF modified_concept IS NOT NULL THEN
  Display: modified_concept
  Show original in tooltip/details
ELSE
  Display: original_concept
END
```

### Status Display
- **Pending**: Yellow badge, "Pending"
- **Cleared**: Green checkmark, "Cleared"
- **Reconciled**: Blue checkmark, "Reconciled"
- **Void**: Red X, "Void"

---

## Validation Rules

### Original Concept
- Required
- 1-500 characters
- Immutable after creation
- Preserved from import source

### Modified Concept
- Optional
- 1-500 characters if provided
- Can be changed anytime
- Can be set to NULL (revert to original)

### Location Name
- Optional
- 1-200 characters if provided
- Free text

### Status
- Required
- Must be one of: pending, cleared, reconciled, void
- Default: cleared

### Notes
- Optional
- No length limit
- Can be very long (receipt details, context, etc.)

---

## Business Rules

### Immutability
- Original concept CANNOT be changed after creation
- Preserves audit trail
- Enables reconciliation with bank statements

### Status Workflow
Typical flow:
1. **Pending**: Transaction created but not cleared
2. **Cleared**: Bank has processed transaction
3. **Reconciled**: User has verified against statement
4. **Void**: Transaction cancelled/reversed

### Display Preference
- Always prefer modified concept for display if set
- Show original concept for reference
- Never lose original data

---

## Testing Requirements

- Test creating transaction with all new fields
- Test updating modified concept
- Test original concept is immutable
- Test status changes
- Test display logic (modified vs original)
- Test searching across both concepts
- Test migration from old description field

---

## Success Criteria

1. ✅ New columns added to transactions table
2. ✅ TransactionStatus enum created
3. ✅ Existing data migrated successfully
4. ✅ Old columns removed
5. ✅ Original concept is immutable
6. ✅ Modified concept editable
7. ✅ Status tracking works
8. ✅ Display logic correct
9. ✅ All tests passing

---

## Notes

- This is a breaking API change
- Coordinate with frontend for simultaneous deployment
- Migration preserves all existing data
- Original concept enables better reconciliation
- Location field prepares for future geo-tagging
