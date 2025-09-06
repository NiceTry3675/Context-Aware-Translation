import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# Railway에서 제공하는 DATABASE_URL을 환경 변수에서 가져옵니다.
# 만약 환경 변수가 없다면, 로컬 개발을 위해 기본 SQLite 경로를 사용합니다.
# Use absolute path to ensure consistency regardless of where the app is started
import pathlib
project_root = pathlib.Path(__file__).parent.parent
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{project_root}/database.db")

# 데이터베이스 엔진 생성
# connect_args는 SQLite에만 필요한 옵션이므로, PostgreSQL 연결 시에는 제거합니다.
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from the shared domain models
from .domains.shared.models.base import Base