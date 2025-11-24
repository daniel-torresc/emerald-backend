Remove the /api/v1/admin/bootstrap endpoint and create the superuser in the initial_schema alembic version instead.
Change the following config variable names:
BOOTSTRAP_ADMIN_USERNAME -> SUPERADMIN_USERNAME
BOOTSTRAP_ADMIN_EMAIL -> SUPERADMIN_EMAIL
BOOTSTRAP_ADMIN_PASSWORD -> SUPERADMIN_PASSWORD
BOOTSTRAP_ADMIN_FULL_NAME -> SUPERADMIN_FULL_NAME

Don't create a legacy endpoint. Just remove it. I don't want to support legacy, as the app is not yet on production. 