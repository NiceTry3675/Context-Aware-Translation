import json
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from .. import crud, models, schemas


class AnnouncementService:
    """Service layer for announcement operations."""
    
    @staticmethod
    def get_active_announcement(db: Session) -> Optional[models.Announcement]:
        """Get the currently active announcement."""
        return crud.get_active_announcement(db)
    
    @staticmethod
    def create_announcement(
        db: Session,
        announcement: schemas.AnnouncementCreate
    ) -> models.Announcement:
        """Create a new announcement."""
        return crud.create_announcement(db=db, announcement=announcement)
    
    @staticmethod
    def deactivate_announcement(
        db: Session,
        announcement_id: int
    ) -> Optional[models.Announcement]:
        """Deactivate a specific announcement."""
        db_announcement = crud.deactivate_announcement(db, announcement_id)
        if not db_announcement:
            raise ValueError("Announcement not found")
        return db_announcement
    
    @staticmethod
    def deactivate_all_announcements(db: Session) -> int:
        """Deactivate all active announcements."""
        return crud.deactivate_all_announcements(db)
    
    @staticmethod
    def format_announcement_for_sse(
        announcement: Optional[models.Announcement],
        is_active: bool = True
    ) -> str:
        """Format an announcement for Server-Sent Events (SSE)."""
        if announcement:
            announcement_data = {
                "id": announcement.id,
                "message": announcement.message,
                "is_active": is_active and announcement.is_active,
                "created_at": announcement.created_at.isoformat()
            }
        else:
            # Return empty announcement
            announcement_data = {
                "id": None,
                "message": "",
                "is_active": False,
                "created_at": datetime.now().isoformat()
            }
        
        json_str = json.dumps(announcement_data, ensure_ascii=False)
        return f"data: {json_str}\n\n"
    
    @staticmethod
    def format_announcement_for_json(announcement: models.Announcement) -> dict:
        """Format an announcement for JSON response."""
        return {
            "id": announcement.id,
            "message": announcement.message,
            "is_active": announcement.is_active,
            "created_at": announcement.created_at.isoformat()
        }
    
    @staticmethod
    def should_send_announcement_update(
        current: Optional[models.Announcement],
        last_sent: Optional[models.Announcement]
    ) -> bool:
        """Determine if an announcement update should be sent."""
        # If one is None and the other isn't, send update
        if (current is None) != (last_sent is None):
            return True
        
        # If both exist, check for changes
        if current and last_sent:
            return (
                current.id != last_sent.id or
                current.message != last_sent.message or
                current.is_active != last_sent.is_active
            )
        
        # Both are None, no update needed
        return False