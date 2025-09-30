from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .settings import get_settings

# Get database URL from centralized settings
settings = get_settings()
SQLALCHEMY_DATABASE_URL = settings.database_url

# 데이터베이스 엔진 생성
# connect_args는 SQLite에만 필요한 옵션이므로, PostgreSQL 연결 시에는 제거합니다.
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # PostgreSQL with connection pooling for production
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_pre_ping=settings.pool_pre_ping,
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from the shared domain models
from ..domains.shared.db_base import Base