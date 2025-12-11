# Instruction: Soft Delete Consistency Refactoring

## Summary

Refactor the codebase to establish a **single, consistent soft delete pattern** using only the `deleted_at` timestamp field. Remove the redundant `is_active` boolean field entirely.

---

## Requirements

### 1. Soft Delete Models

The following models **must** support soft delete via a `deleted_at` field:

- `Account`
- `Card`
- `FinancialInstitution`
- `Transaction`
- `User`

**Soft delete behavior:**
- `deleted_at = NULL` → Entity is active
- `deleted_at = <timestamp>` → Entity is soft-deleted

### 2. Hard Delete Models

All other models in the codebase **must not** have soft delete. They should:
- Use standard hard deletes (row removal)
- Have no `deleted_at` field
- Have no `is_active` field

### 3. Remove `is_active` Field

The `is_active` field is redundant and **must be removed** from all models where it exists. The `deleted_at` field is the single source of truth for entity status.

---

## Scope of Changes

Review and update **all layers** of the application:

| Layer | Required Changes |
|-------|------------------|
| **Models** | Add/remove `deleted_at`; remove all `is_active` fields |
| **Repositories** | Update queries to filter by `deleted_at`; remove `is_active` logic |
| **Services** | Update business logic to use new pattern |
| **Endpoints** | Update request/response schemas if affected |
| **Tests** | Update fixtures, assertions, and test cases |
| **Migrations** | Create migrations for schema changes |

---

## Acceptance Criteria

- [ ] Only the five specified models have a `deleted_at` field
- [ ] No model in the codebase has an `is_active` field
- [ ] Default queries for soft-delete models exclude records where `deleted_at IS NOT NULL`
- [ ] All tests pass with the new pattern
- [ ] Database schema aligns with model definitions

---

## Notes

- Review **every** model, not just the ones listed — ensure no model violates these rules
- Ensure consistent implementation across all soft-delete models
- Encapsulate soft-delete filtering logic in the repository layer
