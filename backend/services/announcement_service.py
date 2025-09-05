import json
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from .. import models, schemas
from ..domains.community.repository import SqlAlchemyAnnouncementRepository


class AnnouncementService:
    """Service layer for announcement operations."""
    
    @staticmethod
    def get_active_announcement(db: Session) -> Optional[models.Announcement]:
        """Get the currently active announcement."""
        repo = SqlAlchemyAnnouncementRepository(db)
        active = repo.get_active()
        return active[0] if active else None
    
    @staticmethod
    def create_announcement(
        db: Session,
        announcement: schemas.AnnouncementCreate
    ) -> models.Announcement:
        """Create a new announcement."""
        repo = SqlAlchemyAnnouncementRepository(db)
        # Deactivate all other announcements first
        db.query(models.Announcement).update({models.Announcement.is_active: False})
        db_announcement = models.Announcement(**announcement.dict())
        db.add(db_announcement)
        db.commit()
        db.refresh(db_announcement)
        return db_announcement
    
    @staticmethod
    def deactivate_announcement(
        db: Session,
        announcement_id: int
    ) -> Optional[models.Announcement]:
        """Deactivate a specific announcement."""
        repo = SqlAlchemyAnnouncementRepository(db)
        db_announcement = repo.get(announcement_id)
        if not db_announcement:
            raise ValueError("Announcement not found")
        db_announcement.is_active = False
        db.commit()
        db.refresh(db_announcement)
        return db_announcement
    
    @staticmethod
    def deactivate_all_announcements(db: Session) -> int:
        """Deactivate all active announcements."""
        updated_count = db.query(models.Announcement).filter(models.Announcement.is_active == True).update({models.Announcement.is_active: False})
        db.commit()
        return updated_count
    
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