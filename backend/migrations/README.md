# Database migrations

These scripts upgrade specific legacy MySQL 8 schemas; they are not a replacement
for creating a fresh current schema from SQLAlchemy metadata. The current
application requires `categories.type`. Review the target schema and the SQL
effects before applying `001_category_management.sql`, which was written for a
legacy category design.

`001_category_management.sql` targets MySQL 8 and upgrades the legacy category
schema. Back up the database, then execute the whole script with a MySQL client.

The migration is safe to retry after interrupted DDL. It performs an ownership
preflight, merges categories that normalize to the same name, repoints
transactions, and combines colliding monthly budgets before adding the new
constraints. Budget amounts are summed when two legacy categories collapse into
one category and period.

Category merging cannot be automatically rolled back because the old `type`
field no longer has an unambiguous value. Restore the pre-migration backup if a
full rollback is required. Do not run this migration against SQLite; the normal
test suite creates the current schema directly from SQLAlchemy metadata.

Apply `001`, `002`, then `003` only after taking and testing a backup. The full
chain has not been executed in the current development environment. See
[docs/DATABASE.md](../../docs/DATABASE.md) for the current model schema,
soft-delete semantics and the disposable MySQL migration-test command.
