# Entity Schemas Refactoring Plan

## Executive Summary

This plan addresses the refactoring of Pydantic schemas across the Emerald Finance Platform to comply with the entity schema patterns defined in `.claude/best-practices/entity-schemas-guide.md`. The audit reveals that while the current codebase follows many best practices (Base schemas, Update schemas with optional fields, Response schemas with `from_attributes`), several gaps exist that need to be addressed.

The primary objectives are:
1. Add missing `Embedded` schemas for entities that are referenced in other responses
2. Add `json_schema_extra` examples to schemas missing them for better API documentation
3. Ensure `model_config = ConfigDict(from_attributes=True)` uses the proper syntax (ConfigDict vs dict)
4. Remove sorting parameters from `FilterParams` schemas (should use common `SortParams`)
5. Update `__init__.py` exports for new schemas

Expected outcomes: Complete compliance with the entity schema guidelines, better API documentation, consistent schema patterns across all entities, and proper separation of concerns for filtering vs sorting.

---

## 1. Audit Summary: Non-Compliant Schemas

### 1.1 Missing Embedded Schemas

The following entities are used as nested references but lack `Embedded` schemas:

| Entity | Referenced In | Current Behavior | Required |
|--------|--------------|------------------|----------|
| `User` | `AccountShareResponse.user` | Uses `UserSummary` (effectively an Embedded) | **OK** (rename to `UserEmbedded` for consistency) |
| `Account` | `CardResponse.account`, `CardListItem.account` | Uses `AccountListItem` (heavy) | **Needs `AccountEmbedded`** |
| `AccountType` | `AccountResponse.account_type`, `AccountListItem.account_type` | Uses `AccountTypeListItem` | **OK** (already minimal) |
| `FinancialInstitution` | `AccountResponse.financial_institution`, `CardResponse.financial_institution` | Uses `FinancialInstitutionResponse` (heavy) or `FinancialInstitutionListItem` | **Needs `FinancialInstitutionEmbedded`** |

### 1.2 Missing `json_schema_extra` Examples

Schemas missing OpenAPI documentation examples:

| Schema File | Schemas Missing Examples |
|-------------|-------------------------|
| `user.py` | `UserBase`, `UserCreate`, `UserUpdate`, `UserPasswordChange`, `UserResponse`, `UserListItem`, `UserFilterParams` |
| `audit.py` | `AuditLogResponse`, `AuditLogFilterParams` |
| `account_share.py` | `AccountShareCreate`, `AccountShareUpdate`, `AccountShareResponse`, `AccountShareListItem`, `UserSummary` |
| `common.py` | `SortParams`, `SearchResult`, `PaginationParams`, `PaginationMeta`, `PaginatedResponse`, `ErrorDetail`, `ErrorResponse` |

### 1.3 Incorrect `model_config` Syntax

Some schemas use dictionary syntax instead of `ConfigDict`:

| File | Schemas | Current | Should Be |
|------|---------|---------|-----------|
| `user.py` | `UserResponse`, `UserListItem` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |
| `account.py` | `AccountResponse`, `AccountListItem` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |
| `transaction.py` | `TransactionResponse`, `TransactionListItem` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |
| `financial_institution.py` | `FinancialInstitutionResponse`, `FinancialInstitutionListItem` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |
| `account_type.py` | `AccountTypeResponse`, `AccountTypeListItem` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |
| `audit.py` | `AuditLogResponse` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |
| `account_share.py` | `UserSummary`, `AccountShareResponse`, `AccountShareListItem` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |
| `card.py` | `CardEmbedded` | `model_config = {"from_attributes": True}` | `model_config = ConfigDict(from_attributes=True)` |

### 1.4 FilterParams Containing Sorting Parameters

Per guidelines, `FilterParams` should contain entity-specific filters ONLY. Sorting should be handled by the common `SortParams` schema.

| Schema | Violating Fields | Fix |
|--------|-----------------|-----|
| `TransactionFilterParams` | `sort_by`, `sort_order` | Remove - use `SortParams` in routes |
| `TransactionSearchParams` | `sort_by`, `sort_order`, `skip`, `limit` | **DEPRECATED** - remove entirely |

### 1.5 Redundant/Deprecated Schemas

| Schema | Issue | Action |
|--------|-------|--------|
| `TransactionSearchParams` | Deprecated, duplicates `TransactionFilterParams` + `PaginationParams` | Remove |

---

## 2. Technical Architecture

### 2.1 Schema Hierarchy (Target State)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCHEMA HIERARCHY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EntityBase                    ← Shared fields across all schemas           │
│    ├── EntityCreate            ← POST /entities (input)                     │
│    ├── EntityUpdate            ← PATCH /entities/{id} (input)               │
│    ├── EntityResponse          ← Single entity response                     │
│    ├── EntityEmbedded          ← Nested in other responses (NEW)            │
│    └── EntityListItem          ← GET /entities (paginated list)             │
│                                                                             │
│  EntityFilterParams            ← GET /entities?filter (NO sort params)      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Files to Modify

```
src/schemas/
├── __init__.py              # Add new Embedded schema exports
├── user.py                  # Add examples, fix model_config syntax
├── account.py               # Add AccountEmbedded, fix model_config
├── account_share.py         # Rename UserSummary → UserEmbedded, add examples
├── account_type.py          # Add examples, fix model_config
├── audit.py                 # Add examples, fix model_config
├── card.py                  # Add examples, fix model_config (CardEmbedded exists)
├── common.py                # Add examples where helpful
├── financial_institution.py # Add FinancialInstitutionEmbedded, fix model_config
└── transaction.py           # Remove deprecated schema, fix FilterParams, fix model_config
```

---

## 3. Implementation Specification

### 3.1 Component: Account Schemas

**Files Involved**:
- `src/schemas/account.py`

**Purpose**: Add `AccountEmbedded` schema for use in Card responses

**Implementation Requirements**:

1. **Add AccountEmbedded Schema**:
   ```python
   class AccountEmbedded(BaseModel):
       """
       Minimal account representation for embedding in other entities.

       Used in Card responses to show the linked account without
       requiring a separate API call.
       """
       id: uuid.UUID = Field(description="Account UUID")
       account_name: str = Field(description="Account display name")
       currency: str = Field(description="ISO 4217 currency code")

       model_config = ConfigDict(from_attributes=True)
   ```

2. **Fix model_config Syntax**:
   - Change `model_config = {"from_attributes": True}` to `model_config = ConfigDict(from_attributes=True)`
   - Add `ConfigDict` import from pydantic

3. **Add json_schema_extra Examples**:
   - Add examples to `AccountCreate`, `AccountUpdate`, `AccountResponse`

**Acceptance Criteria**:
- [ ] `AccountEmbedded` schema exists with id, account_name, currency fields
- [ ] All response schemas use `ConfigDict(from_attributes=True)`
- [ ] Schemas have `json_schema_extra` examples

---

### 3.2 Component: Financial Institution Schemas

**Files Involved**:
- `src/schemas/financial_institution.py`

**Purpose**: Add `FinancialInstitutionEmbedded` for use in Account/Card responses

**Implementation Requirements**:

1. **Add FinancialInstitutionEmbedded Schema**:
   ```python
   class FinancialInstitutionEmbedded(BaseModel):
       """
       Minimal financial institution representation for embedding.

       Used in Account and Card responses to show the institution
       without full details.
       """
       id: uuid.UUID = Field(description="Institution UUID")
       name: str = Field(description="Official institution name")
       short_name: str = Field(description="Display name")
       logo_url: str | None = Field(default=None, description="Logo URL")

       model_config = ConfigDict(from_attributes=True)
   ```

2. **Fix model_config Syntax**:
   - Update `FinancialInstitutionResponse` and `FinancialInstitutionListItem`

3. **Add json_schema_extra Examples**:
   - Add to `FinancialInstitutionCreate`, `FinancialInstitutionUpdate`, `FinancialInstitutionResponse`

**Acceptance Criteria**:
- [ ] `FinancialInstitutionEmbedded` schema exists
- [ ] All response schemas use `ConfigDict(from_attributes=True)`
- [ ] Schemas have `json_schema_extra` examples

---

### 3.3 Component: User Schemas

**Files Involved**:
- `src/schemas/user.py`

**Purpose**: Add `UserEmbedded` schema, fix model_config, add examples

**Implementation Requirements**:

1. **Add UserEmbedded Schema**:
   ```python
   class UserEmbedded(BaseModel):
       """
       Minimal user representation for embedding in other entities.

       Used in AccountShare and other responses to show user info
       without sensitive details.
       """
       id: uuid.UUID = Field(description="User UUID")
       username: str = Field(description="Username")
       email: str = Field(description="Email address")
       full_name: str | None = Field(default=None, description="Full name")

       model_config = ConfigDict(from_attributes=True)
   ```

2. **Fix model_config Syntax**:
   - Update `UserResponse` and `UserListItem`

3. **Add json_schema_extra Examples**:
   - Add to `UserCreate`, `UserUpdate`, `UserPasswordChange`, `UserResponse`

**Acceptance Criteria**:
- [ ] `UserEmbedded` schema exists
- [ ] All response schemas use `ConfigDict(from_attributes=True)`
- [ ] Schemas have `json_schema_extra` examples

---

### 3.4 Component: Account Share Schemas

**Files Involved**:
- `src/schemas/account_share.py`

**Purpose**: Rename `UserSummary` to `UserEmbedded` (or reference from user.py), fix model_config, add examples

**Implementation Requirements**:

1. **Update User Reference**:
   - Either import `UserEmbedded` from `schemas.user` OR
   - Keep `UserSummary` as-is (it's semantically correct for this context)
   - Decision: Keep `UserSummary` - it's specific to the share context and matches the entity schema guide's principle of purpose-specific schemas

2. **Fix model_config Syntax**:
   - Update `UserSummary`, `AccountShareResponse`, `AccountShareListItem`

3. **Add json_schema_extra Examples**:
   - Add to `AccountShareCreate`, `AccountShareUpdate`, `AccountShareResponse`

**Acceptance Criteria**:
- [ ] All response schemas use `ConfigDict(from_attributes=True)`
- [ ] Schemas have `json_schema_extra` examples

---

### 3.5 Component: Transaction Schemas

**Files Involved**:
- `src/schemas/transaction.py`

**Purpose**: Remove deprecated schema, fix FilterParams, fix model_config

**Implementation Requirements**:

1. **Remove Deprecated Schema**:
   - Delete `TransactionSearchParams` class entirely (marked DEPRECATED)

2. **Fix TransactionFilterParams**:
   - Remove `sort_by` and `sort_order` fields
   - These should be passed via common `SortParams` in routes

3. **Fix model_config Syntax**:
   - Update `TransactionResponse` and `TransactionListItem`

4. **Add json_schema_extra Examples**:
   - Add to `TransactionCreate`, `TransactionUpdate`, `TransactionResponse`

**Acceptance Criteria**:
- [ ] `TransactionSearchParams` is removed
- [ ] `TransactionFilterParams` has no sort_by/sort_order fields
- [ ] All response schemas use `ConfigDict(from_attributes=True)`
- [ ] Schemas have `json_schema_extra` examples

---

### 3.6 Component: Card Schemas

**Files Involved**:
- `src/schemas/card.py`

**Purpose**: Update to use new Embedded schemas, fix model_config

**Implementation Requirements**:

1. **Update Relationship Types**:
   - Change `account: AccountListItem` to `account: AccountEmbedded` in `CardResponse` and `CardListItem`
   - Change `financial_institution: FinancialInstitutionListItem | None` to `financial_institution: FinancialInstitutionEmbedded | None`

2. **Fix model_config Syntax**:
   - Update `CardEmbedded` (others already use ConfigDict)

3. **Update Imports**:
   - Import `AccountEmbedded` from `schemas.account`
   - Import `FinancialInstitutionEmbedded` from `schemas.financial_institution`

**Acceptance Criteria**:
- [ ] `CardResponse` and `CardListItem` use `AccountEmbedded` and `FinancialInstitutionEmbedded`
- [ ] All response schemas use `ConfigDict(from_attributes=True)`

---

### 3.7 Component: Account Type Schemas

**Files Involved**:
- `src/schemas/account_type.py`

**Purpose**: Fix model_config syntax

**Implementation Requirements**:

1. **Fix model_config Syntax**:
   - Update `AccountTypeResponse` and `AccountTypeListItem`

2. **Add json_schema_extra Examples**:
   - Add to `AccountTypeCreate`, `AccountTypeUpdate`, `AccountTypeResponse`

**Acceptance Criteria**:
- [ ] All response schemas use `ConfigDict(from_attributes=True)`
- [ ] Schemas have `json_schema_extra` examples

---

### 3.8 Component: Audit Schemas

**Files Involved**:
- `src/schemas/audit.py`

**Purpose**: Fix model_config syntax, add examples

**Implementation Requirements**:

1. **Fix model_config Syntax**:
   - Update `AuditLogResponse`

2. **Add json_schema_extra Examples**:
   - Add to `AuditLogResponse`, `AuditLogFilterParams`

**Acceptance Criteria**:
- [ ] `AuditLogResponse` uses `ConfigDict(from_attributes=True)`
- [ ] Schemas have `json_schema_extra` examples

---

### 3.9 Component: Common Schemas

**Files Involved**:
- `src/schemas/common.py`

**Purpose**: Add examples where helpful for API documentation

**Implementation Requirements**:

1. **Add json_schema_extra Examples**:
   - Add to `PaginationParams`, `PaginationMeta`, `SortParams`
   - These are visible in Swagger/ReDoc

**Acceptance Criteria**:
- [ ] Key common schemas have `json_schema_extra` examples

---

### 3.10 Component: Schema Exports

**Files Involved**:
- `src/schemas/__init__.py`

**Purpose**: Export new Embedded schemas

**Implementation Requirements**:

1. **Add New Exports**:
   ```python
   from schemas.account import AccountEmbedded
   from schemas.financial_institution import FinancialInstitutionEmbedded
   from schemas.user import UserEmbedded

   __all__ = [
       # ... existing exports ...
       # Embedded schemas
       "AccountEmbedded",
       "FinancialInstitutionEmbedded",
       "UserEmbedded",
   ]
   ```

2. **Remove Deprecated Exports**:
   - Remove `TransactionSearchParams` if it was exported

**Acceptance Criteria**:
- [ ] New Embedded schemas are exported
- [ ] Deprecated schemas are not exported

---

## 4. Implementation Roadmap

### Phase 1: Schema Fixes (Size: M, Priority: P0)

**Goal**: Fix all existing schemas to comply with guidelines

**Scope**:
- Fix `model_config` syntax across all files
- Remove sorting from `TransactionFilterParams`
- Remove deprecated `TransactionSearchParams`

**Detailed Tasks**:
1. [ ] Update `src/schemas/user.py`:
   - Add `from pydantic import ConfigDict`
   - Change `model_config = {"from_attributes": True}` to `model_config = ConfigDict(from_attributes=True)` in `UserResponse`, `UserListItem`

2. [ ] Update `src/schemas/account.py`:
   - Add `ConfigDict` import
   - Fix model_config in `AccountResponse`, `AccountListItem`

3. [ ] Update `src/schemas/transaction.py`:
   - Add `ConfigDict` import
   - Fix model_config in `TransactionResponse`, `TransactionListItem`
   - Remove `sort_by` and `sort_order` from `TransactionFilterParams`
   - Delete `TransactionSearchParams` class

4. [ ] Update `src/schemas/financial_institution.py`:
   - Add `ConfigDict` import
   - Fix model_config in `FinancialInstitutionResponse`, `FinancialInstitutionListItem`

5. [ ] Update `src/schemas/account_type.py`:
   - Add `ConfigDict` import
   - Fix model_config in `AccountTypeResponse`, `AccountTypeListItem`

6. [ ] Update `src/schemas/audit.py`:
   - Add `ConfigDict` import
   - Fix model_config in `AuditLogResponse`

7. [ ] Update `src/schemas/account_share.py`:
   - Add `ConfigDict` import
   - Fix model_config in `UserSummary`, `AccountShareResponse`, `AccountShareListItem`

8. [ ] Update `src/schemas/card.py`:
   - Fix model_config in `CardEmbedded`

**Validation Criteria**:
- [ ] All response/embedded schemas use `ConfigDict(from_attributes=True)`
- [ ] `TransactionFilterParams` has no sorting fields
- [ ] `TransactionSearchParams` is removed
- [ ] All tests pass

---

### Phase 2: Add Embedded Schemas (Size: S, Priority: P0)

**Goal**: Add missing Embedded schemas for proper relationship serialization

**Scope**:
- Add `AccountEmbedded`
- Add `FinancialInstitutionEmbedded`
- Add `UserEmbedded`
- Update Card schemas to use new Embedded types

**Detailed Tasks**:
1. [ ] Add `AccountEmbedded` to `src/schemas/account.py`:
   ```python
   class AccountEmbedded(BaseModel):
       id: uuid.UUID = Field(description="Account UUID")
       account_name: str = Field(description="Account display name")
       currency: str = Field(description="ISO 4217 currency code")

       model_config = ConfigDict(from_attributes=True)
   ```

2. [ ] Add `FinancialInstitutionEmbedded` to `src/schemas/financial_institution.py`:
   ```python
   class FinancialInstitutionEmbedded(BaseModel):
       id: uuid.UUID = Field(description="Institution UUID")
       name: str = Field(description="Official institution name")
       short_name: str = Field(description="Display name")
       logo_url: str | None = Field(default=None, description="Logo URL")

       model_config = ConfigDict(from_attributes=True)
   ```

3. [ ] Add `UserEmbedded` to `src/schemas/user.py`:
   ```python
   class UserEmbedded(BaseModel):
       id: uuid.UUID = Field(description="User UUID")
       username: str = Field(description="Username")
       email: str = Field(description="Email address")
       full_name: str | None = Field(default=None, description="Full name")

       model_config = ConfigDict(from_attributes=True)
   ```

4. [ ] Update `src/schemas/card.py`:
   - Import `AccountEmbedded` and `FinancialInstitutionEmbedded`
   - Update `CardResponse.account` type to `AccountEmbedded`
   - Update `CardResponse.financial_institution` type to `FinancialInstitutionEmbedded | None`
   - Update `CardListItem.account` type to `AccountEmbedded`
   - Update `CardListItem.financial_institution` type to `FinancialInstitutionEmbedded | None`

5. [ ] Update `src/schemas/__init__.py`:
   - Add exports for `AccountEmbedded`, `FinancialInstitutionEmbedded`, `UserEmbedded`

**Validation Criteria**:
- [ ] All new Embedded schemas created
- [ ] Card schemas use new Embedded types
- [ ] All tests pass
- [ ] API responses still serialize correctly

---

### Phase 3: Add Documentation Examples (Size: S, Priority: P1)

**Goal**: Add `json_schema_extra` examples to all schemas for better API documentation

**Scope**:
- Add examples to Create, Update, Response schemas
- Add examples to FilterParams schemas
- Add examples to common schemas

**Detailed Tasks**:
1. [ ] Add examples to `src/schemas/user.py`:
   - `UserCreate`, `UserUpdate`, `UserPasswordChange`, `UserResponse`, `UserListItem`

2. [ ] Add examples to `src/schemas/account_share.py`:
   - `AccountShareCreate`, `AccountShareUpdate`, `AccountShareResponse`

3. [ ] Add examples to `src/schemas/audit.py`:
   - `AuditLogResponse`, `AuditLogFilterParams`

4. [ ] Add examples to `src/schemas/common.py`:
   - `PaginationParams`, `SortParams`

5. [ ] Verify existing examples in:
   - `account.py` (has examples)
   - `transaction.py` (has examples)
   - `card.py` (has examples)
   - `financial_institution.py` (has examples)
   - `account_type.py` (has examples)

**Validation Criteria**:
- [ ] All input schemas have `json_schema_extra` examples
- [ ] All response schemas have `json_schema_extra` examples
- [ ] Swagger/ReDoc shows examples correctly

---

## 5. Implementation Sequence

```
Phase 1 (P0)
  ↓ Fix model_config, remove deprecated schemas
Phase 2 (P0)
  ↓ Add Embedded schemas, update references
Phase 3 (P1)
  Add documentation examples
```

**Rationale**:
- Phase 1 first because it fixes breaking issues and removes deprecated code
- Phase 2 depends on Phase 1 for consistent ConfigDict usage
- Phase 3 can run after Phase 2 as it's purely additive documentation

---

## 6. Simplicity & Design Validation

**Simplicity Checklist**:
- [x] Is this the SIMPLEST solution? Yes - following established patterns from guidelines
- [x] Avoided premature optimization? Yes - only adding schemas that are actually needed
- [x] Aligns with existing patterns? Yes - mirrors Card/Transaction schema patterns
- [x] Can we deliver value in smaller increments? Yes - 3 phases, each independently valuable

**Alternatives Considered**:
- **Alternative 1**: Create a generic `EmbeddedMixin` - Rejected because Pydantic doesn't support multiple inheritance well and each embedded schema has different fields
- **Alternative 2**: Use `exclude` on Response schemas - Rejected because explicit Embedded schemas are clearer and more maintainable
- **Alternative 3**: Keep using ListItem for embedding - Rejected because ListItem schemas are heavier than needed for embedded use

**Rationale**: The proposed approach follows the entity schema guidelines exactly, creating purpose-specific schemas that are minimal and focused.

---

## 7. Testing Requirements

### Unit Tests
- [ ] Test `AccountEmbedded.model_validate()` with SQLAlchemy Account model
- [ ] Test `FinancialInstitutionEmbedded.model_validate()` with SQLAlchemy model
- [ ] Test `UserEmbedded.model_validate()` with SQLAlchemy User model
- [ ] Test `TransactionFilterParams` no longer accepts `sort_by`/`sort_order`

### Integration Tests
- [ ] Verify Card API responses serialize with new Embedded types
- [ ] Verify Account API responses work unchanged
- [ ] Verify Transaction API responses work unchanged

### Validation
- [ ] Run `uv run ruff format .` - passes
- [ ] Run `uv run ruff check --fix .` - passes
- [ ] Run `uv run mypy src/` - passes
- [ ] Run `uv run pytest tests/` - passes

---

## 8. References

- [Entity Schema Patterns Guide](/.claude/best-practices/entity-schemas-guide.md)
- [Pydantic v2 ConfigDict](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict)
- [FastAPI Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)
