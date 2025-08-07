"""Admin API endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...dependencies import get_db, verify_admin_secret
from ...services.community_service import CommunityService
from ...services.announcement_service import AnnouncementService
from ... import schemas


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/announcements", dependencies=[Depends(verify_admin_secret)])
def create_new_announcement(
    announcement: schemas.AnnouncementCreate,
    db: Session = Depends(get_db)
):
    """Create a new announcement."""
    result = AnnouncementService.create_announcement(db, announcement)
    return JSONResponse(
        content=AnnouncementService.format_announcement_for_json(result),
        media_type="application/json; charset=utf-8"
    )


@router.put("/announcements/{announcement_id}/deactivate", dependencies=[Depends(verify_admin_secret)])
def deactivate_existing_announcement(
    announcement_id: int,
    db: Session = Depends(get_db)
):
    """Deactivate a specific announcement."""
    try:
        db_announcement = AnnouncementService.deactivate_announcement(db, announcement_id)
        return JSONResponse(
            content=AnnouncementService.format_announcement_for_json(db_announcement),
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
    updated_count = AnnouncementService.deactivate_all_announcements(db)
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
    result = CommunityService.initialize_default_categories(db)
    return result