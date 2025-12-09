# Cards Management - Backend Implementation Summary

**Feature**: Cards Management System
**Date**: 2025-12-09
**Branch**: `feature/cards-management`
**Status**: ✅ Complete and Tested

---

## Implementation Summary

### What Was Built

A complete cards management system allowing users to track their credit and debit cards linked to accounts. The system includes full CRUD operations, account ownership validation, soft delete support, and comprehensive audit logging.

### Changes Made

#### 1. Database Layer
- **New Enum**: `CardType` (credit_card, debit_card) in `src/models/enums.py`
- **New Model**: `Card` in `src/models/card.py` with fields:
  - Required: `account_id`, `card_type`, `name`
  - Optional: `financial_institution_id`, `last_four_digits`, `card_network`, `expiry_month`, `expiry_year`, `credit_limit`, `notes`
  - Mixins: TimestampMixin, SoftDeleteMixin, AuditFieldsMixin
  - Check constraints: expiry_month (1-12), last_four_digits (4 digits), credit_limit (positive)
- **Transaction Enhancement**: Added `card_id` foreign key to `transactions` table (nullable, SET NULL on delete)
- **Migration**: `alembic/versions/ab7237ea9da7_add_cards_table_and_card_id_to_.py`
  - Creates cards table with indexes and constraints
  - Adds card_id column to transactions table

#### 2. Repository Layer
- **New Repository**: `src/repositories/card_repository.py`
  - `get_by_user()` - list all cards for user via account ownership
  - `get_by_id_for_user()` - get single card with ownership check
  - `get_by_account()` - get cards for specific account
  - `count_by_user()` - count user's cards
  - All queries include soft-delete filtering

#### 3. Schema Layer
- **New Schemas**: `src/schemas/card.py`
  - `CardBase` - shared fields
  - `CardCreate` - POST request validation (requires account_id)
  - `CardUpdate` - PATCH request validation (all fields optional)
  - `CardResponse` - GET response with full details
  - `CardListItem` - List response (simplified)
  - Validators: expiry date coupling, year range (2000-2100), 4-digit format
- **Transaction Update**: Added `card_id` field to `TransactionCreate`, `TransactionUpdate`, `TransactionResponse`

#### 4. Service Layer
- **New Service**: `src/services/card_service.py`
  - `create_card()` - validates account ownership, creates card, logs audit event
  - `get_card()` - retrieves single card with ownership check
  - `list_cards()` - lists user's cards with filters (card_type, account_id, pagination)
  - `update_card()` - partial updates with validation
  - `delete_card()` - soft delete with audit logging
  - All operations enforce user ownership via account relationship

#### 5. API Layer
- **New Router**: `src/api/routes/cards.py`
  - `GET /api/v1/cards` - List user's cards (supports filters: card_type, account_id, pagination)
  - `GET /api/v1/cards/{id}` - Get specific card
  - `POST /api/v1/cards` - Create new card (201 Created)
  - `PATCH /api/v1/cards/{id}` - Update card
  - `DELETE /api/v1/cards/{id}` - Soft delete card (204 No Content)
  - All endpoints require active user authentication
- **Dependency**: Added `get_card_service()` factory in `src/api/dependencies.py`
- **Registration**: Cards router registered in `src/main.py` under `/api/v1`

#### 6. Testing
- **Integration Tests**: `tests/integration/test_card_routes.py` (17 tests, all passing)
  - Card creation (success, minimal, unauthorized, not found, validation errors)
  - Card retrieval (success, not found, unauthorized)
  - Card listing (success, filter by type, unauthorized)
  - Card update (success, not found, unauthorized)
  - Card deletion (success, not found, unauthorized, soft delete verification)
- **Test Fixtures**: Added `test_card`, `test_financial_institution_for_cards` in `tests/conftest.py`

### Key Features

✅ **Account Ownership**: Cards are owned through account relationship (no direct user_id)
✅ **Soft Delete**: Cards are never physically deleted (audit trail preserved)
✅ **Audit Logging**: All state-changing operations logged with user, IP, timestamp
✅ **Security**: Never stores full card numbers or CVV (last 4 digits only for identification)
✅ **Validation**: Database-level constraints + Pydantic validation
✅ **Transaction Integration**: Transactions can optionally reference which card was used
✅ **Filtering**: List cards by type (credit/debit) or account
✅ **Pagination**: Skip/limit support for large card lists

### Database Schema

```sql
CREATE TABLE cards (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    financial_institution_id UUID REFERENCES financial_institutions(id) ON DELETE SET NULL,
    card_type card_type NOT NULL, -- enum: credit_card, debit_card
    name VARCHAR(100) NOT NULL,
    last_four_digits VARCHAR(4),
    card_network VARCHAR(50),
    expiry_month INTEGER,
    expiry_year INTEGER,
    credit_limit NUMERIC(15,2),
    notes VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT ck_cards_expiry_month_range CHECK (expiry_month IS NULL OR (expiry_month >= 1 AND expiry_month <= 12)),
    CONSTRAINT ck_cards_last_four_digits_format CHECK (last_four_digits IS NULL OR last_four_digits ~ '^[0-9]{4}$'),
    CONSTRAINT ck_cards_credit_limit_positive CHECK (credit_limit IS NULL OR credit_limit > 0)
);

-- Indexes
CREATE INDEX ix_cards_account_id ON cards(account_id);
CREATE INDEX ix_cards_card_type ON cards(card_type);
CREATE INDEX ix_cards_deleted_at ON cards(deleted_at);
CREATE INDEX ix_cards_financial_institution_id ON cards(financial_institution_id);

-- Transaction enhancement
ALTER TABLE transactions ADD COLUMN card_id UUID REFERENCES cards(id) ON DELETE SET NULL;
CREATE INDEX ix_transactions_card_id ON transactions(card_id);
```

---

## Frontend Integration Instructions

### 1. API Endpoints Available

All endpoints require authentication (`Authorization: Bearer {access_token}`).

#### **GET /api/v1/cards**
List all cards for the authenticated user.

**Query Parameters:**
- `card_type` (optional): Filter by "credit_card" or "debit_card"
- `account_id` (optional): Filter by account UUID
- `include_deleted` (optional): Include soft-deleted cards (default: false)
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Max results (default: 100, max: 100)

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "Chase Sapphire Reserve",
    "card_type": "credit_card",
    "last_four_digits": "4242",
    "card_network": "Visa",
    "account": {
      "id": "uuid",
      "account_name": "Credit Card Account"
    },
    "financial_institution": {
      "id": "uuid",
      "name": "Chase Bank"
    }
  }
]
```

#### **GET /api/v1/cards/{card_id}**
Get a specific card by ID.

**Response (200):**
```json
{
  "id": "uuid",
  "name": "Chase Sapphire Reserve",
  "card_type": "credit_card",
  "last_four_digits": "4242",
  "card_network": "Visa",
  "expiry_month": 12,
  "expiry_year": 2027,
  "credit_limit": 25000.00,
  "notes": "Primary travel card",
  "account": { "id": "uuid", "account_name": "..." },
  "financial_institution": { "id": "uuid", "name": "..." },
  "created_at": "2025-12-09T14:00:00Z",
  "updated_at": "2025-12-09T14:00:00Z"
}
```

**Errors:**
- `401 Unauthorized`: Missing/invalid token
- `404 Not Found`: Card doesn't exist or user doesn't own the account

#### **POST /api/v1/cards**
Create a new card.

**Request Body:**
```json
{
  "account_id": "uuid",  // REQUIRED - must own this account
  "card_type": "credit_card",  // REQUIRED - "credit_card" or "debit_card"
  "name": "Chase Sapphire Reserve",  // REQUIRED - display name
  "last_four_digits": "4242",  // OPTIONAL - exactly 4 digits
  "card_network": "Visa",  // OPTIONAL
  "expiry_month": 12,  // OPTIONAL - must be 1-12
  "expiry_year": 2027,  // OPTIONAL - must be 2000-2100
  "credit_limit": 25000.00,  // OPTIONAL - must be positive
  "financial_institution_id": "uuid",  // OPTIONAL
  "notes": "Primary travel card"  // OPTIONAL - max 500 chars
}
```

**Validation Rules:**
- If `expiry_month` provided, `expiry_year` MUST also be provided (and vice versa)
- `last_four_digits` must match pattern `^[0-9]{4}$` (exactly 4 numeric digits)
- `credit_limit` must be greater than 0
- User must own the specified `account_id`

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "Chase Sapphire Reserve",
  "card_type": "credit_card",
  // ... full card details
}
```

**Errors:**
- `400 Bad Request`: Validation error (expiry coupling, invalid format, etc.)
- `403 Forbidden`: Account doesn't belong to user
- `404 Not Found`: Account or financial institution not found
- `422 Unprocessable Entity`: Invalid field values

#### **PATCH /api/v1/cards/{card_id}**
Update an existing card (partial update supported).

**Request Body (all fields optional):**
```json
{
  "name": "Updated Card Name",
  "last_four_digits": "5555",
  "card_network": "Mastercard",
  "expiry_month": 6,
  "expiry_year": 2028,
  "credit_limit": 30000.00,
  "financial_institution_id": "uuid",
  "notes": "Updated notes"
}
```

**Immutable Fields** (cannot be changed):
- `card_type` - card type is permanent
- `account_id` - cannot move card to different account

**Response (200):**
```json
{
  "id": "uuid",
  "name": "Updated Card Name",
  // ... updated card details
}
```

**Errors:**
- `403 Forbidden`: Card doesn't belong to user's account
- `404 Not Found`: Card doesn't exist
- `422 Unprocessable Entity`: Invalid field values

#### **DELETE /api/v1/cards/{card_id}**
Soft-delete a card.

**Response (204 No Content):** Empty body

**Behavior:**
- Card is soft-deleted (sets `deleted_at` timestamp)
- Card remains in database for audit/history
- Transactions referencing this card will have `card_id` set to NULL
- Deleted cards excluded from normal queries

**Errors:**
- `403 Forbidden`: Card doesn't belong to user's account
- `404 Not Found`: Card doesn't exist

---

### 2. Frontend Implementation Tasks

#### **Required UI Components**

1. **Cards List View** (`/cards`)
   - Display all user's cards in a grid or list
   - Show card name, type icon (credit/debit), last 4 digits, network logo
   - Add filter dropdown for card type (All / Credit Cards / Debit Cards)
   - Add filter dropdown for account (All Accounts / [Account Name])
   - Implement pagination (skip/limit)
   - Add "Create Card" button
   - Add click handler to navigate to card details

2. **Card Details View** (`/cards/{id}`)
   - Display full card information
   - Show associated account and financial institution
   - Show expiry date (if available)
   - Show credit limit (if credit card)
   - Show notes
   - Add "Edit" button → opens card form in edit mode
   - Add "Delete" button → shows confirmation dialog

3. **Card Form Component** (Create/Edit)
   - **Account Selection** (required, dropdown from user's accounts, disabled in edit mode)
   - **Card Type** (required, radio: Credit Card / Debit Card, disabled in edit mode)
   - **Card Name** (required, text input, max 100 chars)
   - **Last Four Digits** (optional, text input, exactly 4 digits, pattern validation)
   - **Card Network** (optional, dropdown: Visa/Mastercard/Amex/Discover/Other)
   - **Expiry Date** (optional, two fields: Month dropdown 1-12, Year input 2000-2100)
   - **Credit Limit** (optional, number input, min 0.01, for credit cards only)
   - **Financial Institution** (optional, dropdown from active institutions)
   - **Notes** (optional, textarea, max 500 chars)
   - Validate expiry date coupling (both month+year or neither)
   - Show validation errors inline
   - Add "Save" and "Cancel" buttons

4. **Card Delete Confirmation Dialog**
   - Display warning: "Delete [Card Name]?"
   - Explain soft delete: "This card will be archived and can be restored by support."
   - Show impact: "Transactions linked to this card will remain but card reference will be cleared."
   - Add "Cancel" and "Delete Card" (danger button)

5. **Transaction Integration**
   - Add `card_id` field to transaction create/edit forms
   - Display as optional dropdown: "Card Used (optional)"
   - Filter dropdown to show only cards for the selected account
   - In transaction list/details, display card name if card was used
   - Example: "Chase Sapphire Reserve (••4242)"

#### **State Management**

Add the following to your store:

```typescript
interface Card {
  id: string;
  name: string;
  card_type: 'credit_card' | 'debit_card';
  last_four_digits?: string;
  card_network?: string;
  expiry_month?: number;
  expiry_year?: number;
  credit_limit?: number;
  notes?: string;
  account: {
    id: string;
    account_name: string;
  };
  financial_institution?: {
    id: string;
    name: string;
  };
  created_at: string;
  updated_at: string;
}

// Store slice
interface CardsState {
  cards: Card[];
  selectedCard: Card | null;
  loading: boolean;
  error: string | null;
  filters: {
    cardType?: 'credit_card' | 'debit_card';
    accountId?: string;
  };
  pagination: {
    skip: number;
    limit: number;
    total: number;
  };
}
```

#### **API Service Functions**

Create `src/services/cardService.ts`:

```typescript
export const cardService = {
  // List cards with filters
  list: (params?: {
    card_type?: 'credit_card' | 'debit_card';
    account_id?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/cards', { params }),

  // Get single card
  get: (cardId: string) => api.get(`/cards/${cardId}`),

  // Create card
  create: (data: {
    account_id: string;
    card_type: 'credit_card' | 'debit_card';
    name: string;
    last_four_digits?: string;
    card_network?: string;
    expiry_month?: number;
    expiry_year?: number;
    credit_limit?: number;
    financial_institution_id?: string;
    notes?: string;
  }) => api.post('/cards', data),

  // Update card
  update: (cardId: string, data: Partial<Omit<Card, 'id' | 'account' | 'financial_institution'>>) =>
    api.patch(`/cards/${cardId}`, data),

  // Delete card
  delete: (cardId: string) => api.delete(`/cards/${cardId}`),
};
```

#### **Routing**

Add these routes to your router:

```typescript
{
  path: '/cards',
  component: CardsListView,
  meta: { requiresAuth: true }
},
{
  path: '/cards/new',
  component: CardFormView,
  meta: { requiresAuth: true }
},
{
  path: '/cards/:id',
  component: CardDetailsView,
  meta: { requiresAuth: true }
},
{
  path: '/cards/:id/edit',
  component: CardFormView,
  meta: { requiresAuth: true }
}
```

#### **Navigation**

Update main navigation to include:
- "Cards" menu item (icon: credit card)
- Badge showing count of user's cards (optional)

#### **UX Considerations**

1. **Security Messaging**
   - Display prominent notice: "For security, we only store the last 4 digits of your card"
   - Never show full card numbers
   - Do not allow editing of `last_four_digits` after creation (immutable for security)

2. **Card Type Icons**
   - Credit Card: 💳 or credit card icon
   - Debit Card: 🏦 or debit card icon

3. **Network Logos**
   - Display Visa/Mastercard/Amex/Discover logos when `card_network` is available

4. **Expiry Date Formatting**
   - Display as "MM/YYYY" format
   - Highlight expired cards (compare to current date)
   - Show warning: "This card has expired" in red

5. **Credit Limit Display**
   - Format with currency symbol and commas (e.g., "$25,000.00")
   - Only show for credit cards
   - Consider adding spending progress bar (requires transaction totals)

6. **Soft Delete UX**
   - After deletion, show toast: "Card archived successfully"
   - Do not remove from UI immediately (fade out animation)
   - Provide "Undo" option in toast (re-fetch cards)

7. **Loading States**
   - Show skeleton cards while loading list
   - Show spinner on form submit
   - Disable form during submission

8. **Error Handling**
   - 403 errors: "You don't have permission to access this card"
   - 404 errors: "Card not found or has been deleted"
   - 422 errors: Display field-specific validation messages
   - Network errors: "Unable to connect. Please try again."

#### **Transaction Updates**

Update transaction forms to include card selection:

1. Add `card_id` field (optional UUID) to transaction create/update payloads
2. In transaction form, add dropdown: "Card Used (optional)"
3. Fetch cards for selected account: `GET /api/v1/cards?account_id={account_id}`
4. Display as: "[Card Name] (••[last_four_digits])"
5. Allow "None" option (null value)
6. In transaction list/details, show card name if present

---

### 3. Testing Checklist

Frontend team should test:

- [ ] Create credit card with all fields
- [ ] Create debit card with minimal fields (name only)
- [ ] Edit card name and notes
- [ ] Edit card expiry date
- [ ] Attempt to create card without account_id (should fail 400)
- [ ] Attempt to create card with only expiry_month (should fail 422 - coupling)
- [ ] Attempt to create card with invalid last_four_digits "12345" (should fail 422)
- [ ] Attempt to create card with negative credit_limit (should fail 422)
- [ ] Attempt to access another user's card (should fail 404)
- [ ] Delete card and verify soft delete (card disappears from list)
- [ ] Filter cards by credit_card type
- [ ] Filter cards by debit_card type
- [ ] Filter cards by specific account
- [ ] Pagination with skip/limit
- [ ] Create transaction with card_id
- [ ] Create transaction without card_id (null)
- [ ] View transaction showing card name

---

### 4. Migration Notes

**Database Migration** (already applied in backend):
- Run `alembic upgrade head` to create cards table and add card_id to transactions
- Migration is idempotent and safe to run multiple times

**No Breaking Changes**:
- `card_id` in transactions is nullable - existing transactions unaffected
- All new endpoints under `/api/v1/cards` - no existing endpoints modified
- Transaction schemas updated but `card_id` is optional everywhere

---

### 5. Support & Questions

For questions or issues, contact:
- Backend Team: Feature complete, 17/17 tests passing
- PR: `feature/cards-management` → `main`
- Documentation: See API endpoint descriptions above

**Feature Status**: ✅ Ready for frontend integration
