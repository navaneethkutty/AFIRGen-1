"""
Database migration runner for AFIRGen backend.

This module provides utilities to apply and rollback database migrations.
Supports MySQL database with proper error handling and transaction management.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import mysql.connector
from mysql.connector import Error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migration execution and rollback."""
    
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 3306
    ):
        """
        Initialize migration runner with database connection details.
        
        Args:
            host: Database host
            user: Database user
            password: Database password
            database: Database name
            port: Database port (default: 3306)
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection: Optional[mysql.connector.MySQLConnection] = None
    
    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                autocommit=False  # Use transactions for safety
            )
            logger.info(f"Connected to database: {self.database}")
        except Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")
    
    def execute_migration_file(self, file_path: Path, rollback: bool = False) -> bool:
        """
        Execute a migration SQL file.
        
        Args:
            file_path: Path to the SQL migration file
            rollback: Whether this is a rollback operation
        
        Returns:
            True if successful, False otherwise
        """
        if not file_path.exists():
            logger.error(f"Migration file not found: {file_path}")
            return False
        
        try:
            # Read SQL file
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split into individual statements (handle multi-statement SQL)
            statements = self._split_sql_statements(sql_content)
            
            cursor = self.connection.cursor()
            
            try:
                for i, statement in enumerate(statements, 1):
                    statement = statement.strip()
                    if not statement or statement.startswith('--'):
                        continue
                    
                    logger.info(f"Executing statement {i}/{len(statements)}")
                    logger.debug(f"SQL: {statement[:100]}...")
                    
                    cursor.execute(statement)
                
                # Commit transaction
                self.connection.commit()
                
                action = "Rollback" if rollback else "Migration"
                logger.info(f"{action} completed successfully: {file_path.name}")
                return True
                
            except Error as e:
                # Rollback on error
                self.connection.rollback()
                logger.error(f"Migration failed, rolled back transaction: {e}")
                logger.error(f"Failed statement: {statement[:200]}")
                return False
            finally:
                cursor.close()
                
        except Exception as e:
            logger.error(f"Error reading migration file: {e}")
            return False
    
    def _split_sql_statements(self, sql_content: str) -> list[str]:
        """
        Split SQL content into individual statements.
        
        Args:
            sql_content: Raw SQL content
        
        Returns:
            List of SQL statements
        """
        # Simple split by semicolon (doesn't handle all edge cases but works for our migrations)
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue
            
            current_statement.append(line)
            
            # Check if statement ends with semicolon
            if line.endswith(';'):
                statements.append(' '.join(current_statement))
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statements.append(' '.join(current_statement))
        
        return statements
    
    def apply_migration(self, migration_name: str) -> bool:
        """
        Apply a migration by name.
        
        Args:
            migration_name: Name of the migration file (without .sql extension)
        
        Returns:
            True if successful, False otherwise
        """
        migrations_dir = Path(__file__).parent
        migration_file = migrations_dir / f"{migration_name}.sql"
        
        logger.info(f"Applying migration: {migration_name}")
        return self.execute_migration_file(migration_file, rollback=False)
    
    def rollback_migration(self, migration_name: str) -> bool:
        """
        Rollback a migration by name.
        
        Args:
            migration_name: Name of the migration file (without _rollback.sql extension)
        
        Returns:
            True if successful, False otherwise
        """
        migrations_dir = Path(__file__).parent
        rollback_file = migrations_dir / f"{migration_name}_rollback.sql"
        
        logger.info(f"Rolling back migration: {migration_name}")
        return self.execute_migration_file(rollback_file, rollback=True)


def main():
    """Main entry point for migration runner CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration runner')
    parser.add_argument('action', choices=['apply', 'rollback'], help='Action to perform')
    parser.add_argument('migration', help='Migration name (e.g., 001_add_fir_indexes)')
    parser.add_argument('--host', default=os.getenv('DB_HOST', 'localhost'), help='Database host')
    parser.add_argument('--port', type=int, default=int(os.getenv('DB_PORT', '3306')), help='Database port')
    parser.add_argument('--user', default=os.getenv('DB_USER', 'root'), help='Database user')
    parser.add_argument('--password', default=os.getenv('DB_PASSWORD', ''), help='Database password')
    parser.add_argument('--database', default=os.getenv('DB_NAME', 'afirgen'), help='Database name')
    
    args = parser.parse_args()
    
    # Create migration runner
    runner = MigrationRunner(
        host=args.host,
        user=args.user,
        password=args.password,
        database=args.database,
        port=args.port
    )
    
    try:
        # Connect to database
        runner.connect()
        
        # Execute action
        if args.action == 'apply':
            success = runner.apply_migration(args.migration)
        else:  # rollback
            success = runner.rollback_migration(args.migration)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Migration runner failed: {e}")
        sys.exit(1)
    finally:
        runner.disconnect()


if __name__ == '__main__':
    main()
