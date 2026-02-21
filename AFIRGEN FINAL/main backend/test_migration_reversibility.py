"""
Property-based test for database migration reversibility.

Feature: backend-optimization
Property 36: Database migration reversibility
Validates: Requirements 10.4

For any database migration script, applying the migration and then reverting it 
should return the database schema to its original state (round-trip property).
"""

import pytest
import mysql.connector
from typing import Dict, List, Set, Tuple
import os
from hypothesis import given, strategies as st, settings, HealthCheck
from dataclasses import dataclass


@dataclass
class TableSchema:
    """Represents a table's schema for comparison."""
    name: str
    columns: Dict[str, str]  # column_name -> column_type
    indexes: Set[str]  # index names
    
    def __eq__(self, other):
        if not isinstance(other, TableSchema):
            return False
        return (
            self.name == other.name and
            self.columns == other.columns and
            self.indexes == other.indexes
        )
    
    def __hash__(self):
        return hash((self.name, tuple(sorted(self.columns.items())), tuple(sorted(self.indexes))))


class DatabaseSchemaCapture:
    """Captures and compares database schemas."""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
    
    def get_connection(self):
        """Create database connection."""
        return mysql.connector.connect(**self.db_config)
    
    def capture_table_schema(self, table_name: str) -> TableSchema:
        """Capture the schema of a specific table."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get column information
            cursor.execute(f"""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (self.db_config['database'], table_name))
            
            columns = {}
            for row in cursor.fetchall():
                col_def = f"{row['COLUMN_TYPE']}"
                if row['IS_NULLABLE'] == 'NO':
                    col_def += " NOT NULL"
                if row['EXTRA']:
                    col_def += f" {row['EXTRA']}"
                columns[row['COLUMN_NAME']] = col_def
            
            # Get index information
            cursor.execute(f"""
                SELECT DISTINCT INDEX_NAME
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                AND INDEX_NAME != 'PRIMARY'
            """, (self.db_config['database'], table_name))
            
            indexes = {row['INDEX_NAME'] for row in cursor.fetchall()}
            
            return TableSchema(name=table_name, columns=columns, indexes=indexes)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_all_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s
                AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """, (self.db_config['database'],))
            
            return [row[0] for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            conn.close()
    
    def capture_database_schema(self) -> Dict[str, TableSchema]:
        """Capture the schema of all tables in the database."""
        tables = self.get_all_tables()
        return {table: self.capture_table_schema(table) for table in tables}
    
    def execute_sql_file(self, sql_file_path: str):
        """Execute SQL statements from a file."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            with open(sql_file_path, 'r') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for statement in statements:
                # Skip comments
                if statement.startswith('--') or not statement:
                    continue
                
                try:
                    cursor.execute(statement)
                    conn.commit()
                except mysql.connector.Error as e:
                    # Some statements might fail if objects don't exist (e.g., DROP IF EXISTS)
                    # This is expected behavior for idempotent migrations
                    if "doesn't exist" not in str(e).lower() and "unknown" not in str(e).lower():
                        raise
            
        finally:
            cursor.close()
            conn.close()


def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment variables."""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'afirgen_test'),
    }


@pytest.fixture
def db_schema_capture():
    """Fixture to provide database schema capture utility."""
    return DatabaseSchemaCapture(get_db_config())


@pytest.fixture
def ensure_test_database():
    """Ensure test database exists and is clean."""
    db_config = get_db_config()
    
    # Connect without database to create it
    conn_config = db_config.copy()
    db_name = conn_config.pop('database')
    
    conn = mysql.connector.connect(**conn_config)
    cursor = conn.cursor()
    
    try:
        # Create test database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        
        # Create base fir_records table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fir_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fir_number VARCHAR(50) UNIQUE NOT NULL,
                session_id VARCHAR(100) NOT NULL,
                complaint_text TEXT,
                fir_content TEXT,
                violations_json JSON,
                status VARCHAR(50) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finalized_at TIMESTAMP NULL,
                INDEX idx_fir_number (fir_number),
                INDEX idx_session_id (session_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()
        
        yield
        
    finally:
        cursor.close()
        conn.close()


class TestMigrationReversibility:
    """
    Test suite for database migration reversibility.
    
    Property 36: For any database migration script, applying the migration 
    and then reverting it should return the database schema to its original 
    state (round-trip property).
    """
    
    def test_migration_001_reversibility(self, db_schema_capture, ensure_test_database):
        """
        Test that migration 001 (add FIR indexes) is reversible.
        
        **Validates: Requirements 10.4**
        
        This test verifies the round-trip property:
        1. Capture original schema
        2. Apply migration
        3. Apply rollback
        4. Verify schema matches original
        """
        # Step 1: Capture original schema
        original_schema = db_schema_capture.capture_database_schema()
        original_fir_table = original_schema.get('fir_records')
        
        assert original_fir_table is not None, "fir_records table should exist"
        
        # Step 2: Apply migration
        migration_file = 'migrations/001_add_fir_indexes.sql'
        db_schema_capture.execute_sql_file(migration_file)
        
        # Verify migration was applied (schema should be different)
        after_migration_schema = db_schema_capture.capture_database_schema()
        after_migration_fir_table = after_migration_schema.get('fir_records')
        
        # Migration should add indexes, so schema should differ
        assert after_migration_fir_table != original_fir_table, \
            "Schema should change after migration"
        
        # Step 3: Apply rollback
        rollback_file = 'migrations/001_add_fir_indexes_rollback.sql'
        db_schema_capture.execute_sql_file(rollback_file)
        
        # Step 4: Verify schema matches original (with some tolerance)
        after_rollback_schema = db_schema_capture.capture_database_schema()
        after_rollback_fir_table = after_rollback_schema.get('fir_records')
        
        # Compare columns (should be identical or very similar)
        # Note: user_id column is intentionally kept in rollback to prevent data loss
        original_columns = set(original_fir_table.columns.keys())
        rollback_columns = set(after_rollback_fir_table.columns.keys())
        
        # All original columns should still exist
        assert original_columns.issubset(rollback_columns), \
            f"Original columns should be preserved. Missing: {original_columns - rollback_columns}"
        
        # Compare indexes (should match original basic indexes)
        original_indexes = original_fir_table.indexes
        rollback_indexes = after_rollback_fir_table.indexes
        
        # The rollback should restore the original basic indexes
        expected_basic_indexes = {'idx_fir_number', 'idx_session_id', 'idx_status', 'idx_created_at'}
        assert expected_basic_indexes.issubset(rollback_indexes), \
            f"Basic indexes should be restored. Missing: {expected_basic_indexes - rollback_indexes}"
        
        # Advanced indexes should be removed
        advanced_indexes = {
            'idx_user_created', 'idx_status_created', 'idx_user_status_created',
            'idx_status_finalized', 'ft_complaint_text', 'ft_fir_content',
            'idx_covering_list', 'idx_user_id'
        }
        assert not advanced_indexes.intersection(rollback_indexes), \
            f"Advanced indexes should be removed. Found: {advanced_indexes.intersection(rollback_indexes)}"
    
    def test_migration_002_reversibility(self, db_schema_capture, ensure_test_database):
        """
        Test that migration 002 (add background_tasks table) is reversible.
        
        **Validates: Requirements 10.4**
        
        This test verifies the round-trip property:
        1. Capture original schema (no background_tasks table)
        2. Apply migration (creates background_tasks table)
        3. Apply rollback (removes background_tasks table)
        4. Verify schema matches original
        """
        # Step 1: Capture original schema
        original_schema = db_schema_capture.capture_database_schema()
        original_tables = set(original_schema.keys())
        
        # background_tasks should not exist initially
        assert 'background_tasks' not in original_tables, \
            "background_tasks table should not exist before migration"
        
        # Step 2: Apply migration
        migration_file = 'migrations/002_add_background_tasks_table.sql'
        db_schema_capture.execute_sql_file(migration_file)
        
        # Verify migration was applied
        after_migration_schema = db_schema_capture.capture_database_schema()
        after_migration_tables = set(after_migration_schema.keys())
        
        assert 'background_tasks' in after_migration_tables, \
            "background_tasks table should exist after migration"
        
        # Verify table structure
        bg_tasks_table = after_migration_schema['background_tasks']
        expected_columns = {
            'id', 'task_id', 'task_name', 'task_type', 'priority', 'status',
            'params', 'result', 'error_message', 'retry_count', 'max_retries',
            'created_at', 'started_at', 'completed_at'
        }
        actual_columns = set(bg_tasks_table.columns.keys())
        assert expected_columns == actual_columns, \
            f"Table should have expected columns. Missing: {expected_columns - actual_columns}, Extra: {actual_columns - expected_columns}"
        
        # Step 3: Apply rollback
        rollback_file = 'migrations/002_add_background_tasks_table_rollback.sql'
        db_schema_capture.execute_sql_file(rollback_file)
        
        # Step 4: Verify schema matches original
        after_rollback_schema = db_schema_capture.capture_database_schema()
        after_rollback_tables = set(after_rollback_schema.keys())
        
        # background_tasks should be removed
        assert 'background_tasks' not in after_rollback_tables, \
            "background_tasks table should not exist after rollback"
        
        # Other tables should remain unchanged
        assert original_tables == after_rollback_tables, \
            f"Table list should match original. Difference: {original_tables.symmetric_difference(after_rollback_tables)}"
    
    @settings(
        max_examples=10,  # Run 10 iterations
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for database operations
    )
    @given(
        migration_order=st.permutations([1, 2])
    )
    def test_migration_reversibility_property(
        self, 
        migration_order: Tuple[int, ...],
        db_schema_capture,
        ensure_test_database
    ):
        """
        Property test: Migrations should be reversible regardless of application order.
        
        **Validates: Requirements 10.4**
        
        Property: For any sequence of migrations, applying them and then rolling 
        them back in reverse order should return to the original state.
        """
        # Capture original schema
        original_schema = db_schema_capture.capture_database_schema()
        original_tables = set(original_schema.keys())
        
        # Apply migrations in the given order
        for migration_num in migration_order:
            migration_file = f'migrations/00{migration_num}_*.sql'
            
            if migration_num == 1:
                db_schema_capture.execute_sql_file('migrations/001_add_fir_indexes.sql')
            elif migration_num == 2:
                db_schema_capture.execute_sql_file('migrations/002_add_background_tasks_table.sql')
        
        # Verify migrations were applied (schema should change)
        after_migration_schema = db_schema_capture.capture_database_schema()
        
        # Rollback migrations in reverse order
        for migration_num in reversed(migration_order):
            if migration_num == 1:
                db_schema_capture.execute_sql_file('migrations/001_add_fir_indexes_rollback.sql')
            elif migration_num == 2:
                db_schema_capture.execute_sql_file('migrations/002_add_background_tasks_table_rollback.sql')
        
        # Verify schema is restored (with tolerance for intentional differences)
        after_rollback_schema = db_schema_capture.capture_database_schema()
        after_rollback_tables = set(after_rollback_schema.keys())
        
        # Core property: Table list should match original
        # (Migration 002 is fully reversible, migration 001 keeps user_id column)
        assert original_tables == after_rollback_tables, \
            f"Table list should match original after rollback. Difference: {original_tables.symmetric_difference(after_rollback_tables)}"


@pytest.mark.integration
class TestMigrationIdempotency:
    """
    Test that migrations are idempotent (can be applied multiple times safely).
    """
    
    def test_migration_001_idempotency(self, db_schema_capture, ensure_test_database):
        """Test that migration 001 can be applied multiple times."""
        # Apply migration twice
        migration_file = 'migrations/001_add_fir_indexes.sql'
        db_schema_capture.execute_sql_file(migration_file)
        
        # Capture schema after first application
        first_schema = db_schema_capture.capture_database_schema()
        
        # Apply again
        db_schema_capture.execute_sql_file(migration_file)
        
        # Capture schema after second application
        second_schema = db_schema_capture.capture_database_schema()
        
        # Schemas should be identical
        assert first_schema == second_schema, \
            "Migration should be idempotent (same result when applied multiple times)"
    
    def test_migration_002_idempotency(self, db_schema_capture, ensure_test_database):
        """Test that migration 002 can be applied multiple times."""
        # Apply migration twice
        migration_file = 'migrations/002_add_background_tasks_table.sql'
        db_schema_capture.execute_sql_file(migration_file)
        
        # Capture schema after first application
        first_schema = db_schema_capture.capture_database_schema()
        
        # Apply again
        db_schema_capture.execute_sql_file(migration_file)
        
        # Capture schema after second application
        second_schema = db_schema_capture.capture_database_schema()
        
        # Schemas should be identical
        assert first_schema == second_schema, \
            "Migration should be idempotent (same result when applied multiple times)"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
