# Feature 3.4: Budget Tracking by Taxonomy

**Phase**: 3 - Enhancement
**Priority**: High
**Dependencies**: Features 3.1 (Taxonomies), 3.2 (Taxonomy Terms)
**Estimated Effort**: 2 weeks

---

## Overview

Enable users to create budgets for any taxonomy term with configurable time periods, alert thresholds, and rollover settings. Track spending against budgets and alert when thresholds reached.

---

## Business Context

**Problem**: Users cannot set spending limits, track against budgets, or receive alerts when approaching limits.

**Solution**: Flexible budget system that works with any taxonomy term, supporting various time periods and account scoping.

---

## Functional Requirements

### Budget Data

#### Core Fields
- **User ID** (required): Budget owner
- **Taxonomy Term ID** (required): What to budget (e.g., "Groceries", "Venezia 2024")
- **Account ID** (optional): Scope to specific account, or NULL for all accounts
- **Name** (required): Budget name
- **Amount** (required): Budget limit
- **Currency** (required): ISO 4217 code

#### Time Period
- **Period** (required): daily, weekly, monthly, quarterly, yearly, custom
- **Start Date** (required): When budget starts
- **End Date** (optional): When budget ends (NULL for recurring)

#### Settings
- **Alert Threshold** (optional): Amount/percentage to trigger alert
- **Rollover Unused** (boolean): Carry unused budget to next period
- **Is Active** (boolean): Budget enabled/disabled

#### Lifecycle
- Soft delete support
- Audit fields

---

## Budget Types

### Recurring Budgets
- No end date (end_date = NULL)
- Repeat based on period
- Examples:
  - $600/month for Groceries
  - $200/week for Restaurants
  - $50/day for Coffee

### One-Time Budgets
- Specific date range
- Examples:
  - $5000 for Venezia 2024 trip (May 1-15)
  - $10000 for Kitchen Renovation (Q1 2025)

### Account-Scoped Budgets
- Limit to specific account
- Examples:
  - $1000/month for Business expenses (Business Checking account only)
  - $500/month for Personal groceries (Personal account only)

---

## User Capabilities

### Budget Creation
- Create budget for any taxonomy term
- Choose time period
- Set alert threshold
- Enable/disable rollover
- Scope to account (optional)

### Budget Tracking
- See current spending vs budget
- Visual progress bars
- Percentage used
- Amount remaining
- Days remaining in period

### Budget Alerts
- Alert when threshold reached (e.g., 80% of budget)
- Alert when budget exceeded
- Alert before period ends if under-budget (optional)

### Budget Management
- View all budgets
- Edit budget amounts
- Adjust periods
- Deactivate budgets
- Delete budgets

### Reporting
- Budget vs actual by period
- Trends over time
- Over/under budget analysis
- Forecast based on current pace

---

## Data Model Requirements

### New Table: `budgets`

**Columns**:
```
id                  UUID (Primary Key)
user_id             UUID NOT NULL (FK to users)
taxonomy_term_id    UUID NOT NULL (FK to taxonomy_terms)
account_id          UUID NULL (FK to accounts)
name                VARCHAR(200) NOT NULL
amount              NUMERIC(15,2) NOT NULL
currency            VARCHAR(3) NOT NULL
period              ENUM NOT NULL
start_date          DATE NOT NULL
end_date            DATE NULL
alert_threshold     NUMERIC(15,2) NULL
rollover_unused     BOOLEAN NOT NULL DEFAULT false
is_active           BOOLEAN NOT NULL DEFAULT true
created_at          TIMESTAMP NOT NULL
updated_at          TIMESTAMP NOT NULL
deleted_at          TIMESTAMP NULL
created_by          UUID NULL
updated_by          UUID NULL
```

**Indexes**:
- Primary key on `id`
- Index on `user_id`
- Index on `taxonomy_term_id`
- Index on `account_id`
- Index on `period`
- Index on `start_date`
- Index on `is_active`
- Index on `deleted_at`

**Constraints**:
- CHECK: `currency ~ '^[A-Z]{3}$'`
- CHECK: `amount > 0`
- CHECK: `alert_threshold IS NULL OR alert_threshold <= amount`

**Enums**:
```
BudgetPeriod: daily, weekly, monthly, quarterly, yearly, custom
```

---

## API Requirements

### Endpoints

**1. List Budgets**
```
GET /api/v1/budgets
```
- List user's budgets
- Include current spending
- Filter by period, active status
- Show progress percentages

**2. Get Budget**
```
GET /api/v1/budgets/{id}
```
- Get budget with spending details
- Include transaction count
- Show daily/weekly pace

**3. Create Budget**
```
POST /api/v1/budgets
```
- Create new budget
- Validate taxonomy term exists
- Validate account belongs to user

**4. Update Budget**
```
PATCH /api/v1/budgets/{id}
```
- Update amount, period, settings
- Cannot change user_id

**5. Delete Budget**
```
DELETE /api/v1/budgets/{id}
```
- Soft delete budget

**6. Budget Performance**
```
GET /api/v1/budgets/{id}/performance
```
- Detailed spending analysis
- Trend over time
- Forecast to end of period

---

## Budget Calculations

### Current Period Spending
```
Calculate spending for:
- All transactions with taxonomy_term_id
- Within current period dates
- Optionally filtered by account_id
- Sum amounts
```

### Remaining Budget
```
remaining = budget_amount - current_spending
```

### Progress Percentage
```
percentage = (current_spending / budget_amount) * 100
```

### Alert Status
```
IF current_spending >= alert_threshold THEN
  Status: ALERT
ELSE IF current_spending >= budget_amount THEN
  Status: EXCEEDED
ELSE
  Status: OK
```

---

## Period Calculation

### Period Boundaries
- **Daily**: Start of day to end of day
- **Weekly**: Monday to Sunday
- **Monthly**: 1st to last day of month
- **Quarterly**: Jan-Mar, Apr-Jun, Jul-Sep, Oct-Dec
- **Yearly**: Jan 1 to Dec 31
- **Custom**: start_date to end_date

### Rollover Logic
If rollover_unused = true:
```
next_period_budget = base_amount + (base_amount - previous_spending)
```

---

## Validation Rules

- Amount must be positive
- Currency must be valid ISO 4217
- Alert threshold must be <= amount
- End date must be after start date (if provided)
- Taxonomy term must exist
- Account must belong to user (if provided)

---

## Business Rules

### Budget Scope
- If account_id NULL: Budget applies to all accounts
- If account_id set: Budget only for that account

### Hierarchy Handling
- Budget applies to term and all child terms
- Example: "Food" budget includes "Groceries" and "Restaurants"

### Period Overlap
- Can have multiple budgets for same term with different periods
- Example: $600/month for Groceries AND $5000/year for Food

---

## Alert System

### Alert Triggers
1. **Threshold Reached**: current_spending >= alert_threshold
2. **Budget Exceeded**: current_spending > amount
3. **Period Ending**: X days before end with unused budget

### Alert Channels
- In-app notifications
- Email (optional)
- Dashboard warnings

---

## Testing Requirements

- Test creating budgets for different periods
- Test budget calculations
- Test account scoping
- Test hierarchy rollup
- Test rollover logic
- Test alert triggering
- Test period boundary calculations

---

## Success Criteria

1. ✅ `budgets` table created
2. ✅ Budget period enum created
3. ✅ Users can create budgets for taxonomy terms
4. ✅ Spending calculations accurate
5. ✅ Alerts trigger correctly
6. ✅ Period calculations correct
7. ✅ Rollover works
8. ✅ All tests passing

---

## Notes

- Budgets work with ANY taxonomy (Categories, Trips, Projects, etc.)
- Flexible periods support different use cases
- Rollover enables envelope budgeting
- Account scoping enables business/personal separation
