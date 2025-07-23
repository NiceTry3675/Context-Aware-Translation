"""
자동 데이터베이스 마이그레이션 스크립트
Railway 배포 시 자동으로 필요한 컬럼들을 추가합니다.
"""
import logging
from sqlalchemy import text, inspect
from .database import engine

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def table_exists(inspector, table_name):
    """Check if a table exists."""
    return inspector.has_table(table_name)

def column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table."""
    if not table_exists(inspector, table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def run_migrations():
    """
    필요한 데이터베이스 마이그레이션을 실행합니다.
    SQLite와 PostgreSQL 모두와 호환됩니다.
    """
    # 먼저 모든 테이블 생성 (SQLAlchemy 모델 기반)
    try:
        from . import models
        logger.info("Creating all tables from models...")
        models.Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created successfully!")
    except Exception as e:
        logger.warning(f"⚠️ Table creation might have failed or tables already exist: {e}")

    # --- 마이그레이션 정의 ---
    migrations_to_run = [
        # Column additions
        {'type': 'add_column', 'table': 'posts', 'column': 'images', 'definition': "JSON DEFAULT '[]'"},
        {'type': 'add_column', 'table': 'posts', 'column': 'is_private', 'definition': 'BOOLEAN DEFAULT FALSE'},
        {'type': 'add_column', 'table': 'comments', 'column': 'is_private', 'definition': 'BOOLEAN DEFAULT FALSE'},
        {'type': 'add_column', 'table': 'users', 'column': 'role', 'definition': "VARCHAR(50) DEFAULT 'user'"},

        # Index creations (each as a separate statement)
        {'type': 'create_index', 'name': 'idx_posts_is_private', 'sql': 'CREATE INDEX IF NOT EXISTS idx_posts_is_private ON posts(is_private)'},
        {'type': 'create_index', 'name': 'idx_posts_category_created', 'sql': 'CREATE INDEX IF NOT EXISTS idx_posts_category_created ON posts(category_id, created_at DESC)'},
        {'type': 'create_index', 'name': 'idx_comments_post_id', 'sql': 'CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)'},
        {'type': 'create_index', 'name': 'idx_comments_is_private', 'sql': 'CREATE INDEX IF NOT EXISTS idx_comments_is_private ON comments(is_private)'},
    ]

    try:
        inspector = inspect(engine)
        with engine.connect() as connection:
            for migration in migrations_to_run:
                try:
                    if migration['type'] == 'add_column':
                        table = migration['table']
                        column = migration['column']
                        definition = migration['definition']
                        
                        if not column_exists(inspector, table, column):
                            logger.info(f"Running migration: Add column '{column}' to table '{table}'")
                            # Use a simple ALTER TABLE statement without IF NOT EXISTS
                            connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {definition}'))
                            connection.commit()
                            logger.info(f"✅ Completed: Add column '{column}' to table '{table}'")
                        else:
                            logger.info(f"✅ Skipped: Column '{column}' already exists in table '{table}'.")

                    elif migration['type'] == 'create_index':
                        name = migration['name']
                        sql = migration['sql']
                        logger.info(f"Running migration: Create index '{name}'")
                        # CREATE INDEX IF NOT EXISTS is compatible with both SQLite and PostgreSQL
                        connection.execute(text(sql))
                        connection.commit()
                        logger.info(f"✅ Completed: Create index '{name}'")

                except Exception as e:
                    logger.warning(f"⚠️ Migration '{migration.get('name') or migration.get('column')}' failed: {e}")
                    # Rollback transaction on error
                    if connection.in_transaction():
                        connection.rollback()

        logger.info("🎉 All migrations checked and applied successfully!")

    except Exception as e:
        logger.error(f"❌ A critical error occurred during the migration process: {e}")
        raise

if __name__ == "__main__":
    run_migrations()
