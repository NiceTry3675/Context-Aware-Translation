
from typing import List, Optional
import json

from sqlalchemy.orm import Session

from backend.domains.user.models import User
from backend.domains.community.models import Announcement
from backend.domains.user.schemas import AnnouncementCreate
from backend.domains.community.repository import AnnouncementRepository, SqlAlchemyAnnouncementRepository
from backend.domains.community.policy import Action, enforce_policy
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.config.database import SessionLocal
from backend.domains.community.exceptions import PermissionDeniedException, CommunityException

class AnnouncementService:
    def __init__(self, session: Session):
        self.session = session
        self.announcement_repo: AnnouncementRepository = SqlAlchemyAnnouncementRepository(session)

    def _create_session(self):
        """Create a new session for UoW transactions."""
        return SessionLocal()

    def get_announcements(self, active_only: bool = False, limit: int = 10) -> List[Announcement]:
        """Get announcements with optional filtering."""
        if active_only:
            return self.announcement_repo.get_active()
        else:
            return self.announcement_repo.list(limit=limit)

    def get_active_announcements(self) -> List[Announcement]:
        """Get only active announcements."""
        return self.announcement_repo.get_active()

    async def create_announcement(self, announcement_data: AnnouncementCreate, user: User) -> Announcement:
        try:
            enforce_policy(action=Action.CREATE, user=user, metadata={'resource_type': 'announcement'})
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(self._create_session) as uow:
            # Use UoW session for repository operations
            announcement_repo = SqlAlchemyAnnouncementRepository(uow.session)
            announcement = announcement_repo.create(
                message=announcement_data.message,
                is_active=announcement_data.is_active
            )
            uow.commit()
            return self.announcement_repo.get(announcement.id)

    async def delete_announcement(self, announcement_id: int, user: User) -> None:
        try:
            enforce_policy(action=Action.DELETE, user=user, metadata={'resource_type': 'announcement'})
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(self._create_session) as uow:
            announcement_repo = SqlAlchemyAnnouncementRepository(uow.session)
            announcement = announcement_repo.get(announcement_id)
            if not announcement:
                raise CommunityException(f"Announcement {announcement_id} not found")

            uow.session.delete(announcement)
            uow.commit()

    async def update_announcement(
        self,
        announcement_id: int,
        message: Optional[str] = None,
        is_active: Optional[bool] = None,
        user: User = None
    ) -> Announcement:
        """Update an announcement."""
        try:
            enforce_policy(action=Action.EDIT, user=user, metadata={'resource_type': 'announcement'})
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(self._create_session) as uow:
            announcement_repo = SqlAlchemyAnnouncementRepository(uow.session)
            announcement = announcement_repo.get(announcement_id)
            if not announcement:
                raise CommunityException(f"Announcement {announcement_id} not found")

            if message is not None:
                announcement.message = message
            if is_active is not None:
                announcement.is_active = is_active

            uow.commit()
            return self.announcement_repo.get(announcement.id)

    def deactivate_all_announcements(self) -> int:
        """Deactivate all active announcements."""
        return self.announcement_repo.deactivate_all()

    def get_active_announcement(self) -> Optional[Announcement]:
        """Get the currently active announcement."""
        active_announcements = self.announcement_repo.get_active()
        return active_announcements[0] if active_announcements else None

    def deactivate_announcement(self, announcement_id: int) -> Optional[Announcement]:
        """Deactivate a specific announcement."""
        announcement = self.announcement_repo.get(announcement_id)
        if not announcement:
            return None

        announcement.is_active = False
        return announcement

    @staticmethod
    def format_announcement_for_sse(announcement: Optional[Announcement], is_active: bool = True) -> str:
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
                "created_at": ""
            }

        json_str = json.dumps(announcement_data, ensure_ascii=False)
        return f"data: {json_str}\n\n"

    @staticmethod
    def format_announcement_for_json(announcement: Announcement) -> dict:
        """Format an announcement for JSON response."""
        return {
            "id": announcement.id,
            "message": announcement.message,
            "is_active": announcement.is_active,
            "created_at": announcement.created_at.isoformat()
        }

    def should_send_announcement_update(
        self,
        old_announcement: Optional[Announcement],
        new_announcement: Optional[Announcement]
    ) -> bool:
        """Determine if an announcement update should be sent."""
        # Send update if there's a new announcement or if announcement was deactivated
        if old_announcement is None and new_announcement is not None:
            return True
        if old_announcement is not None and new_announcement is None:
            return True
        if (old_announcement and new_announcement and
            old_announcement.message != new_announcement.message):
            return True
        return False
