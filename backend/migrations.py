"""
자동 데이터베이스 마이그레이션 스크립트
Railway 배포 시 자동으로 필요한 컬럼들을 추가합니다.
"""
from sqlalchemy import text
from .database import engine
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """필요한 데이터베이스 마이그레이션을 실행합니다."""
    
    # 먼저 모든 테이블 생성 (SQLAlchemy 모델 기반)
    try:
        from . import models
        logger.info("Creating all tables from models...")
        models.Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created successfully!")
    except Exception as e:
        logger.warning(f"⚠️ Table creation failed or already exists: {e}")
    
    migrations = [
        # 이미지 업로드 기능을 위한 images 컬럼 추가
        {
            "name": "Add images column to posts",
            "sql": """
                ALTER TABLE posts 
                ADD COLUMN IF NOT EXISTS images JSON DEFAULT '[]';
            """
        },
        
        # 비밀글 기능을 위한 is_private 컬럼 추가
        {
            "name": "Add is_private column to posts", 
            "sql": """
                ALTER TABLE posts 
                ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;
            """
        },
        
        # 비밀댓글 기능을 위한 is_private 컬럼 추가
        {
            "name": "Add is_private column to comments",
            "sql": """
                ALTER TABLE comments 
                ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;
            """
        },
        
        # 사용자 역할 관리를 위한 role 컬럼 추가
        {
            "name": "Add role column to users",
            "sql": """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';
            """
        },
        
        # 인덱스 추가 (성능 최적화)
        {
            "name": "Add indexes for performance",
            "sql": """
                CREATE INDEX IF NOT EXISTS idx_posts_is_private ON posts(is_private);
                CREATE INDEX IF NOT EXISTS idx_posts_category_created ON posts(category_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
                CREATE INDEX IF NOT EXISTS idx_comments_is_private ON comments(is_private);
            """
        }
    ]
    
    try:
        with engine.connect() as connection:
            for migration in migrations:
                logger.info(f"Running migration: {migration['name']}")
                try:
                    connection.execute(text(migration['sql']))
                    connection.commit()
                    logger.info(f"✅ Completed: {migration['name']}")
                except Exception as e:
                    logger.warning(f"⚠️ Migration '{migration['name']}' failed or already applied: {e}")
                    
        logger.info("🎉 All migrations completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migrations() 