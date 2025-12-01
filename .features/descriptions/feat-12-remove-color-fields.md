# Feature 4.1: Remove Color Fields from Accounts

**Phase**: 4 - Cleanup
**Priority**: Low
**Dependencies**: None
**Estimated Effort**: 2 days

---

## Overview

Remove the `color_hex` field from the accounts table as it's not a best practice to store UI preferences in the domain data model. Color management should be handled in user preferences or theme settings.

---

## Business Context

**Problem**: Storing `color_hex` in accounts table mixes UI concerns with business data, violates separation of concerns, and makes data model unnecessarily complex.

**Solution**: Remove `color_hex` field entirely. UI colors should be determined by frontend themes, user preferences, or account type associations.

---

## Functional Requirements

### Remove Field
- Drop `color_hex` column from accounts table
- No replacement field needed
- No data migration needed

### UI Color Alternatives
Colors can be determined by:
1. Account type (each type has default color scheme)
2. User theme preferences (stored in user settings, not accounts)
3. Frontend defaults based on account position/order
4. Institution branding colors (from financial_institutions table)

---

## User Impact

**Before**: Users could set custom color for each account
**After**: Account colors determined by type, theme, or institution

**Migration**:
- Inform users that custom account colors will be reset
- Colors will be based on account type going forward
- No user action required

---

## Data Model Changes

### Modify Table: `accounts`

**Remove Column**:
```
color_hex   VARCHAR(7)
```

---

## API Changes

### Modified Endpoints

**All account endpoints**: Remove `color_hex` from request/response schemas

No functional changes - purely removing an unused field.

---

## Testing Requirements

- Verify column dropped successfully
- Verify no references to color_hex in code
- Verify API still works without field
- Verify frontend displays accounts correctly

---

## Success Criteria

1. ✅ `color_hex` column removed from accounts table
2. ✅ All references removed from codebase
3. ✅ API updated (no breaking changes to critical functionality)
4. ✅ All tests passing
5. ✅ Frontend updated to use alternative coloring

---

## Notes

- Simple, low-risk change
- Improves data model cleanliness
- Color management better handled in UI layer
- Can be done independently of other features
