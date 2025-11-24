# Backend Team Requirements

## Summary

The frontend has been implemented following the principle that **backend is the authoritative source for all business data**. However, several endpoints are missing and need to be implemented.

---

## 🚨 CRITICAL - Missing Endpoints

### 1. Metadata/Enum Endpoints

**Problem:** Frontend needs to dynamically fetch dropdown options, enums, and business configurations rather than hardcoding them.

#### `GET /api/metadata/account-types`

Returns available account types with display metadata. Enums should be retrieved from database. The types of accounts that there exist are:
- Current Accounts
- Savings Accounts
- Investment Accounts
- Other Accounts
Update whatever's needed to follow this (alembic versions, Python enums, etc.). We will add more account types in the future. But now, support only these four.

```json
{
  "account_types": [
    {
      "key": "checking",
      "label": "Checking"
    },
    {
      "key": "savings",
      "label": "Savings"
    },
    {
      "key": "investment",
      "label": "Investment"
    },
    {
      "key": "other",
      "label": "Other"
    }
  ]
}
```

**Why needed:**
- Account creation dropdown
- Account filtering
- Ensures frontend and backend stay in sync
- Allows backend to add new types without frontend changes

---

#### `GET /api/metadata/currencies`

Returns supported currencies.

```json
{
  "currencies": [
    {
      "code": "USD",
      "symbol": "$",
      "name": "US Dollar",
    },
    {
      "code": "EUR",
      "symbol": "€",
      "name": "Euro",
    }
    // ... etc
  ]
}
```

**Why needed:**
- Currency selection dropdown in accounts and transactions
- Currency display formatting
- Ensures only valid currencies can be selected

---

#### `GET /api/metadata/transaction-types`

Returns available transaction types. Enums should be retrieved from database. The types of transactions that there exist are:
- Income: money in
- Expense: money out
- Transfer: transfer between own accounts
Update whatever's needed to follow this (alembic versions, Python enums, etc.). We will add more transaction types in the future. But now, support only these three.

```json
{
  "transaction_types": [
    {
      "key": "income",
      "label": "Income"
    },
    {
      "value": "expense",
      "label": "Expense"
    },
    {
      "value": "transfer",
      "label": "Transfer"
    }
  ]
}
```

**Why needed:**
- Transaction filtering
- Transaction type badges with correct colors
- Transaction creation dropdown

---

## ✅ Current Workaround

Frontend is using **temporary mocks** for missing endpoints:

- These mocks are clearly marked with `TODO` comments
- Will be replaced immediately when endpoints are available

---

## 📋 Implementation Checklist

- [ ] Implement `GET /api/metadata/account-types`
- [ ] Implement `GET /api/metadata/currencies`
- [ ] Implement `GET /api/metadata/transaction-types`

---
