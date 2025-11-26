Remove all user role-related code from the codebase. Users are treated uniformly, with admin privileges handled exclusively by the is_admin flag. Delete the following:

- Role tables, models, and database columns
- Role assignment/management functions and APIs
- Role-based access control (RBAC) logic and middleware
- Role enums, constants, and type definitions
- Role checks in authorization logic (replace with is_admin checks where needed)
- Role-related UI components and forms
- Role fields in user schemas and DTOs
- Any migrations that created role structures

Ensure admin functionality remains intact using only the is_admin boolean flag. Test thoroughly to verify no broken dependencies remain.
