#!/usr/bin/env python3
"""
Database migration script to add post-editing columns to translation_jobs table.
This script adds the missing columns that were introduced for post-editing functionality.
"""

import sqlite3
import sys
from datetime import datetime

def backup_database():
    """Create a backup of the database before migration."""
    import shutil
    backup_name = f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    try:
        shutil.copy2("database.db", backup_name)
        print(f"Database backed up to {backup_name}")
        return backup_name
    except Exception as e:
        print(f"Failed to backup database: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def add_column_if_not_exists(cursor, table_name, column_name, column_definition):
    """Add a column to a table if it doesn't already exist."""
    if not check_column_exists(cursor, table_name, column_name):
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
            print(f"  Added column {column_name}")
            return True
        except sqlite3.OperationalError as e:
            print(f"  Failed to add column {column_name}: {e}")
            return False
    else:
        print(f"  - Column {column_name} already exists")
        return True

def migrate_database():
    """Add missing post-editing columns to the translation_jobs table."""
    print('\n=== Database Migration: Adding Post-Edit Columns ===\n')
    
    # Backup first
    backup_file = backup_database()
    if not backup_file:
        response = input("Failed to backup database. Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Migration aborted.")
            return False
    
    try:
        # Connect to database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        print('\nAdding missing columns to translation_jobs table:')
        
        # List of columns to add with their definitions
        columns_to_add = [
            ("validation_enabled", "BOOLEAN DEFAULT 0"),
            ("validation_status", "VARCHAR"),
            ("validation_progress", "INTEGER DEFAULT 0"),
            ("validation_sample_rate", "INTEGER DEFAULT 100"),
            ("quick_validation", "BOOLEAN DEFAULT 0"),
            ("validation_report_path", "VARCHAR"),
            ("validation_completed_at", "TIMESTAMP"),
            ("post_edit_enabled", "BOOLEAN DEFAULT 0"),
            ("post_edit_status", "VARCHAR"),
            ("post_edit_progress", "INTEGER DEFAULT 0"),
            ("post_edit_log_path", "VARCHAR"),
            ("post_edit_completed_at", "TIMESTAMP"),
            ("final_glossary", "JSON"),
            ("owner_id", "INTEGER REFERENCES users(id)"),
            ("segment_size", "INTEGER DEFAULT 15000")
        ]
        
        # Add each column if it doesn't exist
        success = True
        for column_name, column_def in columns_to_add:
            if not add_column_if_not_exists(cursor, "translation_jobs", column_name, column_def):
                success = False
        
        if success:
            # Commit changes
            conn.commit()
            print('\nMigration completed successfully!')
            
            # Verify the schema
            cursor.execute("PRAGMA table_info(translation_jobs)")
            columns = cursor.fetchall()
            print(f'\nTable now has {len(columns)} columns')
            
        else:
            print('\nSome columns failed to add. Rolling back...')
            conn.rollback()
            
        conn.close()
        return success
        
    except Exception as e:
        print(f'\nMigration failed: {e}')
        if backup_file:
            print(f"You can restore from backup: {backup_file}")
        return False

if __name__ == "__main__":
    if migrate_database():
        print("\n=== Migration Complete ===")
        print("You can now restart the backend server.")
        sys.exit(0)
    else:
        print("\n=== Migration Failed ===")
        print("Please check the error messages above.")
        sys.exit(1)
