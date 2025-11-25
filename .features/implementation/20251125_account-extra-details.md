# Account Extra Details - Frontend Integration Guide

**Implementation Date:** November 25, 2025
**Feature Branch:** `feature/account-extra-details`
**Status:** ✅ Complete - Ready for Frontend Integration

---

## 📋 Summary

The backend now supports **6 new optional metadata fields** for accounts, enabling visual customization, bank information storage, and encrypted IBAN handling.

---

## 🆕 New Account Fields

### Visual Customization
| Field | Type | Required | Default | Description | Updateable |
|-------|------|----------|---------|-------------|------------|
| `color_hex` | `string` | No | `#818E8F` | Hex color code for UI display (e.g., `#FF5733`) | ✅ Yes |
| `icon_url` | `string` | No | `null` | URL or path to account icon image | ✅ Yes |

### Bank Information (Immutable)
| Field | Type | Required | Default | Description | Updateable |
|-------|------|----------|---------|-------------|------------|
| `bank_name` | `string` | No | `null` | Name of financial institution (max 100 chars) | ❌ No |
| `iban` | `string` | No | `null` | Full IBAN - **encrypted at rest** | ❌ No |
| `iban_last_four` | `string` | No | `null` | **Read-only** - Last 4 digits for display | ❌ No |

### User Notes
| Field | Type | Required | Default | Description | Updateable |
|-------|------|----------|---------|-------------|------------|
| `notes` | `string` | No | `null` | Personal notes about the account (max 500 chars) | ✅ Yes |

---

## 🔧 Required Frontend Changes

### 1. Update Account Creation Form

**Add these optional fields to your create account form:**

```typescript
// POST /api/v1/accounts
{
  // Existing required fields
  "account_name": "My Savings",
  "account_type": "savings",
  "currency": "USD",
  "opening_balance": "1000.00",

  // NEW OPTIONAL FIELDS - Add to your form
  "bank_name": "Chase Bank",           // Optional, immutable
  "iban": "DE89370400440532013000",    // Optional, immutable, will be encrypted
  "color_hex": "#FF5733",               // Optional, default: #818E8F
  "icon_url": "https://...",            // Optional
  "notes": "Emergency fund savings"     // Optional
}
```

**Form Field Recommendations:**
- **`color_hex`**: Add a color picker component (default to `#818E8F` gray)
- **`icon_url`**: Add file upload or icon selector
- **`bank_name`**: Add text input with 100 character limit
- **`iban`**: Add text input with IBAN validation (optional)
- **`notes`**: Add textarea with 500 character limit

---

### 2. Update Account Display Components

**The API response now includes new fields:**

```typescript
// GET /api/v1/accounts/{id} - Response
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "account_name": "My Savings",
  "account_type": "savings",
  "currency": "USD",
  "opening_balance": "1000.00",
  "current_balance": "1234.56",
  "is_active": true,

  // NEW FIELDS IN RESPONSE
  "color_hex": "#FF5733",              // Use for account card background/badge
  "icon_url": "https://...",           // Display account icon
  "bank_name": "Chase Bank",           // Show bank name
  "iban_last_four": "3000",            // Show "****3000" - NEVER full IBAN
  "notes": "Emergency fund",           // Display in account details

  "created_at": "2025-11-04T00:00:00Z",
  "updated_at": "2025-11-04T00:00:00Z"
}
```

**Update your account card/list components to:**
- **Apply `color_hex`** as background color, badge color, or border accent
- **Display `icon_url`** as account icon/avatar
- **Show `bank_name`** below account name (if provided)
- **Display `iban_last_four`** as "****1234" (if IBAN was set)
- **Show `notes`** in account details view

---

### 3. Update Account Edit Form

**Allow users to update these fields:**

```typescript
// PUT /api/v1/accounts/{id}
{
  // Existing updateable fields
  "account_name": "Renamed Account",   // Optional
  "is_active": false,                  // Optional

  // NEW UPDATEABLE FIELDS
  "color_hex": "#3498DB",              // Optional
  "icon_url": "https://...",           // Optional
  "notes": "Updated notes"             // Optional
}
```

**⚠️ IMPORTANT - These fields are IMMUTABLE:**
- `bank_name` - Cannot be changed after account creation
- `iban` / `iban_last_four` - Cannot be changed after account creation
- `currency` - Already immutable
- `opening_balance` - Already immutable
- `account_type` - Already immutable

**UI Recommendation:**
- Gray out or hide immutable fields in edit form
- Show them as read-only text

---

### 4. Account List Component Updates

**The list endpoint now returns visual metadata:**

```typescript
// GET /api/v1/accounts - Response
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "account_name": "My Savings",
    "account_type": "savings",
    "currency": "USD",
    "current_balance": "1234.56",
    "is_active": true,

    // NEW FIELDS FOR LIST VIEW
    "color_hex": "#FF5733",
    "icon_url": "https://...",
    "bank_name": "Chase Bank",

    "created_at": "2025-11-04T00:00:00Z"
  }
]
```

**Use these fields to:**
- Color-code account cards using `color_hex`
- Display icons using `icon_url`
- Show bank name subtitle using `bank_name`

---

## 🔒 Security Notes for Frontend

### ⚠️ CRITICAL - IBAN Handling

**NEVER:**
- ❌ Store full IBAN in frontend state/localStorage
- ❌ Display full IBAN to user
- ❌ Send full IBAN in GET requests
- ❌ Expect full IBAN in API responses

**ALWAYS:**
- ✅ Send full IBAN **ONLY** during account creation (POST)
- ✅ Display **ONLY** `iban_last_four` as "****1234"
- ✅ Full IBAN is encrypted server-side automatically
- ✅ Backend NEVER returns full IBAN in any response

---

## 📝 Validation Rules

### Frontend Validation (Add to your forms)

**`color_hex`:**
```javascript
// Must match: #RRGGBB (7 characters: # + 6 hex digits)
const colorRegex = /^#[0-9A-Fa-f]{6}$/;
if (!colorRegex.test(colorHex)) {
  error = "Invalid color format. Use #RRGGBB (e.g., #FF5733)";
}
```

**`iban`:**
```javascript
// Use a library like 'ibantools' or 'iban' for validation
import { isValidIBAN } from 'ibantools';

if (iban && !isValidIBAN(iban)) {
  error = "Invalid IBAN format or checksum";
}

// Remove spaces/hyphens before sending:
const normalized = iban.replace(/[\s-]/g, '').toUpperCase();
```

**`bank_name`:**
```javascript
// Max 100 characters
if (bankName && bankName.length > 100) {
  error = "Bank name must be 100 characters or less";
}
```

**`icon_url`:**
```javascript
// Must be valid URL format
try {
  new URL(iconUrl);
} catch {
  error = "Invalid URL format";
}
```

**`notes`:**
```javascript
// Max 500 characters
if (notes && notes.length > 500) {
  error = "Notes must be 500 characters or less";
}
```

---

## 🎨 UI/UX Recommendations

### Color Picker Component
```typescript
// Provide common banking colors as presets
const PRESET_COLORS = [
  { name: "Default Gray", hex: "#818E8F" },
  { name: "Blue", hex: "#3498DB" },
  { name: "Green", hex: "#2ECC71" },
  { name: "Red", hex: "#E74C3C" },
  { name: "Orange", hex: "#FF5733" },
  { name: "Purple", hex: "#9B59B6" },
];
```

### Icon Selector
```typescript
// Provide default bank icons or allow custom upload
const PRESET_ICONS = [
  { name: "Savings", url: "/icons/piggy-bank.svg" },
  { name: "Checking", url: "/icons/wallet.svg" },
  { name: "Credit Card", url: "/icons/credit-card.svg" },
  { name: "Investment", url: "/icons/chart.svg" },
];
```

### IBAN Display
```typescript
// Always mask IBAN in display
function displayIBAN(ibanLastFour: string | null): string {
  return ibanLastFour ? `•••• ${ibanLastFour}` : "Not set";
}
```

---

## 🧪 Testing Checklist

### Test Account Creation
- [ ] Create account with all new fields populated
- [ ] Create account with NO optional fields (should use defaults)
- [ ] Create account with only `color_hex` set
- [ ] Create account with valid IBAN - verify `iban_last_four` in response
- [ ] Create account with invalid IBAN - expect 422 error
- [ ] Create account with invalid color format - expect 422 error

### Test Account Update
- [ ] Update `color_hex` - verify changes persist
- [ ] Update `icon_url` - verify changes persist
- [ ] Update `notes` - verify changes persist
- [ ] Try to update `bank_name` - should be ignored/rejected
- [ ] Try to update `iban` - should be ignored/rejected

### Test Account Display
- [ ] Account card uses `color_hex` for styling
- [ ] Account icon displays from `icon_url`
- [ ] Bank name shows correctly
- [ ] IBAN displays as masked (****1234)
- [ ] Notes display in account details

---

## 📊 TypeScript Interface Updates

**Update your TypeScript interfaces:**

```typescript
// Account creation request
export interface AccountCreateRequest {
  account_name: string;
  account_type: AccountType;
  currency: string;
  opening_balance: string;
  // NEW OPTIONAL FIELDS
  bank_name?: string;
  iban?: string;
  color_hex?: string;
  icon_url?: string;
  notes?: string;
}

// Account update request
export interface AccountUpdateRequest {
  account_name?: string;
  is_active?: boolean;
  // NEW UPDATEABLE FIELDS
  color_hex?: string;
  icon_url?: string;
  notes?: string;
}

// Account response (detail view)
export interface AccountResponse {
  id: string;
  user_id: string;
  account_name: string;
  account_type: AccountType;
  currency: string;
  opening_balance: string;
  current_balance: string;
  is_active: boolean;
  // NEW FIELDS
  color_hex: string;           // Always present (has default)
  icon_url: string | null;
  bank_name: string | null;
  iban_last_four: string | null;  // READ ONLY - never send full IBAN
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// Account list item (optimized for lists)
export interface AccountListItem {
  id: string;
  account_name: string;
  account_type: AccountType;
  currency: string;
  current_balance: string;
  is_active: boolean;
  // NEW FIELDS
  color_hex: string;
  icon_url: string | null;
  bank_name: string | null;
  created_at: string;
}
```

---

## 🔄 Migration Strategy

### Existing Accounts
All existing accounts will have:
- `color_hex`: `#818E8F` (default gray)
- `icon_url`: `null`
- `bank_name`: `null`
- `iban`: `null`
- `iban_last_four`: `null`
- `notes`: `null`

**Action Required:**
- Update UI to handle `null` values gracefully
- Provide option to "Edit account" and add missing details
- Show default color/icon when fields are `null`

---

## 📞 Support & Questions

**Backend API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Questions or Issues?**
- Contact backend team for API clarifications
- Check `.features/plans/20251124_account-extra-details.md` for detailed specs
- Review `src/schemas/account.py` for exact validation rules

---

## ✅ Quick Start Checklist

**Frontend Developer Action Items:**

1. **Update TypeScript Interfaces**
   - [ ] Add 6 new fields to `AccountCreateRequest`
   - [ ] Add 3 new fields to `AccountUpdateRequest`
   - [ ] Add 6 new fields to `AccountResponse`
   - [ ] Add 3 new fields to `AccountListItem`

2. **Update Create Account Form**
   - [ ] Add color picker (default: `#818E8F`)
   - [ ] Add icon URL input or file uploader
   - [ ] Add bank name text input (max 100 chars)
   - [ ] Add IBAN input with validation (optional)
   - [ ] Add notes textarea (max 500 chars)

3. **Update Edit Account Form**
   - [ ] Add color picker for `color_hex`
   - [ ] Add icon URL input/uploader for `icon_url`
   - [ ] Add notes textarea for `notes`
   - [ ] Make `bank_name` read-only (grayed out)
   - [ ] Show `iban_last_four` as masked, read-only

4. **Update Account Display Components**
   - [ ] Use `color_hex` for account card styling
   - [ ] Display `icon_url` as account icon
   - [ ] Show `bank_name` as subtitle/secondary text
   - [ ] Display `iban_last_four` as "****1234"
   - [ ] Show `notes` in account details view

5. **Add Validation**
   - [ ] Validate hex color format (`/^#[0-9A-Fa-f]{6}$/`)
   - [ ] Validate IBAN format using library
   - [ ] Enforce 100 char limit on `bank_name`
   - [ ] Enforce 500 char limit on `notes`
   - [ ] Validate URL format for `icon_url`

6. **Test Thoroughly**
   - [ ] Create account with all fields
   - [ ] Create account with minimal fields
   - [ ] Update account colors/icons/notes
   - [ ] Verify immutable fields can't be changed
   - [ ] Test IBAN masking displays correctly

---

**🎉 Ready to Implement!** All backend changes are complete and tested. The API is ready for frontend integration.
