
from typing import List

from sqlalchemy.orm import Session

from backend.domains.user.models import User
from backend.domains.community.models import Announcement
from backend.domains.user.schemas import AnnouncementCreate
from backend.domains.community.repository import AnnouncementRepository, SqlAlchemyAnnouncementRepository
from backend.domains.community.policy import Action, enforce_policy
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.community.exceptions import PermissionDeniedException, CommunityException

class AnnouncementService:
    def __init__(self, session: Session):
        self.session = session
        self.announcement_repo: AnnouncementRepository = SqlAlchemyAnnouncementRepository(session)

    def get_active_announcements(self) -> List[Announcement]:
        return self.announcement_repo.get_active()

    async def create_announcement(self, announcement_data: AnnouncementCreate, user: User) -> Announcement:
        try:
            enforce_policy(action=Action.CREATE, user=user, metadata={'resource_type': 'announcement'})
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(lambda: self.session) as uow:
            announcement = self.announcement_repo.create(
                message=announcement_data.message,
                is_active=announcement_data.is_active
            )
            uow.commit()
            return announcement

    async def delete_announcement(self, announcement_id: int, user: User) -> None:
        try:
            enforce_policy(action=Action.DELETE, user=user, metadata={'resource_type': 'announcement'})
        except PermissionError as e:
            raise PermissionDeniedException(str(e))

        with SqlAlchemyUoW(lambda: self.session) as uow:
            announcement = self.announcement_repo.get(announcement_id)
            if not announcement:
                raise CommunityException(f"Announcement {announcement_id} not found")

            self.announcement_repo.delete(announcement_id)
            uow.commit()
