# Feature 4.2: Remove Transaction Tags Table

**Phase**: 4 - Cleanup
**Priority**: Medium
**Dependencies**: Feature 3.3 (Transaction Classification with Taxonomies)
**Estimated Effort**: 1 week

---

## Overview

Remove the deprecated `transaction_tags` table after all tags have been migrated to the taxonomy system. This completes the transition from simple tags to flexible taxonomies.

---

## Business Context

**Problem**: `transaction_tags` table is obsolete after migration to taxonomies in Feature 3.3. Keeping it creates confusion and maintenance burden.

**Solution**: After verifying 100% migration success, permanently remove the transaction_tags table.

---

## Functional Requirements

### Pre-Removal Verification

**Must verify before removal**:
1. All transaction tags migrated to taxonomy terms
2. All transaction-tag links migrated to transaction_taxonomy_terms
3. Tag counts match between old and new systems
4. No active usage of transaction_tags table
5. All APIs updated to use taxonomies

### Removal Steps

1. **Final Verification**
   - Run migration verification script
   - Check for any remaining tags not migrated
   - Verify transaction counts match

2. **Create Rollback Script**
   - Save final snapshot of transaction_tags data
   - Create script to restore if needed
   - Store in secure backup location

3. **Remove Table**
   - DROP transaction_tags table
   - Remove from ORM models
   - Remove from API schemas

4. **Code Cleanup**
   - Remove all references to transaction_tags
   - Remove tag-related endpoints (replaced by taxonomy endpoints)
   - Update documentation

---

## Migration Verification

### Verification Queries

```sql
-- Count tags per user in old system
SELECT user_id, COUNT(*)
FROM transaction_tags
GROUP BY user_id;

-- Count terms in "Tags" taxonomy per user in new system
SELECT t.user_id, COUNT(*)
FROM taxonomy_terms tt
JOIN taxonomies t ON tt.taxonomy_id = t.id
WHERE t.name = 'Tags'
GROUP BY t.user_id;

-- Verify counts match
```

### Rollback Preparation

Before removal:
1. Export transaction_tags to JSON/CSV
2. Save schema definition
3. Document restoration procedure
4. Store in backup system (S3, etc.)

---

## API Changes

### Removed Endpoints

**DELETE these endpoints**:
```
GET    /api/v1/transactions/{id}/tags
POST   /api/v1/transactions/{id}/tags
DELETE /api/v1/transactions/{id}/tags/{tag}
GET    /api/v1/tags (tag autocomplete)
```

**Replaced by** (already exist from Feature 3.3):
```
GET    /api/v1/transactions/{id}/terms
POST   /api/v1/transactions/{id}/terms
DELETE /api/v1/transactions/{id}/terms/{term_id}
GET    /api/v1/taxonomies/{id}/terms
```

---

## User Communication

### Notification

**Inform users**:
- "Transaction tags have been migrated to the new taxonomy system"
- "Your existing tags are now available in the 'Tags' taxonomy"
- "You can now organize tags into hierarchies and create multiple classification schemes"
- "No action required - all your data has been preserved"

### Documentation Updates

- Update user guide to reference taxonomies instead of tags
- Update API documentation
- Update tutorials and examples

---

## Testing Requirements

### Pre-Removal Verification Tests
- Test all tags migrated successfully
- Test tag counts match
- Test no active tag API usage
- Test all transaction links preserved

### Post-Removal Tests
- Test transaction_tags table doesn't exist
- Test no code references transaction_tags
- Test all taxonomy functionality works
- Test no broken API endpoints

---

## Rollback Plan

If issues discovered after removal:

1. **Stop and Assess**
   - Identify specific issue
   - Determine if rollback necessary

2. **Restore Table**
   - Restore transaction_tags schema
   - Import data from backup
   - Restore code references

3. **Investigate**
   - Determine what was missed in migration
   - Fix migration script
   - Re-verify

4. **Retry Removal**
   - Only after fixes verified
   - With enhanced verification

---

## Success Criteria

1. ✅ 100% of tags migrated to taxonomies (verified)
2. ✅ Rollback script created and tested
3. ✅ `transaction_tags` table dropped
4. ✅ All code references removed
5. ✅ Old tag API endpoints removed
6. ✅ Documentation updated
7. ✅ Users notified of migration
8. ✅ All tests passing

---

## Timeline

**Week 1**: Verification and preparation
- Run verification scripts
- Create rollback plan
- Test in staging environment

**Week 2**: Removal
- Remove table in production
- Remove code references
- Update documentation
- Monitor for issues

---

## Notes

- **Critical**: Must verify 100% migration before removal
- Keep rollback script for at least 90 days post-removal
- Monitor error logs for any references to old tag system
- This is a one-way change - cannot easily reverse
- Coordinate with frontend team for simultaneous updates
