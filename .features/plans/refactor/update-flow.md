# Database Entry Update Flow Refactoring Plan

## 1. Executive Summary

This plan addresses the refactoring of the Emerald Finance Platform backend to comply with the database entry update flow guidelines defined in `.claude/best-practices/database-entry-update-flow.md`.

**Current State:** The codebase has **significant inconsistencies** in how update operations are implemented across different services. After thorough analysis, the audit revealed multiple deviations from the prescribed architecture:

1. **Inconsistent service method signatures** - Some accept Pydantic schemas, others accept individual parameters
2. **Mixed transaction commit patterns** - Some services commit explicitly, others delegate to callers
3. **Inconsistent use of `model_dump(exclude_unset=True)`** - Only 2 of 6 services use this pattern
4. **Repository receives both patterns** - Sometimes called with kwargs, sometimes without
5. **Audit logging detail varies** - Some track old/new values, others log minimal metadata

**Primary Objectives:**
1. Standardize all update service methods to accept Pydantic schemas
2. Unify transaction commit responsibility (services commit, routes don't)
3. Implement `model_dump(exclude_unset=True)` consistently for partial updates
4. Simplify repository `update()` to only flush/refresh (no kwargs)
5. Standardize audit logging to capture old/new values for compliance

**Expected Outcomes:**
- Consistent, predictable update behavior across all entities
- Clear separation of concerns between layers
- Proper partial update support for PATCH semantics
- GDPR-compliant audit trails with change tracking
- Reduced code duplication and maintenance burden

---

## 2. Technical Architecture

### 2.1 System Design Overview

The target architecture follows the guidelines exactly:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API ROUTE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  Pydantic update schema (all fields optional)                    │
│  DOES:      - Extract HTTP context (IP, user agent, request ID)             │
│             - Call service method with schema object                        │
│             - Convert response to Pydantic schema                           │
│  RETURNS:   Pydantic response schema (JSON)                                 │
│  DOES NOT:  - Unpack schema fields individually                             │
│             - Manage transaction commits                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: Pydantic schema + entity ID + context
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  Pydantic schema + entity_id + current_user + HTTP context       │
│  DOES:      - Fetch existing entity from repository                         │
│             - Permission checks (ownership, admin, etc.)                    │
│             - Business validation (uniqueness, constraints)                 │
│             - Capture old values for audit                                  │
│             - Apply changes via model_dump(exclude_unset=True)              │
│             - Handle side effects (balance updates, cascades)               │
│             - Call repository.update()                                      │
│             - Capture new values for audit                                  │
│             - Log audit event                                               │
│             - Commit transaction                                            │
│  RETURNS:   SQLAlchemy model instance                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ passes: SQLAlchemy model instance
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REPOSITORY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  RECEIVES:  SQLAlchemy model instance (already modified)                    │
│  DOES:      - session.flush()                                               │
│             - session.refresh(instance)                                     │
│  RETURNS:   SQLAlchemy model instance (with updated timestamps)             │
│  DOES NOT:  - Accept **kwargs for attribute updates                         │
│             - Modify model attributes                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Current State Analysis

| Service | Schema-based | Uses exclude_unset | Commits | Audit Detail |
|---------|-------------|-------------------|---------|--------------|
| UserService.update_user_profile | Yes (UserUpdate) | Yes | No | Full |
| AccountService.update_account | No (individual params) | No | No | Full |
| CardService.update_card | Yes (CardUpdate) | Yes | No | Minimal |
| TransactionService.update_transaction | No (individual params + UNSET sentinel) | No | No | Full |
| AccountTypeService.update_account_type | Yes (AccountTypeUpdate) | No | **Yes** | Minimal |
| FinancialInstitutionService.update_institution | Yes (FinancialInstitutionUpdate) | No | **Yes** | Minimal |
| AccountService.update_share | No (single param) | N/A | No | Minimal |

### 2.3 Target State

| Service | Schema-based | Uses exclude_unset | Commits | Audit Detail |
|---------|-------------|-------------------|---------|--------------|
| All services | Yes | Yes | Yes | Full (old/new values) |

### 2.4 File Structure

```
src/
├── api/routes/
│   ├── accounts.py         # PATCH /accounts/{id} - remove schema unpacking
│   ├── transactions.py     # PUT /transactions/{id} - remove schema unpacking
│   └── account_shares.py   # PATCH /shares/{id} - already minimal
├── services/
│   ├── account_service.py  # Refactor to schema-based, add commit
│   ├── transaction_service.py # Refactor to schema-based, add commit
│   ├── card_service.py     # Add commit, enhance audit
│   ├── user_service.py     # Add commit (already compliant otherwise)
│   ├── account_type_service.py # Use exclude_unset, enhance audit
│   └── financial_institution_service.py # Use exclude_unset, enhance audit
├── repositories/
│   └── base.py             # Simplify update() to remove **kwargs
└── schemas/
    └── account_share.py    # Already has AccountShareUpdate
```

---

## 3. Implementation Specification

### 3.1 Component: BaseRepository.update() Simplification

**Files Involved:**
- `src/repositories/base.py`

**Purpose:** Simplify the update method to only handle persistence (flush/refresh), not attribute modification. Services should modify model attributes before calling update().

**Current Implementation:**
```python
async def update(
    self,
    instance: ModelType,
    **kwargs: Any,
) -> ModelType:
    for key, value in kwargs.items():
        setattr(instance, key, value)
    await self.session.flush()
    await self.session.refresh(instance)
    return instance
```

**Target Implementation:**
```python
async def update(self, instance: ModelType) -> ModelType:
    """Persist changes to an already-modified model instance."""
    await self.session.flush()
    await self.session.refresh(instance)
    return instance
```

**Implementation Requirements:**

1. **Core Logic:**
   - Remove `**kwargs` parameter
   - Remove `setattr` loop
   - Keep flush/refresh behavior

2. **Breaking Change:**
   - All services calling `repo.update(instance, **kwargs)` must be updated
   - Services must modify attributes before calling update()

3. **Edge Cases & Error Handling:**
   - [ ] Handle case: instance not in session (session.add needed?)
   - [ ] Validate: instance is not None
   - [ ] Error: flush failure (let exception propagate)

**Acceptance Criteria:**
- [ ] update() method no longer accepts **kwargs
- [ ] All service calls updated to not pass kwargs
- [ ] All tests pass

**Implementation Notes:**
- This aligns with the creation flow pattern where `add()` receives a fully-constructed instance
- Makes the repository layer truly "persistence only"

---

### 3.2 Component: AccountService.update_account() Refactoring

**Files Involved:**
- `src/services/account_service.py`
- `src/api/routes/accounts.py`
- `src/schemas/account.py`

**Purpose:** Refactor from individual parameters to schema-based pattern with proper partial update support.

**Current Implementation (Problematic):**
```python
async def update_account(
    self,
    account_id: uuid.UUID,
    current_user: User,
    account_name: str | None = None,       # Individual params
    account_type_id: uuid.UUID | None = None,
    financial_institution_id: uuid.UUID | None = None,
    color_hex: str | None = None,
    icon_url: HttpUrl | None = None,
    notes: str | None = None,
    # ... context params
) -> Account:
    # Manual field-by-field checks
    if account_name is not None and account_name != account.account_name:
        # validation...
        account.account_name = account_name
    # ... repeated for each field
```

**Target Implementation:**
```python
async def update_account(
    self,
    account_id: uuid.UUID,
    data: AccountUpdate,                    # Pydantic schema
    current_user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> Account:
    # 1. Fetch existing
    account = await self.account_repo.get_by_id(account_id)
    if not account:
        raise NotFoundError("Account")

    # 2. Permission check
    if account.user_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Not authorized to update this account")

    # 3. Get only provided fields
    update_dict = data.model_dump(exclude_unset=True)

    if not update_dict:
        return account  # Nothing to update

    # 4. Business validations (only for changing fields)
    if "account_name" in update_dict and update_dict["account_name"] != account.account_name:
        if await self.account_repo.exists_by_name(current_user.id, update_dict["account_name"]):
            raise AlreadyExistsError("Account with this name already exists")

    if "account_type_id" in update_dict:
        if not await self.account_type_repo.exists(update_dict["account_type_id"]):
            raise NotFoundError("AccountType")

    if "financial_institution_id" in update_dict:
        if update_dict["financial_institution_id"] is not None:
            if not await self.institution_repo.exists(update_dict["financial_institution_id"]):
                raise NotFoundError("FinancialInstitution")

    # 5. Capture old values for audit
    old_values = {
        "account_name": account.account_name,
        "account_type_id": str(account.account_type_id) if account.account_type_id else None,
        "financial_institution_id": str(account.financial_institution_id) if account.financial_institution_id else None,
        "color_hex": account.color_hex,
        "icon_url": str(account.icon_url) if account.icon_url else None,
        "notes": account.notes,
    }

    # 6. Apply changes to model
    for key, value in update_dict.items():
        setattr(account, key, value)
    account.updated_by = current_user.id

    # 7. Persist
    account = await self.account_repo.update(account)

    # 8. Capture new values for audit
    new_values = {
        "account_name": account.account_name,
        "account_type_id": str(account.account_type_id) if account.account_type_id else None,
        "financial_institution_id": str(account.financial_institution_id) if account.financial_institution_id else None,
        "color_hex": account.color_hex,
        "icon_url": str(account.icon_url) if account.icon_url else None,
        "notes": account.notes,
    }

    # 9. Audit with old/new values
    await self.audit_service.log_data_change(
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="account",
        entity_id=account_id,
        old_values=old_values,
        new_values=new_values,
        extra_metadata={"changed_fields": list(update_dict.keys())},
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    # 10. Commit
    await self.session.commit()
    return account
```

**Route Update (accounts.py):**
```python
# Current (problematic - unpacks fields):
account = await account_service.update_account(
    account_id=account_id,
    current_user=current_user,
    account_name=update_data.account_name,
    account_type_id=update_data.account_type_id,
    # ... each field unpacked
)

# Target (passes schema):
account = await account_service.update_account(
    account_id=account_id,
    data=update_data,  # Pass schema directly
    current_user=current_user,
    ip_address=request.client.host if request.client else None,
)
```

**Acceptance Criteria:**
- [ ] Service accepts AccountUpdate schema
- [ ] Route passes schema without unpacking
- [ ] Uses model_dump(exclude_unset=True)
- [ ] Captures old/new values for audit
- [ ] Commits transaction
- [ ] All tests pass

---

### 3.3 Component: TransactionService.update_transaction() Refactoring

**Files Involved:**
- `src/services/transaction_service.py`
- `src/api/routes/transactions.py`
- `src/schemas/transaction.py`

**Purpose:** Refactor from individual parameters with UNSET sentinel to schema-based pattern.

**Current Implementation Issues:**
1. Uses individual parameters instead of schema
2. Uses custom `UNSET` sentinel for nullable fields
3. Route unpacks schema fields individually
4. Complex manual tracking of changes

**Implementation Requirements:**

1. **Core Logic:**
   - Accept `TransactionUpdate` schema
   - Use `model_dump(exclude_unset=True)` for partial updates
   - For nullable fields (like `card_id`), check if key is in update_dict
   - Handle balance delta calculation before applying changes

2. **Handling nullable fields (card_id):**
   ```python
   update_dict = data.model_dump(exclude_unset=True)

   # If card_id was explicitly provided (even as null)
   if "card_id" in update_dict:
       new_card_id = update_dict["card_id"]
       if new_card_id is not None:
           # Validate card exists
           card = await self.card_repo.get_by_id(new_card_id)
           if not card:
               raise NotFoundError("Card")
       # Can be None to clear the card association
       transaction.card_id = new_card_id
   ```

3. **Balance delta handling:**
   ```python
   old_amount = transaction.amount
   if "amount" in update_dict:
       new_amount = update_dict["amount"]
       balance_delta = new_amount - old_amount
   else:
       balance_delta = Decimal(0)

   # Apply all updates
   for key, value in update_dict.items():
       setattr(transaction, key, value)

   # Apply balance change if needed
   if balance_delta != Decimal(0):
       account = await self.account_repo.get_for_update(transaction.account_id)
       account.current_balance += balance_delta
       await self.account_repo.update(account)
   ```

**Acceptance Criteria:**
- [ ] Service accepts TransactionUpdate schema
- [ ] Route passes schema without unpacking
- [ ] Properly handles nullable card_id
- [ ] Correctly calculates balance delta
- [ ] Captures old/new values for audit
- [ ] Commits transaction
- [ ] All tests pass

---

### 3.4 Component: CardService.update_card() Enhancement

**Files Involved:**
- `src/services/card_service.py`

**Current Status:** Partially compliant - already uses schema and exclude_unset.

**Required Changes:**

1. **Add transaction commit:**
   ```python
   # After audit logging
   await self.session.commit()
   return CardResponse.model_validate(card)
   ```

2. **Enhance audit logging (capture old/new values):**
   ```python
   # Before changes
   old_values = {
       "name": card.name,
       "last_four_digits": card.last_four_digits,
       "card_network": card.card_network,
       # ... all auditable fields
   }

   # After changes
   new_values = {
       "name": card.name,
       "last_four_digits": card.last_four_digits,
       # ... all auditable fields
   }

   await self.audit_service.log_data_change(
       user_id=current_user.id,
       action=AuditAction.UPDATE,
       entity_type="card",
       entity_id=card_id,
       old_values=old_values,
       new_values=new_values,
       extra_metadata={"changed_fields": list(update_data.keys())},
       # ... context
   )
   ```

**Acceptance Criteria:**
- [ ] Commits transaction
- [ ] Logs old/new values in audit
- [ ] All tests pass

---

### 3.5 Component: UserService.update_user_profile() Enhancement

**Files Involved:**
- `src/services/user_service.py`

**Current Status:** Mostly compliant - uses schema and exclude_unset.

**Required Changes:**

1. **Add transaction commit:**
   ```python
   # After audit logging
   await self.session.commit()
   return user
   ```

**Acceptance Criteria:**
- [ ] Commits transaction
- [ ] All tests pass

---

### 3.6 Component: AccountTypeService.update_account_type() Refactoring

**Files Involved:**
- `src/services/account_type_service.py`

**Current Issues:**
1. Manually tracks changes instead of using exclude_unset
2. Already commits (good)
3. Minimal audit logging

**Required Changes:**

1. **Use model_dump(exclude_unset=True):**
   ```python
   update_dict = data.model_dump(exclude_unset=True)
   if not update_dict:
       return AccountTypeResponse.model_validate(account_type)

   # Apply all changes
   for key, value in update_dict.items():
       setattr(account_type, key, value)
   ```

2. **Enhance audit logging:**
   ```python
   old_values = {
       "name": account_type.name,
       "description": account_type.description,
       "icon_url": str(account_type.icon_url) if account_type.icon_url else None,
       "sort_order": account_type.sort_order,
   }

   # After update
   new_values = {
       "name": account_type.name,
       "description": account_type.description,
       "icon_url": str(account_type.icon_url) if account_type.icon_url else None,
       "sort_order": account_type.sort_order,
   }

   await self.audit_service.log_data_change(
       # ... full audit with old/new values
   )
   ```

**Acceptance Criteria:**
- [ ] Uses model_dump(exclude_unset=True)
- [ ] Logs old/new values in audit
- [ ] All tests pass

---

### 3.7 Component: FinancialInstitutionService.update_institution() Refactoring

**Files Involved:**
- `src/services/financial_institution_service.py`

**Current Issues:**
1. Manually tracks changes instead of using exclude_unset
2. Already commits (good)
3. Minimal audit logging

**Required Changes:** Same pattern as AccountTypeService:

1. Use `model_dump(exclude_unset=True)`
2. Simplify field-by-field checks to only validate changing fields
3. Enhance audit logging with old/new values

**Acceptance Criteria:**
- [ ] Uses model_dump(exclude_unset=True)
- [ ] Only validates fields that are changing
- [ ] Logs old/new values in audit
- [ ] All tests pass

---

### 3.8 Component: AccountService.update_share() Enhancement

**Files Involved:**
- `src/services/account_service.py`

**Current Status:** Simple single-field update.

**Required Changes:**

1. **Add transaction commit:**
   ```python
   await self.session.commit()
   return share
   ```

2. **Enhance audit (old/new permission level):**
   ```python
   old_values = {"permission_level": str(share.permission_level)}
   # After update
   new_values = {"permission_level": str(share.permission_level)}

   await self.audit_service.log_data_change(
       user_id=current_user.id,
       action=AuditAction.UPDATE,
       entity_type="account_share",
       entity_id=share_id,
       old_values=old_values,
       new_values=new_values,
       # ... context
   )
   ```

**Acceptance Criteria:**
- [ ] Commits transaction
- [ ] Logs old/new permission level
- [ ] All tests pass

---

## 4. Implementation Roadmap

### 4.1 Phase Breakdown

#### Phase 1: Repository Simplification (Size: S, Priority: P0)

**Goal:** Simplify BaseRepository.update() to match guidelines - persistence only.

**Scope:**
- ✅ Include: Remove **kwargs from update()
- ✅ Include: Update all service calls that pass kwargs
- ❌ Exclude: Service refactoring (Phase 2)

**Detailed Tasks:**

1. [ ] Update `src/repositories/base.py`:
   - Remove `**kwargs` parameter from update()
   - Remove setattr loop
   - Update docstring

2. [ ] Identify services calling update() with kwargs:
   - `CardService.update_card()` - passes `**update_data`
   - Any others using this pattern

3. [ ] Update service calls:
   - Apply setattr before calling repo.update()
   - Call `repo.update(instance)` without kwargs

4. [ ] Run tests:
   - `uv run pytest tests/ -v`

**Validation Criteria:**
- [ ] update() no longer accepts kwargs
- [ ] All tests pass
- [ ] No behavioral changes

**Dependencies:** None

---

#### Phase 2: Transaction Commit Standardization (Size: S, Priority: P0)

**Goal:** Ensure all services commit their transactions.

**Scope:**
- ✅ Include: Add commits to services without explicit commit
- ✅ Include: Remove any duplicate route-level commits
- ❌ Exclude: Audit logging changes (Phase 4)

**Detailed Tasks:**

1. [ ] Add `await self.session.commit()` to:
   - `UserService.update_user_profile()` - after audit log
   - `CardService.update_card()` - after audit log
   - `AccountService.update_account()` - after audit log
   - `AccountService.update_share()` - after audit log
   - `TransactionService.update_transaction()` - after audit log

2. [ ] Verify existing commits in:
   - `AccountTypeService.update_account_type()` - already commits
   - `FinancialInstitutionService.update_institution()` - already commits

3. [ ] Check routes for duplicate commits and remove if found

4. [ ] Run tests

**Validation Criteria:**
- [ ] All update services commit
- [ ] No duplicate commits
- [ ] All tests pass

**Dependencies:** None (can run parallel with Phase 1)

---

#### Phase 3: Service Signature Refactoring (Size: M, Priority: P1)

**Goal:** Standardize all update methods to accept Pydantic schemas.

**Scope:**
- ✅ Include: Refactor AccountService.update_account()
- ✅ Include: Refactor TransactionService.update_transaction()
- ✅ Include: Update corresponding routes
- ❌ Exclude: Services already using schemas (CardService, UserService)

**Detailed Tasks:**

1. [ ] Refactor `AccountService.update_account()`:
   - Change signature to accept `AccountUpdate` schema
   - Implement `model_dump(exclude_unset=True)` pattern
   - Move validation to only check changing fields

2. [ ] Update `src/api/routes/accounts.py`:
   - Remove schema field unpacking
   - Pass `AccountUpdate` directly to service

3. [ ] Refactor `TransactionService.update_transaction()`:
   - Change signature to accept `TransactionUpdate` schema
   - Remove UNSET sentinel (use exclude_unset instead)
   - Handle nullable card_id via key presence in update_dict

4. [ ] Update `src/api/routes/transactions.py`:
   - Remove schema field unpacking
   - Pass `TransactionUpdate` directly to service

5. [ ] Run tests

**Validation Criteria:**
- [ ] Services accept schemas
- [ ] Routes don't unpack schemas
- [ ] Uses model_dump(exclude_unset=True)
- [ ] All tests pass

**Dependencies:** Phase 1 (repo simplified)

---

#### Phase 4: Audit Logging Standardization (Size: S, Priority: P2)

**Goal:** Ensure all update operations log old/new values for compliance.

**Scope:**
- ✅ Include: Enhance CardService audit
- ✅ Include: Enhance AccountTypeService audit
- ✅ Include: Enhance FinancialInstitutionService audit
- ✅ Include: Enhance AccountService.update_share() audit

**Detailed Tasks:**

1. [ ] Verify `AuditService.log_data_change()` method exists or create it:
   - Should accept old_values, new_values, extra_metadata
   - Log to audit_logs table

2. [ ] Update each service to capture old values before changes

3. [ ] Update each service to capture new values after changes

4. [ ] Update each audit call to use log_data_change() with old/new values

5. [ ] Run tests

**Validation Criteria:**
- [ ] All update operations log old/new values
- [ ] Audit logs include changed_fields metadata
- [ ] All tests pass

**Dependencies:** Phase 2 (commits standardized)

---

#### Phase 5: Use exclude_unset Consistently (Size: S, Priority: P2)

**Goal:** Use model_dump(exclude_unset=True) in all schema-based services.

**Scope:**
- ✅ Include: AccountTypeService - add exclude_unset
- ✅ Include: FinancialInstitutionService - add exclude_unset
- ❌ Exclude: Services already using it (CardService, UserService)

**Detailed Tasks:**

1. [ ] Update `AccountTypeService.update_account_type()`:
   - Replace manual field checks with exclude_unset pattern
   - Simplify code

2. [ ] Update `FinancialInstitutionService.update_institution()`:
   - Replace manual field checks with exclude_unset pattern
   - Keep uniqueness validations only for changing fields

3. [ ] Run tests

**Validation Criteria:**
- [ ] All services use exclude_unset
- [ ] Code is simpler
- [ ] All tests pass

**Dependencies:** Phase 3 (signatures refactored)

---

### 4.2 Implementation Sequence

```
Phase 1 (P0, ~1 hour)     Phase 2 (P0, ~1 hour)
Repository Simplify       Transaction Commits
       │                        │
       └──────────┬─────────────┘
                  │
                  ▼
        Phase 3 (P1, ~3 hours)
      Service Signature Refactor
                  │
                  ▼
        Phase 4 (P2, ~2 hours)
      Audit Logging Standardize
                  │
                  ▼
        Phase 5 (P2, ~1 hour)
      Use exclude_unset Consistently
```

**Rationale for ordering:**
- Phases 1 & 2 are independent and can run in parallel
- Phase 3 depends on Phase 1 (repo interface changed)
- Phase 4 depends on Phase 2 (commits in place)
- Phase 5 depends on Phase 3 (consistent schema usage)

**Quick Wins:**
- Phase 2 (commit standardization) provides immediate consistency
- Phase 1 (repo simplification) enables cleaner service code

---

## 5. Simplicity & Design Validation

### Simplicity Checklist

- [x] Is this the SIMPLEST solution that solves the problem?
  - **Yes:** We're standardizing on existing patterns, not inventing new ones

- [x] Have we avoided premature optimization?
  - **Yes:** No performance changes, only consistency fixes

- [x] Does this align with existing patterns in the codebase?
  - **Yes:** CardService and UserService already use the target pattern

- [x] Can we deliver value in smaller increments?
  - **Yes:** Each phase provides standalone value

- [x] Are we solving the actual problem vs. a perceived problem?
  - **Yes:** Inconsistency is real and causes maintenance burden

### Alternatives Considered

**Alternative 1: Keep individual parameters for complex services**
- Why not chosen: Creates inconsistency, harder to maintain, error-prone in routes

**Alternative 2: Use route middleware for transaction commits**
- Why not chosen: Services should control their own transaction boundaries for proper error handling

**Alternative 3: Create a generic update decorator**
- Why not chosen: Over-engineering; explicit code is clearer for this use case

**Rationale:** The proposed approach uses proven patterns already in the codebase (CardService, UserService) and applies them consistently.

---

## 6. Summary of Changes

### Files Requiring Changes

| File | Phase | Change Type | Description |
|------|-------|-------------|-------------|
| `src/repositories/base.py` | 1 | Simplify | Remove **kwargs from update() |
| `src/services/card_service.py` | 1,2,4 | Minor | Remove kwargs usage, add commit, enhance audit |
| `src/services/user_service.py` | 2 | Minor | Add commit |
| `src/services/account_service.py` | 2,3,4 | Major | Refactor signature, add commit, enhance audit |
| `src/services/transaction_service.py` | 2,3,4 | Major | Refactor signature, remove UNSET, add commit, enhance audit |
| `src/services/account_type_service.py` | 4,5 | Moderate | Enhance audit, use exclude_unset |
| `src/services/financial_institution_service.py` | 4,5 | Moderate | Enhance audit, use exclude_unset |
| `src/api/routes/accounts.py` | 3 | Moderate | Pass schema directly, don't unpack |
| `src/api/routes/transactions.py` | 3 | Moderate | Pass schema directly, don't unpack |

### Testing Requirements

For each phase:
- [ ] Unit tests for modified service methods
- [ ] Integration tests for affected API endpoints
- [ ] Verify audit logs contain old/new values
- [ ] Verify partial updates work correctly (only provided fields updated)
- [ ] Verify null values can clear optional fields where supported

---

## 7. References & Related Documents

- `.claude/best-practices/database-entry-update-flow.md` - Update flow guidelines (source document)
- `.claude/best-practices/database-entry-creation-flow.md` - Creation flow guidelines (reference pattern)
- `.features/plans/refactor/creation-flow.md` - Creation flow refactoring plan (completed)
- [FastAPI Body Updates Documentation](https://fastapi.tiangolo.com/tutorial/body-updates/)
- [Pydantic Partial Update Models Guide](https://www.getorchestra.io/guides/pydantic-partial-update-models-in-fastapi-a-tutorial)
