Remove the /api/v1/admin/bootstrap endpoint and create the superuser with alembic instead.
Change the following config variable names:
BOOTSTRAP_ADMIN_USERNAME -> SUPERADMIN_USERNAME
BOOTSTRAP_ADMIN_EMAIL -> SUPERADMIN_EMAIL
BOOTSTRAP_ADMIN_PASSWORD -> SUPERADMIN_PASSWORD
BOOTSTRAP_ADMIN_FULL_NAME -> SUPERADMIN_FULL_NAME

Forget about legacy. I don't want to support legacy. I just want to change it. 