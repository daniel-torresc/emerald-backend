# Feature 3.1: Taxonomy System Foundation

**Phase**: 3 - Enhancement
**Priority**: High
**Dependencies**: None
**Estimated Effort**: 1 week

---

## Overview

Create a flexible categorization system that replaces simple tags with multiple independent taxonomies. Users can create custom classification schemes like "Categories" (Food, Transportation), "Trips" (Venezia 2024, Portugal 2025), "Projects" (Kitchen Renovation), etc.

---

## Business Context

**Problem**: Current tagging system is limited:
- Only one dimension of classification (tags)
- No hierarchical structure
- No organization or grouping
- Difficult to manage many tags
- Cannot separate different classification purposes

**Solution**: Create taxonomies as independent classification schemes that can each contain hierarchical terms. One transaction can be classified by multiple taxonomies simultaneously.

---

## Functional Requirements

### Taxonomy Data

Store the following for each taxonomy:

#### 1. Identification
- **User ID** (required): Owner of the taxonomy
- **Name** (required): Taxonomy name (e.g., "Categories", "Trips", "Projects", "Clients", "Tax Years")
- **Description** (optional): Explanation of taxonomy purpose

#### 2. Visual Identity
- **Icon** (optional): Icon or emoji for UI

#### 3. Classification
- **Is System** (required): System-provided vs user-created
- **Sort Order** (required): Display order in UI

#### 4. Lifecycle
- Soft delete support
- Audit fields (created_by, updated_by)

---

## System vs Custom Taxonomies

### System Taxonomies
- Pre-created for each user
- Cannot be deleted (only hidden/deactivated via soft delete)
- Can be customized by user (rename, change icon)
- Default: "Categories" taxonomy

### Custom Taxonomies
- Created by users
- Can be fully customized
- Can be deleted
- Examples: "Trips", "Projects", "Clients", "Properties"

---

## Default "Categories" Taxonomy

### Onboarding Choice

During user onboarding, ask:
**"Would you like to start with pre-populated categories?"**

Options:
1. **Pre-populated**: Create default category terms (Food, Transportation, Housing, etc.)
2. **Start empty**: Create empty "Categories" taxonomy, let user build from scratch

### Pre-populated Terms (if chosen)
If user chooses pre-populated categories, create these taxonomy terms:
- Food & Dining
- Transportation
- Housing
- Utilities
- Healthcare
- Entertainment
- Shopping
- Income
- Savings & Investments
- Other

(Details on taxonomy terms in Feature 3.2)

---

## User Capabilities

### Taxonomy Management
- View all taxonomies
- Create custom taxonomies
- Edit taxonomy name, description, icon
- Delete custom taxonomies (soft delete)
- Reorder taxonomies

### System Taxonomy
- Customize "Categories" taxonomy name/icon
- Choose to pre-populate or start empty
- Cannot delete "Categories" (only soft delete/hide)

### Organization
- Group transactions by taxonomy
- See all terms within a taxonomy
- View transaction counts per taxonomy

---

## Data Model Requirements

### New Table: `taxonomies`

**Columns**:
```
id            UUID (Primary Key)
user_id       UUID NOT NULL (FK to users)
name          VARCHAR(100) NOT NULL
description   VARCHAR(500) NULL
icon          VARCHAR(50) NULL
is_system     BOOLEAN NOT NULL DEFAULT false
sort_order    INTEGER NOT NULL DEFAULT 0
created_at    TIMESTAMP NOT NULL
updated_at    TIMESTAMP NOT NULL
deleted_at    TIMESTAMP NULL
created_by    UUID NULL
updated_by    UUID NULL
```

**Indexes**:
- Primary key on `id`
- Index on `user_id`
- Index on `name`
- Index on `is_system`
- Index on `deleted_at`
- Unique partial index on `(user_id, name)` WHERE `deleted_at IS NULL`

**Foreign Keys**:
- `user_id` → `users.id` ON DELETE CASCADE

---

## API Requirements

### Endpoints

**1. List Taxonomies**
```
GET /api/v1/taxonomies
```
- List user's taxonomies
- Filter by is_system
- Sort by sort_order
- Include term counts

**2. Get Taxonomy**
```
GET /api/v1/taxonomies/{id}
```
- Get details including terms
- Include transaction count

**3. Create Taxonomy**
```
POST /api/v1/taxonomies
```
- Create custom taxonomy
- Validate name uniqueness
- Set is_system = false automatically

**4. Update Taxonomy**
```
PATCH /api/v1/taxonomies/{id}
```
- Update name, description, icon, sort_order
- Cannot change is_system or user_id

**5. Delete Taxonomy**
```
DELETE /api/v1/taxonomies/{id}
```
- Soft delete
- Cannot delete if has terms with transactions
- Warn user about term/transaction count

**6. Onboarding Taxonomy Setup**
```
POST /api/v1/users/me/onboarding/taxonomy
```
- Create "Categories" taxonomy
- Optionally pre-populate with default terms
- Choice: "pre-populated" or "empty"

---

## Validation Rules

### Name
- Required
- 1-100 characters
- Unique per user (case-insensitive)
- Trimmed of whitespace

### Description
- Optional
- 0-500 characters

### Icon
- Optional
- 0-50 characters

### Sort Order
- Integer
- Default: 0
- Can be negative

---

## Business Rules

### System Taxonomy Rules
- Each user gets one "Categories" system taxonomy
- Created during user registration or onboarding
- Cannot be hard deleted
- Can be soft deleted (hidden)
- Can be renamed/customized

### Custom Taxonomy Rules
- Users can create unlimited custom taxonomies
- Each taxonomy name must be unique per user
- Can be deleted if no terms or transactions

### Onboarding
- New users prompted to choose pre-populated or empty categories
- Choice stored in user preferences/onboarding state
- Can change later by adding terms manually

---

## Migration Requirements

### For New Users
- Create "Categories" taxonomy during registration
- Prompt for pre-population choice during onboarding

### For Existing Users
- Create "Categories" taxonomy for all existing users
- Set is_system = true
- Leave empty (no pre-population for existing users)
- Users will migrate existing tags in Feature 3.3

---

## Testing Requirements

- Test creating custom taxonomies
- Test name uniqueness per user
- Test updating taxonomy
- Test soft deleting taxonomy
- Test system taxonomy cannot be hard deleted
- Test onboarding flow with both choices

---

## Success Criteria

1. ✅ `taxonomies` table created
2. ✅ All users have "Categories" system taxonomy
3. ✅ Users can create custom taxonomies
4. ✅ Name uniqueness enforced
5. ✅ Onboarding flow with pre-population choice
6. ✅ Soft delete works
7. ✅ All tests passing

---

## Notes

- This feature does NOT include taxonomy terms (Feature 3.2)
- This feature does NOT classify transactions (Feature 3.3)
- Focus on taxonomy management foundation
- Pre-population choice is important for user experience
