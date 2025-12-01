# Feature 2.4: Link Transactions to Payment Methods

**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: Feature 2.3 (Payment Methods)
**Estimated Effort**: 1 week

---

## Overview

Enable transactions to reference which payment method was used, allowing users to track spending by credit card, debit card, digital wallet, or other payment instruments.

---

## Business Context

**Problem**: Users cannot track which payment method (card/wallet) was used for transactions, making it impossible to:
- Monitor credit card spending
- Track rewards eligibility
- Analyze spending by payment method
- Reconcile credit card statements

**Solution**: Add optional foreign key from transactions to payment_methods table.

---

## Functional Requirements

### Transaction Changes

Add optional `payment_method_id` field to transactions:
- Links to payment_methods table
- Nullable (not all transactions have payment methods, e.g., cash from wallet)
- Users select payment method when creating/editing transactions
- Users can see which method was used for historical transactions

---

## User Capabilities

### Transaction Creation/Editing
- Select payment method from dropdown
- Filter payment methods by type
- See recently used payment methods first
- Option to not select payment method (NULL)
- Auto-suggest primary payment method

### Transaction Display
- See payment method name/icon with transaction
- See card last 4 digits if applicable
- Click payment method to see all transactions for that method

### Analytics & Reporting
- **Filter by Payment Method**: See all transactions for specific card/wallet
- **Group by Payment Method**: Total spending per payment method
- **Credit Card Tracking**: Monitor spending vs credit limit
- **Reconciliation**: Match transactions to credit card statements
- **Rewards Analysis**: Identify eligible transactions

### Payment Method Insights
- Total spent per payment method
- Transaction count per payment method
- Most used payment methods
- Spending trends by payment method over time

---

## Data Model Requirements

### Modify Table: `transactions`

**Add Column**:
```
payment_method_id   UUID NULL (FK to payment_methods.id)
```

**Add Index**:
- Index on `payment_method_id` (for filtering and joins)

**Add Foreign Key**:
- `payment_method_id` → `payment_methods.id`
- ON DELETE SET NULL (if payment method deleted, transaction remains but loses link)

---

## API Requirements

### Modified Endpoints

**1. Create Transaction** (Updated)
```
POST /api/v1/transactions
```
- Add optional `payment_method_id` field
- Validate payment method exists and belongs to user
- Return payment method details in response

**2. Update Transaction** (Updated)
```
PATCH /api/v1/transactions/{id}
```
- Allow updating `payment_method_id`
- Allow setting to NULL (remove payment method)
- Validate payment method belongs to user

**3. Get Transaction** (Updated)
```
GET /api/v1/transactions/{id}
```
- Include payment method details in response
- Return NULL if no payment method linked

**4. List Transactions** (Updated)
```
GET /api/v1/transactions
```
- Include payment method details for each transaction
- Add filtering by `payment_method_id`
- Add grouping by payment method

### New Analytics Endpoints

**5. Spending by Payment Method**
```
GET /api/v1/analytics/spending-by-payment-method
```
- Group transactions by payment method
- Return totals, counts, averages
- Support date range filtering

---

## Validation Rules

- Payment method must exist
- Payment method must belong to current user
- Payment method can be NULL
- Payment method should be active (warning if using deleted method)

---

## Migration Requirements

### Database Changes
1. Add `payment_method_id UUID NULL` to transactions
2. Add foreign key and index
3. All existing transactions have payment_method_id = NULL

### No Data Migration Needed
- This is additive, no data to migrate
- Users can manually add payment methods to historical transactions if desired

---

## Testing Requirements

- Test creating transaction with payment method
- Test creating transaction without payment method
- Test updating payment method on transaction
- Test filtering transactions by payment method
- Test deleting payment method (transactions set to NULL)
- Test analytics/grouping by payment method

---

## Success Criteria

1. ✅ `payment_method_id` column added to transactions
2. ✅ Foreign key and index created
3. ✅ All existing transactions have payment_method_id = NULL
4. ✅ API endpoints updated
5. ✅ Users can link transactions to payment methods
6. ✅ Analytics show spending by payment method
7. ✅ All tests passing

---

## Notes

- Existing transactions start with no payment method (NULL)
- Users encouraged to track payment methods for credit cards
- Future: Auto-suggest payment method based on merchant
- Future: Import credit card statements and match transactions
