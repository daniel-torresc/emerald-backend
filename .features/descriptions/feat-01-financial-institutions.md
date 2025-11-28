# Feature 1.1: Financial Institutions Master Data

**Phase**: 1 - Foundation
**Priority**: High
**Dependencies**: None
**Estimated Effort**: 1 week

---

## Overview

Create a centralized repository of financial institutions (banks, credit unions, brokerages, and fintech companies) that will serve as master data for the entire platform. This foundational table will enable standardized institution data, eliminate duplicate/inconsistent bank names, and support future features like bank logos and automated data enrichment.

---

## Business Context

**Problem**: Currently, bank names are stored as free-text strings in the accounts table, leading to:
- Inconsistent data: "Chase", "chase", "Chase Bank", "JPMorgan Chase" all referring to the same institution
- No standardization across users
- Inability to display bank logos or institutional metadata
- Difficult to aggregate reports by institution
- No support for international banks with proper identifiers

**Solution**: Create a centralized financial institutions table that stores standardized institution data with proper identifiers (SWIFT codes, routing numbers) and metadata.

---

## Functional Requirements

### Data to Store

The system must store the following information for each financial institution:

#### 1. Identification
- **Official Name** (required)
  - Full legal name of the institution
  - Example: "JPMorgan Chase Bank, N.A."
  - Maximum 200 characters

- **Short Name** (required)
  - Common/display name used in UI
  - Example: "Chase"
  - Maximum 100 characters

- **Institution Type** (required)
  - One of: bank, credit_union, brokerage, fintech, other
  - Helps categorize and filter institutions

#### 2. Geographic Information
- **Country Code** (required)
  - ISO 3166-1 alpha-2 country code
  - Examples: "US", "GB", "DE", "JP"
  - Used for filtering institutions by country
  - Enables international support

#### 3. Banking Identifiers
- **SWIFT Code** (optional)
  - BIC/SWIFT code for international transfers
  - Format: 8 or 11 alphanumeric characters
  - Example: "CHASUS33" (Chase)
  - Must be unique across all institutions if provided

- **Routing Number** (optional)
  - ABA routing number for US banks
  - Format: 9 digits
  - Example: "021000021" (Chase)
  - Must be unique across all institutions if provided

#### 4. Metadata
- **Logo URL** (optional)
  - URL to institution's logo image
  - Used for display in UI
  - Maximum 500 characters

- **Website URL** (optional)
  - Official website of the institution
  - Maximum 500 characters

#### 5. Status
- **Is Active** (required)
  - Boolean flag indicating if institution is operational
  - Allows marking defunct institutions as inactive
  - Default: true

#### 6. Timestamps
- **Created At** (automatic)
  - When the institution record was created

- **Updated At** (automatic)
  - When the institution record was last modified

---

## Data Model Requirements

### Table: `financial_institutions`

**Columns**:
```
id                    UUID (Primary Key)
name                  VARCHAR(200) NOT NULL
short_name            VARCHAR(100) NOT NULL
swift_code            VARCHAR(11) NULL
routing_number        VARCHAR(9) NULL
country_code          VARCHAR(2) NOT NULL
institution_type      ENUM NOT NULL
logo_url              VARCHAR(500) NULL
website_url           VARCHAR(500) NULL
is_active             BOOLEAN NOT NULL DEFAULT true
created_at            TIMESTAMP NOT NULL
updated_at            TIMESTAMP NOT NULL
```

**Indexes**:
- Primary key on `id`
- Index on `name` (for searching)
- Index on `short_name` (for searching)
- Unique partial index on `swift_code` (WHERE swift_code IS NOT NULL)
- Unique partial index on `routing_number` (WHERE routing_number IS NOT NULL)
- Index on `country_code` (for filtering by country)
- Index on `institution_type` (for filtering by type)
- Index on `is_active` (for filtering active institutions)

**Constraints**:
- SWIFT code must be unique if provided
- Routing number must be unique if provided
- Institution type must be one of the valid enum values

---

## Institution Type Enum

Create a new enum type: `InstitutionType`

**Values**:
- `bank` - Traditional banks (commercial, retail, universal banks)
- `credit_union` - Credit unions and cooperative banks
- `brokerage` - Investment firms and brokerage houses
- `fintech` - Financial technology companies (Revolut, Wise, etc.)
- `other` - Other financial institutions not covered above

---

## Seed Data Requirements

The system should be pre-populated with common financial institutions to make it easy for users to select their banks without manual entry.

### Initial Seed Set

**Top Banks**:
- JPMorgan Chase Bank (US)
- Bank of America (US)
- Wells Fargo Bank (US)
- Citibank (US)
- U.S. Bank (US)
- Goldman Sachs Bank USA (US)
- Morgan Stanley (US)
- American Express (US)
- Fidelity Investments (US)
- Vanguard (US)
- HSBC (UK)
- Barclays (UK)
- Lloyds Banking Group (UK)
- Santander (Spain)
- BBVA (Spain)
- BNP Paribas (France)
- Société Générale (France)
- Deutsche Bank (Germany)
- Commerzbank (Germany)
- ING Bank (Netherlands)
- Rabobank (Netherlands)
- UBS (Switzerland)
- Credit Suisse (Switzerland)
- UniCredit (Italy)
- Revolut (UK - Fintech)
- N26 (Germany - Fintech)
- Wise (UK - Fintech)

### Seed Data Format

Each institution should include:
- Accurate official name and short name
- Correct institution type
- Country code
- SWIFT code (if applicable)
- Routing number (for US banks)
- Logo URL (link to public logo or placeholder)
- Website URL

---

## User Capabilities After Implementation

**Direct User Capabilities**: None

This is an internal master data table. Users will not directly interact with this table in this feature. However, this table prepares the foundation for Feature 2.1 where users will be able to:
- Select institutions when creating accounts
- View institution information (name, logo) with their accounts
- Filter and group accounts by institution

**Administrative Capabilities**:
- System administrators can add new financial institutions
- System administrators can update institution information
- System administrators can mark institutions as inactive
- System administrators can manage the master institution list

---

## API Requirements

### Endpoints Needed

**1. List Financial Institutions** (Public/Authenticated)
```
GET /api/v1/financial-institutions
```
- List all active financial institutions
- Support filtering by:
  - Institution type
  - Country code
  - Search by name/short name
- Support pagination
- Return: id, name, short_name, institution_type, country_code, logo_url

**2. Get Financial Institution Details** (Public/Authenticated)
```
GET /api/v1/financial-institutions/{id}
```
- Get detailed information about a specific institution
- Return all fields

**3. Create Financial Institution** (Admin Only)
```
POST /api/v1/financial-institutions
```
- Create a new financial institution
- Validate all required fields
- Ensure SWIFT/routing number uniqueness

**4. Update Financial Institution** (Admin Only)
```
PATCH /api/v1/financial-institutions/{id}
```
- Update institution information
- Validate updated data
- Track changes in audit log

**5. Deactivate Financial Institution** (Admin Only)
```
DELETE /api/v1/financial-institutions/{id}
```
- Mark institution as inactive (is_active = false)
- Do not physically delete (referenced by accounts)

---

## Validation Rules

### Name Validation
- Official name: 1-200 characters, required
- Short name: 1-100 characters, required
- Both should be trimmed of leading/trailing whitespace

### SWIFT Code Validation
- Format: 8 or 11 alphanumeric characters
- Must be uppercase
- Must be globally unique if provided
- Optional field

### Routing Number Validation
- Format: Exactly 9 digits
- Must be globally unique if provided
- Optional field
- US banks should have routing numbers

### Country Code Validation
- Must be valid ISO 3166-1 alpha-2 code
- Must be uppercase
- Required field

### Institution Type Validation
- Must be one of: bank, credit_union, brokerage, fintech, other
- Required field

### URL Validation
- Logo URL: Valid URL format, max 500 characters
- Website URL: Valid URL format, max 500 characters
- Both optional

---

## Migration Requirements

### Database Changes
1. Create `institution_type` enum with values: bank, credit_union, brokerage, fintech, other
2. Create `financial_institutions` table with all columns and indexes
3. Run seed script to populate initial institution data

### No Data Migration Needed
- This is a new table with no dependencies
- No existing data to migrate
- Accounts table not modified in this feature

---

## Testing Requirements

### Data Integrity Tests
- Verify SWIFT code uniqueness constraint
- Verify routing number uniqueness constraint
- Verify institution type enum values
- Verify country code format

### Seed Data Tests
- Verify all 100 seed institutions are created
- Verify no duplicate SWIFT codes
- Verify no duplicate routing numbers
- Verify all US banks have routing numbers
- Verify all international banks have SWIFT codes

### API Tests
- Test listing institutions with pagination
- Test filtering by institution type
- Test filtering by country code
- Test searching by name
- Test creating institution (admin)
- Test updating institution (admin)
- Test deactivating institution (admin)
- Test authorization (non-admin cannot create/update)

---

## Success Criteria

1. ✅ `financial_institutions` table created with all required columns and indexes
2. ✅ `InstitutionType` enum created with 5 values
3. ✅ Seed script successfully populates 100 initial institutions
4. ✅ All API endpoints implemented and tested
5. ✅ Admin can manage institutions (create, update, deactivate)
6. ✅ Users/API can list and search institutions
7. ✅ All validation rules enforced
8. ✅ All tests passing
9. ✅ No breaking changes to existing functionality

---

## Future Enhancements (Out of Scope)

- Automatic logo fetching from external APIs
- Institution data enrichment from financial data providers
- Support for bank branch information
- Integration with open banking APIs
- Institution relationship tracking (parent companies, subsidiaries)

---

## Notes

- This feature does NOT modify the accounts table
- This feature does NOT require user migration
- This is purely foundational infrastructure
- Users will not see any changes until Feature 2.1 is implemented
- Focus on data quality in seed script - accurate names, codes, and metadata
