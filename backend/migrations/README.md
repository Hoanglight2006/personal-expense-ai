# Database migrations

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
