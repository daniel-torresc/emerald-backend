# Feature 2.4: Link Transactions to Cards

**Phase**: 2 - Integration
**Priority**: High
**Dependencies**: Feature 2.3 (Cards Management)

---

## Overview

Enable transactions to reference which card was used, allowing users to track spending by credit card or debit card. This feature extends the basic card-transaction linking established in Feature 2.3 with enhanced filtering, and reporting capabilities.

---

## Functional Requirements

### Transaction-Card Relationship

The `card_id` foreign key on transactions (added in Feature 2.3) enables:
- Users select which card was used when creating/editing transactions
- Users can see which card was used for historical transactions
- Transactions can exist without a card (e.g., cash transactions)

---

## User Capabilities

### Transaction Creation/Editing
- Select card from dropdown when creating transactions
- Filter available cards by type (credit/debit)
- See recently used cards first
- Option to not select a card (NULL)
- Auto-suggest primary card based on account

### Transaction Display
- See card name with transaction
- See card last 4 digits if available
- See card network icon (Visa, Mastercard, etc.)
- Click card to see all transactions for that card

---

## API Requirements

### Modified Endpoints

**1. Create Transaction** (Updated)
```
POST /api/v1/transactions
```
- Add optional `card_id` field
- Validate card exists and belongs to user (via account ownership)
- Return card details in response

**2. Update Transaction** (Updated)
```
PATCH /api/v1/transactions/{id}
```
- Allow updating `card_id`
- Allow setting to NULL (remove card association)
- Validate card belongs to user via account ownership

**3. Get Transaction** (Updated)
```
GET /api/v1/transactions/{id}
```
- Include card details in response (name, last_four_digits, card_network, card_type)
- Return NULL if no card linked

**4. List Transactions** (Updated)
```
GET /api/v1/transactions
```
- Include card details for each transaction
- Add filtering by `card_id`
- Support filtering by card_type (show only credit card or debit card transactions)

---

## Validation Rules

- Card must exist and not be soft-deleted
- Card must belong to current user (via account ownership check)
- Card can be NULL (not all transactions use cards)
- Warning if linking to a soft-deleted card

---

## Response Schema Updates

### Transaction Response (with Card)
```json
{
  "id": "uuid",
  "amount": 150.00,
  "description": "Restaurant dinner",
  "card": {
    "id": "uuid",
    "name": "Chase Sapphire Reserve",
    "card_type": "credit_card",
    "last_four_digits": "4242",
    "card_network": "Visa"
  },
  ...
}
```

---

## Testing Requirements

### Transaction-Card Integration Tests
- Test creating transaction with card_id
- Test creating transaction without card_id (NULL)
- Test updating card_id on existing transaction
- Test setting card_id to NULL (removing card)
- Test card validation (must belong to user via account)
- Test card response included in transaction GET

### Filtering Tests
- Test filtering transactions by card_id
- Test filtering transactions by card_type
- Test pagination with card filters

### Edge Cases
- Test transaction behavior when card is soft-deleted (card_id becomes NULL)
- Test user cannot link transaction to another user's card

---

## Success Criteria

1. Transactions can be created/updated with optional card_id
2. Transaction responses include card details when linked
3. Transactions can be filtered by card_id and card_type
4. All authorization checks pass (card belongs to user via account)
5. All tests passing with 80%+ coverage

---

## Notes

- This feature builds on the card_id column added in Feature 2.3 (Cards Management)
- Existing transactions will have card_id = NULL
- Users can retroactively add cards to historical transactions
