- Inspect the CURRENT database schema state (all tables, columns, constraints, indexes, etc.)
- Generate ONE clean "initial" base migration that creates everything from scratch
- This should be a "initial_schema" migration
- Delete/ignore existing migration files - we're starting fresh

Merge all the alembic migrations in one single stage. I am in the very early stages of my app and no one is using it yet, so having multiple migrations is unuseful.