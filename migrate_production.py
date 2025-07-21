"""
Railway 프로덕션 환경 데이터베이스 마이그레이션
독립적으로 실행 가능한 스크립트
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수가 없으면 .env 파일 로드
if not os.environ.get("DATABASE_URL"):
    from dotenv import load_dotenv
    load_dotenv()

from backend.migrations import run_migrations

def main():
    """메인 마이그레이션 실행 함수"""
    print("🚂 Railway 프로덕션 환경 마이그레이션 시작...")
    print(f"📍 DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')[:50]}...")
    
    try:
        run_migrations()
        print("✅ 마이그레이션 완료!")
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 