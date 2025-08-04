"""
자동 데이터베이스 마이그레이션 스크립트
Railway 배포 시 자동으로 필요한 컬럼들을 추가합니다.
"""
import logging
import time
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError
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
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            # --- 기존 마이그레이션 로직 시작 ---
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
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'owner_id', 'definition': 'VARCHAR(255)'},
                {'type': 'add_column', 'table': 'posts', 'column': 'images', 'definition': "JSON DEFAULT '[]'"},
                {'type': 'add_column', 'table': 'posts', 'column': 'is_private', 'definition': 'BOOLEAN DEFAULT FALSE'},
                {'type': 'add_column', 'table': 'comments', 'column': 'is_private', 'definition': 'BOOLEAN DEFAULT FALSE'},
                {'type': 'add_column', 'table': 'users', 'column': 'role', 'definition': "VARCHAR(50) DEFAULT 'user'"},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'final_glossary', 'definition': 'JSON'},
                
                # Validation and Post-Edit columns
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'validation_enabled', 'definition': 'BOOLEAN DEFAULT FALSE'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'validation_status', 'definition': 'VARCHAR(50)'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'validation_progress', 'definition': 'INTEGER DEFAULT 0'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'validation_sample_rate', 'definition': 'INTEGER DEFAULT 100'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'quick_validation', 'definition': 'BOOLEAN DEFAULT FALSE'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'validation_report_path', 'definition': 'VARCHAR(500)'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'validation_completed_at', 'definition': 'TIMESTAMP'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'post_edit_enabled', 'definition': 'BOOLEAN DEFAULT FALSE'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'post_edit_status', 'definition': 'VARCHAR(50)'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'post_edit_log_path', 'definition': 'VARCHAR(500)'},
                {'type': 'add_column', 'table': 'translation_jobs', 'column': 'post_edit_completed_at', 'definition': 'TIMESTAMP'},

                # Index creations (each as a separate statement)
                {'type': 'create_index', 'name': 'idx_posts_is_private', 'sql': 'CREATE INDEX IF NOT EXISTS idx_posts_is_private ON posts(is_private)'},
                {'type': 'create_index', 'name': 'idx_posts_category_created', 'sql': 'CREATE INDEX IF NOT EXISTS idx_posts_category_created ON posts(category_id, created_at DESC)'},
                {'type': 'create_index', 'name': 'idx_comments_post_id', 'sql': 'CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)'},
                {'type': 'create_index', 'name': 'idx_comments_is_private', 'sql': 'CREATE INDEX IF NOT EXISTS idx_comments_is_private ON comments(is_private)'},
            ]

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
                                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {definition}'))
                                connection.commit()
                                logger.info(f"✅ Completed: Add column '{column}' to table '{table}'")
                            else:
                                logger.info(f"✅ Skipped: Column '{column}' already exists in table '{table}'.")

                        elif migration['type'] == 'create_index':
                            name = migration['name']
                            sql = migration['sql']
                            logger.info(f"Running migration: Create index '{name}'")
                            connection.execute(text(sql))
                            connection.commit()
                            logger.info(f"✅ Completed: Create index '{name}'")

                    except Exception as e:
                        logger.warning(f"⚠️ Migration '{migration.get('name') or migration.get('column')}' failed: {e}")
                        if connection.in_transaction():
                            connection.rollback()

            logger.info("🎉 All migrations checked and applied successfully!")
            return  # 성공 시 루프 종료

        except OperationalError as e:
            logger.warning(f"DB connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("❌ All DB connection attempts failed.")
                raise
        except Exception as e:
            logger.error(f"❌ A critical error occurred during the migration process: {e}")
            raise

if __name__ == "__main__":
    run_migrations()
