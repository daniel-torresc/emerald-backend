# Feature 3.3: Transaction Classification with Taxonomies

**Phase**: 3 - Enhancement
**Priority**: High
**Dependencies**: Features 3.1 (Taxonomy System), 3.2 (Taxonomy Terms)
**Estimated Effort**: 2 weeks

---

## Overview

Enable transactions to be classified by multiple taxonomy terms simultaneously, replacing the simple tag system. One transaction can have terms from multiple taxonomies (e.g., "Food → Restaurants" AND "Venezia 2024" AND "Business Expenses").

---

## Business Context

**Problem**: Simple tags limit to one-dimensional classification. Cannot classify a transaction as both "Food" and "Venezia Trip" and "Business Expense" simultaneously.

**Solution**: Many-to-many relationship between transactions and taxonomy terms, enabling multi-dimensional classification.

---

## Functional Requirements

### Transaction-Term Linking

#### Junction Table
- Links transactions to taxonomy terms
- Many-to-many relationship
- One transaction can have multiple terms
- One term can classify multiple transactions
- Track when classification was added

---

## User Capabilities

### Transaction Classification
- Assign multiple taxonomy terms to one transaction
- Select terms from different taxonomies
- Remove term assignments
- View all assigned terms
- Auto-suggest terms based on merchant/description

### Transaction Display
- See all assigned taxonomy terms
- Grouped by taxonomy
- Breadcrumb path for hierarchical terms
- Click term to see all transactions with that term

### Filtering & Search
- Filter transactions by any taxonomy term
- Combine filters (AND/OR logic)
- Filter by multiple terms from different taxonomies
- Unclassified transactions filter

### Reporting & Analytics
- Group transactions by taxonomy term
- Sum by term with hierarchy rollup
- Cross-taxonomy reports (e.g., "All Food expenses on Venezia Trip")
- Budget tracking by term (Feature 3.4)

---

## Data Model Requirements

### New Table: `transaction_taxonomy_terms` (Junction)

**Columns**:
```
id                UUID (Primary Key)
transaction_id    UUID NOT NULL (FK to transactions)
taxonomy_term_id  UUID NOT NULL (FK to taxonomy_terms)
created_at        TIMESTAMP NOT NULL
```

**Indexes**:
- Primary key on `id`
- Index on `transaction_id`
- Index on `taxonomy_term_id`
- Unique index on `(transaction_id, taxonomy_term_id)`

**Foreign Keys**:
- `transaction_id` → `transactions.id` ON DELETE CASCADE
- `taxonomy_term_id` → `taxonomy_terms.id` ON DELETE CASCADE

---

## Migration from transaction_tags

### Step 1: Create "Tags" Taxonomy
- For each user, create a "Tags" taxonomy
- is_system = false (custom taxonomy)

### Step 2: Migrate Tags to Terms
- For each unique tag in `transaction_tags`
- Create taxonomy term in user's "Tags" taxonomy
- Map tag name to term name

### Step 3: Link Transactions
- For each transaction_tag record
- Create transaction_taxonomy_terms entry
- Link transaction to corresponding term

### Step 4: Verify
- Verify all tags migrated
- Verify all transaction links preserved
- Verify counts match

### Step 5: Remove Old Table
- After verification, DELETE `transaction_tags` table
- No keeping for reference (per user decision)

---

## API Requirements

### Modified Endpoints

**1. Create/Update Transaction**
```
POST/PATCH /api/v1/transactions/{id}
```
- Add `taxonomy_term_ids` array field
- Accept list of term UUIDs
- Validate all terms exist
- Validate user owns terms or terms are from user's taxonomies

**2. Get/List Transactions**
```
GET /api/v1/transactions
```
- Include taxonomy terms in response
- Group by taxonomy
- Show full path for hierarchical terms
- Filter by `taxonomy_term_id` (single or multiple)

### New Endpoints

**3. Add Term to Transaction**
```
POST /api/v1/transactions/{id}/terms
```
- Add one or more terms
- Prevent duplicates

**4. Remove Term from Transaction**
```
DELETE /api/v1/transactions/{id}/terms/{term_id}
```
- Remove term assignment

**5. Bulk Classify**
```
POST /api/v1/transactions/bulk-classify
```
- Assign terms to multiple transactions
- Useful for retroactive classification

---

## Validation Rules

- Taxonomy term must exist
- Term must belong to user's taxonomy
- Cannot assign same term twice to one transaction
- Can assign terms from different taxonomies
- Can assign multiple terms from same taxonomy

---

## Business Rules

### Classification Flexibility
- No limit on number of terms per transaction
- Can mix terms from different taxonomies
- Can have no terms (unclassified)

### Hierarchy Handling
- Classify with most specific term
- Parent terms can be inferred for reporting
- Example: Classify as "Italian" → implies "Restaurants" → implies "Food"

### Term Deletion
- If term deleted, remove from transactions
- Warn user about transaction count before deleting term

---

## Reporting Features

### Hierarchy Rollup
```
Food: $500
├── Groceries: $300
└── Restaurants: $200
    ├── Fast Food: $50
    └── Italian: $150
```

### Cross-Taxonomy Analysis
```
Venezia 2024 Trip + Food Category = $850
Venezia 2024 Trip + Transportation = $300
```

---

## Testing Requirements

- Test assigning single term
- Test assigning multiple terms from different taxonomies
- Test preventing duplicate term assignment
- Test removing term assignment
- Test filtering by term
- Test hierarchy rollup in reports
- Test migration from transaction_tags
- Test deleting term removes from transactions

---

## Success Criteria

1. ✅ `transaction_taxonomy_terms` table created
2. ✅ Many-to-many relationship works
3. ✅ Transactions can have multiple terms
4. ✅ Filtering by terms works
5. ✅ Hierarchy rollup works
6. ✅ Migration from tags complete
7. ✅ `transaction_tags` table deleted
8. ✅ All tests passing

---

## Notes

- This REPLACES the tag system completely
- Much more powerful than simple tags
- Enables multi-dimensional analysis
- Foundation for budgeting (Feature 3.4)
- After migration, delete transaction_tags table entirely
