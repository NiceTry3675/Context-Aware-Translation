"""
자동 초기화 모듈
Railway 배포 시 필요한 초기 설정을 자동으로 수행합니다.
"""
import logging
from sqlalchemy.orm import Session
from . import models, crud
from .database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_categories():
    """기본 커뮤니티 카테고리 초기화"""
    try:
        with Session(engine) as db:
            # 기존 카테고리가 있는지 확인
            try:
                existing_categories = crud.get_post_categories(db)
                if existing_categories:
                    logger.info(f"✅ Categories already exist ({len(existing_categories)} found). Skipping initialization.")
                    return existing_categories
            except Exception as e:
                logger.warning(f"⚠️ Could not check existing categories: {e}. Proceeding with initialization...")

            # 기본 카테고리 데이터
            default_categories = [
                {
                    "name": "announcement",
                    "display_name": "📢 공지사항",
                    "description": "중요한 공지사항과 업데이트",
                    "is_admin_only": True,
                    "order": 1
                },
                {
                    "name": "suggestion",
                    "display_name": "💡 건의사항",
                    "description": "서비스 개선을 위한 제안과 아이디어",
                    "is_admin_only": False,
                    "order": 2
                },
                {
                    "name": "qna",
                    "display_name": "❓ Q&A",
                    "description": "질문과 답변, 사용법 문의",
                    "is_admin_only": False,
                    "order": 3
                },
                {
                    "name": "free",
                    "display_name": "💬 자유게시판",
                    "description": "자유로운 소통과 대화",
                    "is_admin_only": False,
                    "order": 4
                }
            ]

            created_categories = []
            for cat_data in default_categories:
                # schemas.PostCategoryCreate 사용
                from . import schemas
                category_create = schemas.PostCategoryCreate(**cat_data)
                category = crud.create_post_category(db, category_create)
                created_categories.append(category)
                logger.info(f"✅ Created category: {category.display_name}")

            logger.info(f"🎉 Successfully initialized {len(created_categories)} categories!")
            return created_categories

    except Exception as e:
        logger.error(f"❌ Failed to initialize categories: {e}")
        return []

def run_auto_init():
    """모든 자동 초기화 작업 실행"""
    logger.info("🚀 Starting auto initialization...")
    
    # 카테고리 초기화
    categories = init_categories()
    
    logger.info("✨ Auto initialization completed!")
    return {
        "categories": len(categories)
    }

if __name__ == "__main__":
    run_auto_init() 