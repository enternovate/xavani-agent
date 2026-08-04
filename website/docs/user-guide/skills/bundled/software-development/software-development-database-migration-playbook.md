---
title: "Database Migration Playbook — Safe database schema migrations — forward-only, tested, reversible"
sidebar_label: "Database Migration Playbook"
description: "Safe database schema migrations — forward-only, tested, reversible"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Database Migration Playbook

Safe database schema migrations — forward-only, tested, reversible.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/database-migration-playbook` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Database Migration Playbook

> "Every migration should be safe to run on a live database with zero downtime."

## When to use

- Adding or modifying tables, columns, or indexes.
- Changing data types or constraints.
- Backfilling data.

## Prerequisites

- Migration tool configured (Alembic, Flyway, Prisma, etc.).
- Staging environment that mirrors production.

## Steps

### 1. Write the migration

Forward migration:
```sql
-- Add column (safe: no lock on modern DBs)
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255);

-- Add index (use CONCURRENTLY for zero-downtime)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
```

### 2. Write the rollback

Every migration must have a rollback:
```sql
-- Rollback
DROP INDEX IF EXISTS idx_users_email;
ALTER TABLE users DROP COLUMN IF EXISTS display_name;
```

### 3. Test on staging

- Run the migration on a copy of production data.
- Verify the schema change is correct.
- Verify the rollback works.
- Measure migration duration.

### 4. Safe migration patterns

**Safe (no downtime):**
- Adding a nullable column.
- Adding an index (CONCURRENTLY).
- Adding a new table.

**Risky (requires care):**
- Renaming a column (add new, backfill, switch, drop old).
- Changing a column type (add new, backfill, switch).
- Dropping a column (stop reading first, then drop).

**Dangerous (avoid):**
- Dropping a table with data.
- Changing primary keys.
- Large data backfills without batching.

### 5. Deploy

1. Run migration in staging, verify.
2. Run migration in production during low traffic.
3. Monitor for errors.
4. If issues: run rollback immediately.

### 6. Backfill data (if needed)

Batch large backfills:
```sql
-- Process 1000 rows at a time
UPDATE users SET display_name = name
WHERE display_name IS NULL
LIMIT 1000;
```

## Verification

- Migration runs successfully on staging.
- Rollback is tested and works.
- Migration duration is acceptable (&lt;30s for most).
- No data loss or corruption.
