# Feature 4.3: Remove Transaction Type Field

**Phase**: 4 - Cleanup
**Priority**: Medium
**Dependencies**: Feature 3.3 (Transaction Classification with Taxonomies)
**Estimated Effort**: 1 week

---

## Overview

Remove the `transaction_type` enum field (income/expense/transfer) from transactions table. Transaction type can be inferred from amount sign, taxonomy classification, or other metadata.

---

## Business Context

**Problem**: `transaction_type` enum is redundant:
- Income/expense can be inferred from amount sign (positive = income, negative = expense)
- Taxonomy system provides richer classification
- Transfer type can be identified by linked transactions or taxonomy
- Adds unnecessary complexity

**Solution**: Remove `transaction_type` field and infer type from data.

---

## Functional Requirements

### Type Inference Rules

**After removal, determine type by**:

1. **Amount Sign**
   - Positive amount → Income
   - Negative amount → Expense
   - Zero amount → Neutral/Adjustment

2. **Taxonomy Classification** (optional)
   - Create optional "Transaction Types" taxonomy
   - Terms: Income, Expense, Transfer
   - Users can explicitly classify if needed

3. **Transfer Identification**
   - Transactions with linked transfer pairs
   - Taxonomy term "Transfer"
   - Notes or description containing "transfer"

---

## Type Inference Logic

### Simple Inference (Amount-Based)
```
getTransactionType(transaction):
  if transaction.amount > 0:
    return "income"
  elif transaction.amount < 0:
    return "expense"
  else:
    return "neutral"
```

### Advanced Inference (Taxonomy-Based)
```
getTransactionType(transaction):
  # Check for explicit type taxonomy term
  type_term = transaction.taxonomy_terms
    .filter(taxonomy.name == "Transaction Types")
    .first()

  if type_term:
    return type_term.name  # "Income", "Expense", "Transfer"

  # Fallback to amount sign
  return inferFromAmount(transaction)
```

---

## Data Model Changes

### Modify Table: `transactions`

**Remove Column**:
```
transaction_type   ENUM(income, expense, transfer)
```

**Remove Enum**:
```
DROP TYPE TransactionType
```

---

## Migration Requirements

### Pre-Removal Verification

**Verify**:
1. All transactions have appropriate amount signs
2. Income transactions: amount > 0
3. Expense transactions: amount < 0
4. Transfer transactions: documented or linked

### Data Validation

```sql
-- Check for inconsistencies
SELECT id, amount, transaction_type
FROM transactions
WHERE
  (transaction_type = 'income' AND amount <= 0) OR
  (transaction_type = 'expense' AND amount >= 0);
```

### Optional: Create Type Taxonomy

For users who want explicit type classification:
1. Create "Transaction Types" taxonomy (system or user)
2. Create terms: Income, Expense, Transfer
3. Optionally migrate existing transaction_type values to taxonomy terms

---

## API Changes

### Modified Endpoints

**Request Changes**:
- Remove `transaction_type` field from create/update requests
- Infer type from `amount` sign

**Response Changes**:
- Remove `transaction_type` from responses, OR
- Add computed `type` field (derived from amount/taxonomy)

**Example Response**:
```json
{
  "id": "...",
  "amount": -50.00,
  "computed_type": "expense",  // Derived from amount < 0
  "taxonomy_terms": [
    {
      "taxonomy": "Categories",
      "term": "Food > Restaurants"
    }
  ]
}
```

---

## User Impact

### For API Clients

**Breaking Changes**:
- Cannot send `transaction_type` in create/update
- May receive `computed_type` instead of `transaction_type`

**Migration Guide**:
1. Remove `transaction_type` from request bodies
2. Use amount sign to determine type
3. Use taxonomy for explicit classification if needed

### For Users

**No visible changes**:
- Transactions still displayed as income/expense
- Filtering by type still works (based on amount sign)
- Can explicitly classify using "Transaction Types" taxonomy if desired

---

## Reporting Changes

### Type-Based Reports

**Before**: Filter by `transaction_type` enum
**After**: Filter by computed type

```
Income Transactions: WHERE amount > 0
Expense Transactions: WHERE amount < 0
Transfers: WHERE taxonomy_terms includes "Transfer"
```

### Dashboard Widgets
- Income vs Expense chart: Based on amount sign
- Monthly income: SUM(amount WHERE amount > 0)
- Monthly expenses: SUM(amount WHERE amount < 0)

---

## Validation Rules

### Amount Sign Validation

**Enforce consistency**:
- If user classifies with "Income" taxonomy term → warn if amount < 0
- If user classifies with "Expense" taxonomy term → warn if amount > 0
- Don't enforce strictly (allow user override)

---

## Testing Requirements

### Data Validation Tests
- Verify all income transactions have amount > 0
- Verify all expense transactions have amount < 0
- Test computed type logic

### API Tests
- Test creating transaction without type field
- Test computed type in responses
- Test filtering by computed type
- Test type inference from amount

### Migration Tests
- Verify enum dropped successfully
- Verify no code references transaction_type
- Test backward compatibility workarounds

---

## Backward Compatibility

### Gradual Migration

**Option 1: Immediate Removal**
- Remove field completely
- Update all clients simultaneously

**Option 2: Deprecation Period**
- Keep field but ignore it
- Return computed type
- Warn clients about deprecation
- Remove after transition period

---

## Success Criteria

1. ✅ `transaction_type` column removed from transactions
2. ✅ `TransactionType` enum dropped from database
3. ✅ Type inference logic implemented
4. ✅ Computed type works correctly
5. ✅ API updated
6. ✅ Reports use computed type
7. ✅ All tests passing
8. ✅ Documentation updated

---

## Optional Enhancement

Create system "Transaction Types" taxonomy:
- Provides explicit type classification
- Users can override amount-based inference
- Supports custom types beyond income/expense/transfer
- Example: Refund, Adjustment, Fee Reversal

---

## Notes

- Simplifies data model
- Relies on amount sign convention (negative = expense)
- Taxonomy system provides flexibility for explicit typing
- Breaking change for API clients
- Coordinate with frontend for simultaneous deployment
