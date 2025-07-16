import os
import sys
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

# Add backend path to sys.path to allow direct imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Now we can import from database
from database import SQLALCHEMY_DATABASE_URL

def add_resume_columns():
    """Inspects the database and adds resume-related columns if they don't exist."""
    print(f"Connecting to database: {SQLALCHEMY_DATABASE_URL}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)

    table_name = "translation_jobs"
    columns_to_add = {
        "last_successful_segment": "INTEGER DEFAULT 0",
        "context_snapshot_json": "TEXT DEFAULT '{}'"
    }

    try:
        print(f"Inspecting table: '{table_name}'")
        existing_columns = [col["name"] for col in inspector.get_columns(table_name)]
        print(f"Found existing columns: {existing_columns}")

        with engine.connect() as connection:
            for col_name, col_type in columns_to_add.items():
                if col_name not in existing_columns:
                    print(f"Column '{col_name}' not found. Adding it...")
                    # Use text() for cross-database compatibility of the query
                    # The ALTER TABLE syntax is standard SQL
                    connection.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}'))
                    print(f"Successfully added column: '{col_name}'")
                else:
                    print(f"Column '{col_name}' already exists. Skipping.")
            
            # For PostgreSQL, commit is implicit with execute. For others, it's good practice.
            # As we are using raw execute, we might need to handle transactions.
            # However, for simple DDL like ALTER TABLE, most DBs handle it atomically.
            # connection.commit() # This might be needed for some DB drivers

        print("\nDatabase migration check completed successfully.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the database is running and accessible.")

if __name__ == "__main__":
    add_resume_columns()
