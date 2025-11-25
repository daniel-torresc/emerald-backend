### Optional Fields in Account Schema

1. **`bank`** (enum, optional, max 100 chars)
   - Frontend designs show bank name on account cards
   - Would allow users to track which bank each account is with

2. **`notes`** (string, optional, max 500 chars)
   - Allow users to add personal notes/descriptions to accounts
   - Common feature in finance apps


4. **MEDIUM** (Nice to have):
   - Add `bank` field to Account schema
   - Add `notes` field to Account schema

5. **LOW** (Can implement later):
   - Add `last_transaction_date` to AccountResponse







# Instructions: Add Account Metadata Fields

## Objective
Add new metadata fields to the Account model and update the existing Alembic migration to include these columns in the database schema.

## Fields to Add

Add the following fields to your Account Pydantic model:

1. **color_hex**: Hex color code for visual identification (default to #818E8F)
2. **icon_url**: URL or path to the account icon (can be None)
3. **bank_name**: Name of the financial institution
4. **iban**: Encrypted IBAN (full account number, stored encrypted)
5. **iban_last_four**: Last 4 digits of IBAN for display purposes
6. **notes**: Free-text field for user notes and comments

## Steps

### 1. Update the Pydantic Model

Locate your Account model and add the new fields

### 2. Update the Alembic Migration

Locate the most recent Alembic migration file for the accounts table (in your `alembic/versions/` directory) and add the columns to that version. Don't create a new version, just update this one and rerun migrations. It doesn't matter if data is lost, we are in a very early stage. 

### 3. Update SQLAlchemy Model 

Update the SQLAlchemy model accordingly

### 4. Update corresponding API endpoints

Update the create, list, get, and update account methods to support these new fields. The new fields that can be updated are: 
- color_hex
- icon_url
- notes
The rest can only be set at creation time.

## Validation

After applying the migration:

1. Verify the columns exist in the database
2. Test creating/updating accounts with the new fields

## Notes

- Consider implementing encryption/decryption logic for the `iban` field before storing
- The `iban_last_four` should be extracted from the full IBAN before encryption
- `color_hex` is limited to 7 characters to store standard hex colors (e.g., "#FF5733")