# Feature 3.2: Hierarchical Taxonomy Terms

**Phase**: 3 - Enhancement
**Priority**: High
**Dependencies**: Feature 3.1 (Taxonomy System Foundation)
**Estimated Effort**: 2 weeks

---

## Overview

Create hierarchical terms (categories/values) within each taxonomy, supporting unlimited parent-child depth for organizing transactions. Example: Food → Restaurants → Italian or Home → Utilities → Electricity.

---

## Business Context

**Problem**: Need structured, hierarchical categorization within each taxonomy for better organization and reporting.

**Solution**: Taxonomy terms with self-referencing parent-child relationships, enabling tree structures of any depth.

---

## Functional Requirements

### Taxonomy Term Data

#### Core Fields
- **Taxonomy ID** (required): Which taxonomy this term belongs to
- **Parent Term ID** (optional): Parent term for hierarchy (NULL = root level)
- **Name** (required): Term name (e.g., "Groceries", "Venezia 2024")
- **Description** (optional): Term explanation
- **Icon** (optional): Visual identifier
- **Sort Order** (required): Display order within parent

#### Lifecycle
- Soft delete support
- Audit fields (created_by, updated_by)

---

## Hierarchy Examples

### Categories Taxonomy
```
Food (parent_id: NULL)
├── Groceries (parent_id: Food.id)
│   ├── Organic (parent_id: Groceries.id)
│   └── Regular (parent_id: Groceries.id)
└── Restaurants (parent_id: Food.id)
    ├── Fast Food (parent_id: Restaurants.id)
    └── Fine Dining (parent_id: Restaurants.id)

Transportation (parent_id: NULL)
├── Gas (parent_id: Transportation.id)
└── Public Transit (parent_id: Transportation.id)
```

### Trips Taxonomy
```
Venezia 2024 (parent_id: NULL)
Portugal 2025 (parent_id: NULL)
Tokyo 2026 (parent_id: NULL)
```

---

## User Capabilities

### Term Management
- Create root-level terms
- Create child terms under any term
- Move terms (change parent)
- Reorder terms within same level
- Edit term details
- Delete terms (soft delete)

### Hierarchy Navigation
- View term tree structure
- Expand/collapse branches
- Drag-and-drop to reorganize
- Breadcrumb navigation (Food > Restaurants > Italian)

### Term Selection
- Select any term for transaction classification
- Auto-select parent terms if child selected (optional)
- Search across all terms
- Filter by taxonomy

---

## Data Model Requirements

### New Table: `taxonomy_terms`

**Columns**:
```
id              UUID (Primary Key)
taxonomy_id     UUID NOT NULL (FK to taxonomies)
parent_term_id  UUID NULL (FK to taxonomy_terms, self-reference)
name            VARCHAR(100) NOT NULL
description     VARCHAR(500) NULL
icon            VARCHAR(50) NULL
sort_order      INTEGER NOT NULL DEFAULT 0
created_at      TIMESTAMP NOT NULL
updated_at      TIMESTAMP NOT NULL
deleted_at      TIMESTAMP NULL
created_by      UUID NULL
updated_by      UUID NULL
```

**Indexes**:
- Primary key on `id`
- Index on `taxonomy_id`
- Index on `parent_term_id`
- Index on `name`
- Index on `deleted_at`
- Unique partial index on `(taxonomy_id, name)` WHERE `deleted_at IS NULL`

**Constraints**:
- CHECK: `id != parent_term_id` (no self-reference)
- Foreign key cycle prevention (enforced in business logic)

**Foreign Keys**:
- `taxonomy_id` → `taxonomies.id` ON DELETE CASCADE
- `parent_term_id` → `taxonomy_terms.id` ON DELETE CASCADE

---

## API Requirements

### Endpoints

**1. List Terms**
```
GET /api/v1/taxonomies/{taxonomy_id}/terms
```
- List all terms in taxonomy
- Return as tree structure or flat list
- Include parent/children relationships
- Include transaction counts

**2. Get Term**
```
GET /api/v1/terms/{id}
```
- Get term with full path (breadcrumb)
- Include children
- Include transaction count

**3. Create Term**
```
POST /api/v1/taxonomies/{taxonomy_id}/terms
```
- Create new term
- Optionally specify parent_term_id
- Validate name uniqueness within taxonomy

**4. Update Term**
```
PATCH /api/v1/terms/{id}
```
- Update name, description, icon, sort_order
- Allow changing parent (move in tree)
- Validate no circular references

**5. Delete Term**
```
DELETE /api/v1/terms/{id}
```
- Soft delete
- Cascade delete children (optional) or move children to parent
- Warn if has transactions

**6. Bulk Create (Pre-population)**
```
POST /api/v1/taxonomies/{taxonomy_id}/terms/bulk
```
- Create multiple terms at once
- Used for pre-population during onboarding
- Accepts tree structure

---

## Pre-populated Category Terms

If user chooses pre-populated categories during onboarding:

### Root Categories
1. **Food & Dining**
   - Groceries
   - Restaurants
   - Takeout & Delivery
   - Coffee Shops

2. **Transportation**
   - Gas & Fuel
   - Public Transit
   - Parking
   - Ride Sharing
   - Maintenance

3. **Housing**
   - Rent / Mortgage
   - Home Insurance
   - Maintenance & Repairs

4. **Utilities**
   - Electricity
   - Water
   - Gas
   - Internet
   - Phone

5. **Healthcare**
   - Medical
   - Dental
   - Pharmacy
   - Insurance

6. **Entertainment**
   - Movies & Shows
   - Sports & Recreation
   - Hobbies
   - Subscriptions

7. **Shopping**
   - Clothing
   - Electronics
   - Home Goods
   - Personal Care

8. **Income**
   - Salary
   - Freelance
   - Investments
   - Other Income

9. **Savings & Investments**
   - Emergency Fund
   - Retirement
   - Investments

10. **Other**
    - Miscellaneous

---

## Validation Rules

### Name
- Required
- 1-100 characters
- Unique within taxonomy (case-insensitive)

### Parent Term
- Must belong to same taxonomy
- Cannot be self
- Cannot create circular reference

### Hierarchy Depth
- No hard limit
- Practical recommendation: 3-4 levels max

---

## Business Rules

### Term Uniqueness
- Term names unique per taxonomy
- Same name can exist in different taxonomies
- Same name can exist at different levels in tree

### Circular Reference Prevention
- Cannot set parent to self
- Cannot set parent to own descendant
- Validate entire chain on parent change

### Deletion Rules
- Soft delete term
- Options for children:
  - Cascade delete children
  - Move children to deleted term's parent
- Cannot delete if transactions reference it (or warn user)

---

## Testing Requirements

- Test creating root and child terms
- Test hierarchy navigation
- Test moving terms (change parent)
- Test circular reference prevention
- Test name uniqueness per taxonomy
- Test pre-population bulk create
- Test deleting terms with children

---

## Success Criteria

1. ✅ `taxonomy_terms` table created
2. ✅ Self-referencing hierarchy works
3. ✅ Circular reference prevention works
4. ✅ Users can create nested terms
5. ✅ Pre-population creates default terms
6. ✅ Term tree displayed correctly
7. ✅ All tests passing

---

## Notes

- This feature does NOT classify transactions yet (Feature 3.3)
- Focus on term management and hierarchy
- Pre-populated terms provide good starting point
- Users can customize pre-populated terms
