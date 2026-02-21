# Database Migrations

This directory contains database migration scripts for the AFIRGen backend optimization project.

## Overview

Migrations are used to apply schema changes to the database in a controlled, versioned manner. Each migration has a corresponding rollback script to revert changes if needed.

## Migration Files

### 001_add_fir_indexes.sql

**Purpose**: Add optimized database indexes for FIR tables to improve query performance.

**Changes**:
- Adds `user_id` column to `fir_records` table
- Creates primary indexes on frequently queried columns:
  - `fir_number`
  - `session_id`
  - `status`
  - `created_at`
  - `user_id`
- Creates composite indexes for common query patterns:
  - `idx_user_created`: User's FIRs ordered by creation date
  - `idx_status_created`: Filter by status and sort by date
  - `idx_user_status_created`: User's FIRs filtered by status
  - `idx_status_finalized`: Finalized FIRs ordered by finalization date
- Creates full-text indexes for search functionality:
  - `ft_complaint_text`: Full-text search on complaint text
  - `ft_fir_content`: Full-text search on FIR content
- Creates covering index for common SELECT queries

**Requirements**: Validates Requirements 1.2 (Database Query Optimization)

**Rollback**: `001_add_fir_indexes_rollback.sql`

## Usage

### Using the Migration Runner Script

The `migration_runner.py` script provides a CLI for applying and rolling back migrations.

#### Apply a Migration

```bash
# Using environment variables for database connection
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=afirgen

python migrations/migration_runner.py apply 001_add_fir_indexes
```

Or with command-line arguments:

```bash
python migrations/migration_runner.py apply 001_add_fir_indexes \
  --host localhost \
  --port 3306 \
  --user root \
  --password your_password \
  --database afirgen
```

#### Rollback a Migration

```bash
python migrations/migration_runner.py rollback 001_add_fir_indexes
```

### Manual Execution

You can also execute migrations manually using MySQL client:

```bash
# Apply migration
mysql -h localhost -u root -p afirgen < migrations/001_add_fir_indexes.sql

# Rollback migration
mysql -h localhost -u root -p afirgen < migrations/001_add_fir_indexes_rollback.sql
```

## Migration Naming Convention

Migrations follow the naming pattern: `{number}_{description}.sql`

- **number**: Sequential number (001, 002, etc.)
- **description**: Brief description using snake_case

Rollback scripts use the pattern: `{number}_{description}_rollback.sql`

## Best Practices

1. **Always test migrations** on a development database before applying to production
2. **Backup your database** before running migrations in production
3. **Review rollback scripts** to ensure they properly revert changes
4. **Use transactions** when possible to ensure atomicity
5. **Make migrations idempotent** using `IF EXISTS` and `IF NOT EXISTS` clauses
6. **Document changes** in this README when adding new migrations

## Index Strategy

The indexes created by migration 001 follow these principles:

### Single-Column Indexes
Used for simple lookups and filtering:
- `idx_fir_number`: Lookup by FIR number (unique identifier)
- `idx_user_id`: Filter by user
- `idx_status`: Filter by status
- `idx_created_at`: Sort by creation date

### Composite Indexes
Used for complex queries with multiple conditions:
- **Left-most prefix rule**: MySQL can use composite indexes for queries that match the left-most columns
- **Order matters**: Columns are ordered by selectivity (most selective first)

Example query patterns:
```sql
-- Uses idx_user_created
SELECT * FROM fir_records WHERE user_id = 'user_123' ORDER BY created_at DESC;

-- Uses idx_status_created
SELECT * FROM fir_records WHERE status = 'pending' ORDER BY created_at DESC;

-- Uses idx_user_status_created
SELECT * FROM fir_records 
WHERE user_id = 'user_123' AND status = 'pending' 
ORDER BY created_at DESC;
```

### Full-Text Indexes
Used for text search functionality:
```sql
-- Search in complaint text
SELECT * FROM fir_records 
WHERE MATCH(complaint_text) AGAINST('theft robbery' IN NATURAL LANGUAGE MODE);

-- Search in FIR content
SELECT * FROM fir_records 
WHERE MATCH(fir_content) AGAINST('section 420' IN BOOLEAN MODE);
```

### Covering Indexes
Include all columns needed for a query, allowing index-only scans:
```sql
-- This query can be satisfied entirely from idx_covering_list
SELECT user_id, status, created_at, fir_number, session_id
FROM fir_records
WHERE user_id = 'user_123' AND status = 'pending'
ORDER BY created_at DESC;
```

## Verifying Indexes

After applying migrations, verify indexes are created:

```sql
-- Show all indexes on fir_records table
SHOW INDEX FROM fir_records;

-- Analyze query execution plan
EXPLAIN SELECT * FROM fir_records WHERE user_id = 'user_123' ORDER BY created_at DESC;
```

Look for:
- `type: ref` or `type: range` (good - using index)
- `key: idx_user_created` (shows which index is used)
- Low `rows` count (fewer rows examined = better performance)

## Troubleshooting

### Migration Fails with "Index already exists"

The migration is designed to be idempotent. If it fails, check:
1. Are indexes already created?
2. Run `SHOW INDEX FROM fir_records;` to see existing indexes
3. If needed, manually drop conflicting indexes before re-running

### Rollback Fails

If rollback fails:
1. Check the error message for specific issues
2. Verify the table structure: `DESCRIBE fir_records;`
3. Manually fix any inconsistencies
4. Re-run the rollback script

### Performance Issues After Migration

If queries are slower after adding indexes:
1. Run `ANALYZE TABLE fir_records;` to update statistics
2. Check query execution plans with `EXPLAIN`
3. Consider removing unused indexes (each index has overhead for writes)

## Future Migrations

When adding new migrations:
1. Increment the migration number (002, 003, etc.)
2. Create both forward and rollback scripts
3. Test thoroughly on development database
4. Update this README with migration details
5. Document any new index strategies or patterns
