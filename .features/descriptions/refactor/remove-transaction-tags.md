Remove the `tags feature from transactions throughout the entire codebase.

This includes:
- **Database** – Remove the `TransactionTag` table and the `tags` field from the `transaction` table/model.
- **Schemas/Models** – Update all data models, DTOs, and validation schemas to remove `tags`
- **API Endpoints** – Remove any endpoints or request/response handling related to transaction tags
- **Services/Business Logic** – Remove tag-related logic from all service layers
- **Tests** – Update or remove any unit, integration, or e2e tests that reference transaction tags

Ensure no orphaned code, imports, or references to transaction tags remain after the changes.