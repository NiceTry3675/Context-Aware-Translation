"""Admin API endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...dependencies import get_db, verify_admin_secret
from ...domains.community.service import CommunityService
from ...domains.user.service import UserService
from ... import schemas


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/announcements", dependencies=[Depends(verify_admin_secret)])
async def create_new_announcement(
    announcement: schemas.AnnouncementCreate,
    db: Session = Depends(get_db)
):
    """Create a new announcement."""
    service = UserService(db)
    # Deactivate all other announcements first
    service.deactivate_all_announcements()
    # Create the new announcement as an admin user (using system admin context)
    from ...models import Announcement
    db_announcement = Announcement(**announcement.dict())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    return JSONResponse(
        content=UserService.format_announcement_for_json(db_announcement),
        media_type="application/json; charset=utf-8"
    )


@router.put("/announcements/{announcement_id}/deactivate", dependencies=[Depends(verify_admin_secret)])
def deactivate_existing_announcement(
    announcement_id: int,
    db: Session = Depends(get_db)
):
    """Deactivate a specific announcement."""
    try:
        service = UserService(db)
        db_announcement = service.deactivate_announcement(announcement_id)
        return JSONResponse(
            content=UserService.format_announcement_for_json(db_announcement),
            media_type="application/json; charset=utf-8"
        )
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"detail": str(e)},
            media_type="application/json; charset=utf-8"
        )


@router.put("/announcements/deactivate-all", dependencies=[Depends(verify_admin_secret)])
def deactivate_all_announcements(db: Session = Depends(get_db)):
    """Deactivate all active announcements."""
    service = UserService(db)
    updated_count = service.deactivate_all_announcements()
    return JSONResponse(
        content={
            "message": f"모든 공지가 비활성화되었습니다.",
            "deactivated_count": updated_count,
            "success": True
        },
        media_type="application/json; charset=utf-8"
    )


@router.post("/community/init-categories", dependencies=[Depends(verify_admin_secret)])
def initialize_categories(db: Session = Depends(get_db)):
    """Initialize default post categories."""
    from ...models import PostCategory
    from ...domains.community.repository import PostCategoryRepository
    
    default_categories = [
        {"name": "notice", "display_name": "공지사항", "description": "중요한 공지사항", "is_admin_only": True, "order": 1},
        {"name": "suggestion", "display_name": "건의사항", "description": "서비스 개선을 위한 제안", "is_admin_only": False, "order": 2},
        {"name": "qna", "display_name": "Q&A", "description": "질문과 답변", "is_admin_only": False, "order": 3},
        {"name": "free", "display_name": "자유게시판", "description": "자유로운 소통 공간", "is_admin_only": False, "order": 4}
    ]
    
    created_categories = []
    category_repo = PostCategoryRepository(db)
    for cat_data in default_categories:
        existing = category_repo.get_by_name(cat_data["name"])
        if not existing:
            category = PostCategory(**cat_data)
            db.add(category)
            db.commit()
            db.refresh(category)
            created_categories.append(category)
    
    return {
        "message": f"Created {len(created_categories)} categories",
        "categories": created_categories
    }