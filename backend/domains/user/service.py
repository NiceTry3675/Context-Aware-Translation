"""User domain service layer with business logic."""

import json
from typing import List, Optional, Protocol
from datetime import datetime
import hashlib
import hmac

from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.user import User
from backend.models.translation import TranslationJob, TranslationUsageLog
from backend.models.community import Announcement
from backend.schemas.user import (
    UserResponse,
    UserUpdate,
    AnnouncementCreate,
    AnnouncementResponse,
    UsageLogResponse
)
from backend.domains.user.repository import UserRepository, SqlAlchemyUserRepository
from backend.domains.shared.uow import SqlAlchemyUoW
from backend.domains.shared.events import DomainEvent
from backend.config.settings import get_settings


# Domain Events
class UserCreatedEvent(DomainEvent):
    """Event raised when a new user is created."""
    
    def __init__(self, user_id: int, clerk_user_id: str, email: Optional[str]):
        super().__init__(event_type="user.created")
        self.user_id = user_id
        self.clerk_user_id = clerk_user_id
        self.email = email


class UserUpdatedEvent(DomainEvent):
    """Event raised when a user is updated."""
    
    def __init__(self, user_id: int, changes: dict):
        super().__init__(event_type="user.updated")
        self.user_id = user_id
        self.changes = changes


class UserRoleChangedEvent(DomainEvent):
    """Event raised when a user's role is changed."""
    
    def __init__(self, user_id: int, old_role: str, new_role: str):
        super().__init__(event_type="user.role_changed")
        self.user_id = user_id
        self.old_role = old_role
        self.new_role = new_role


class UserService:
    """Service layer for user domain operations."""
    
    def __init__(self, session: Session):
        """Initialize with database session."""
        self.session = session
        self.user_repo = SqlAlchemyUserRepository(session)
        self.settings = get_settings()
    
    # User operations
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User database ID
            
        Returns:
            User instance or None if not found
        """
        return self.user_repo.get(user_id)
    
    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """
        Get a user by Clerk user ID.
        
        Args:
            clerk_user_id: Clerk user identifier
            
        Returns:
            User instance or None if not found
        """
        return self.user_repo.get_by_clerk_id(clerk_user_id)
    
    async def create_or_update_user(
        self,
        clerk_user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> User:
        """
        Create or update a user from external data.
        
        Args:
            clerk_user_id: Clerk user identifier
            email: User email address
            name: User display name
            metadata: Additional metadata
            
        Returns:
            Created or updated user
        """
        async with SqlAlchemyUoW(self.session) as uow:
            existing_user = self.user_repo.get_by_clerk_id(clerk_user_id)
            is_new = existing_user is None
            
            user = self.user_repo.create_or_update_from_clerk(
                clerk_user_id=clerk_user_id,
                email=email,
                name=name
            )
            
            # Store metadata if provided
            if metadata:
                if not user.metadata:
                    user.metadata = {}
                user.metadata.update(metadata)
            
            await uow.flush()
            
            # Raise appropriate event
            if is_new:
                uow.add_event(UserCreatedEvent(
                    user_id=user.id,
                    clerk_user_id=clerk_user_id,
                    email=email
                ))
            else:
                changes = {}
                if existing_user.email != email:
                    changes['email'] = (existing_user.email, email)
                if existing_user.name != name:
                    changes['name'] = (existing_user.name, name)
                
                if changes:
                    uow.add_event(UserUpdatedEvent(
                        user_id=user.id,
                        changes=changes
                    ))
            
            await uow.commit()
            return user
    
    async def update_user_role(
        self,
        user_id: int,
        new_role: str,
        admin_user: User
    ) -> User:
        """
        Update a user's role.
        
        Args:
            user_id: ID of user to update
            new_role: New role (admin/user)
            admin_user: User performing the update (must be admin)
            
        Returns:
            Updated user
            
        Raises:
            PermissionError: If admin_user is not an admin
            ValueError: If user not found or invalid role
        """
        if admin_user.role != "admin":
            raise PermissionError("Only admins can change user roles")
        
        if new_role not in ["admin", "user"]:
            raise ValueError(f"Invalid role: {new_role}")
        
        async with SqlAlchemyUoW(self.session) as uow:
            user = self.user_repo.get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            old_role = user.role
            if old_role != new_role:
                success = self.user_repo.update_role(user_id, new_role)
                if success:
                    uow.add_event(UserRoleChangedEvent(
                        user_id=user_id,
                        old_role=old_role,
                        new_role=new_role
                    ))
                    await uow.commit()
                    
                    # Refresh user to get updated data
                    self.session.refresh(user)
            
            return user
    
    def get_user_statistics(self, user_id: int) -> dict:
        """
        Get comprehensive statistics for a user.
        
        Args:
            user_id: User database ID
            
        Returns:
            Dictionary with user statistics
        """
        stats = self.user_repo.get_user_statistics(user_id)
        
        # Add additional statistics from other tables
        user = self.user_repo.get(user_id)
        if user:
            # Count translation jobs
            job_count = self.session.query(TranslationJob).filter(
                TranslationJob.user_id == user_id
            ).count()
            
            # Count API usage
            usage_count = self.session.query(TranslationUsageLog).filter(
                TranslationUsageLog.user_id == user_id
            ).count()
            
            # Get total tokens used
            total_tokens = self.session.query(
                func.sum(TranslationUsageLog.total_tokens)
            ).filter(
                TranslationUsageLog.user_id == user_id
            ).scalar() or 0
            
            stats.update({
                'translation_job_count': job_count,
                'api_usage_count': usage_count,
                'total_tokens_used': total_tokens
            })
        
        return stats
    
    def search_users(
        self,
        query: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 20
    ) -> List[User]:
        """
        Search for users.
        
        Args:
            query: Search query for name/email
            role: Filter by role
            limit: Maximum results
            
        Returns:
            List of matching users
        """
        if query:
            users = self.user_repo.search_by_name_or_email(query, limit)
        else:
            users = self.session.query(User).limit(limit).all()
        
        # Filter by role if specified
        if role:
            users = [u for u in users if u.role == role]
        
        return users
    
    def is_admin(self, user: Optional[User]) -> bool:
        """
        Check if a user has admin privileges.
        
        Args:
            user: User to check
            
        Returns:
            True if user is an admin, False otherwise
        """
        if not user:
            return False
        return user.role == "admin"
    
    # Clerk webhook handling
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        headers: dict
    ) -> bool:
        """
        Verify Clerk webhook signature.
        
        Args:
            payload: Raw webhook payload
            headers: Request headers
            
        Returns:
            True if signature is valid
        """
        signing_secret = self.settings.clerk_webhook_secret
        if not signing_secret:
            # If no secret configured, skip verification (dev only)
            return self.settings.app_env == "development"
        
        signature = headers.get('svix-signature')
        if not signature:
            return False
        
        # Clerk uses Svix for webhooks
        # The signature format is: v1,signature
        parts = signature.split(' ')
        for part in parts:
            if part.startswith('v1,'):
                expected_sig = part[3:]  # Remove 'v1,' prefix
                break
        else:
            return False
        
        # Compute expected signature
        timestamp = headers.get('svix-timestamp', '')
        msg_id = headers.get('svix-id', '')
        
        signed_content = f"{msg_id}.{timestamp}.{payload.decode('utf-8')}"
        computed_sig = hmac.new(
            signing_secret.encode('utf-8'),
            signed_content.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(computed_sig, expected_sig)
    
    async def handle_clerk_webhook(
        self,
        event_type: str,
        data: dict
    ) -> Optional[User]:
        """
        Handle Clerk webhook events.
        
        Args:
            event_type: Type of webhook event
            data: Event data
            
        Returns:
            User if relevant, None otherwise
        """
        if event_type == "user.created":
            return await self._handle_user_created(data)
        elif event_type == "user.updated":
            return await self._handle_user_updated(data)
        elif event_type == "user.deleted":
            return await self._handle_user_deleted(data)
        else:
            # Ignore other event types
            return None
    
    async def _handle_user_created(self, data: dict) -> User:
        """Handle user.created webhook event."""
        user_data = data.get("data", {})
        return await self.create_or_update_user(
            clerk_user_id=user_data.get("id"),
            email=self._extract_email(user_data),
            name=self._extract_name(user_data),
            metadata={'clerk_created_at': user_data.get("created_at")}
        )
    
    async def _handle_user_updated(self, data: dict) -> User:
        """Handle user.updated webhook event."""
        user_data = data.get("data", {})
        return await self.create_or_update_user(
            clerk_user_id=user_data.get("id"),
            email=self._extract_email(user_data),
            name=self._extract_name(user_data),
            metadata={'clerk_updated_at': user_data.get("updated_at")}
        )
    
    async def _handle_user_deleted(self, data: dict) -> None:
        """Handle user.deleted webhook event."""
        user_data = data.get("data", {})
        clerk_user_id = user_data.get("id")
        
        if clerk_user_id:
            user = self.user_repo.get_by_clerk_id(clerk_user_id)
            if user:
                # Soft delete or mark as inactive
                user.metadata = user.metadata or {}
                user.metadata['deleted_at'] = datetime.utcnow().isoformat()
                self.session.commit()
    
    @staticmethod
    def _extract_email(clerk_data: dict) -> Optional[str]:
        """Extract primary email from Clerk user data."""
        email_addresses = clerk_data.get("email_addresses", [])
        primary_email_id = clerk_data.get("primary_email_address_id")
        
        for email_obj in email_addresses:
            if email_obj.get("id") == primary_email_id:
                return email_obj.get("email_address")
        
        # Fallback to first email if no primary
        if email_addresses:
            return email_addresses[0].get("email_address")
        
        return None
    
    @staticmethod
    def _extract_name(clerk_data: dict) -> Optional[str]:
        """Extract full name from Clerk user data."""
        first_name = clerk_data.get("first_name", "")
        last_name = clerk_data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        return full_name or None
    
    # Usage tracking
    
    def get_user_usage_logs(
        self,
        user_id: int,
        limit: int = 100
    ) -> List[TranslationUsageLog]:
        """
        Get API usage logs for a user.
        
        Args:
            user_id: User database ID
            limit: Maximum logs to return
            
        Returns:
            List of usage logs
        """
        from sqlalchemy import desc
        
        return self.session.query(TranslationUsageLog).filter(
            TranslationUsageLog.user_id == user_id
        ).order_by(
            desc(TranslationUsageLog.created_at)
        ).limit(limit).all()
    
    def get_usage_summary(
        self,
        user_id: int,
        days: int = 30
    ) -> dict:
        """
        Get usage summary for a user.
        
        Args:
            user_id: User database ID
            days: Number of days to look back
            
        Returns:
            Dictionary with usage summary
        """
        from sqlalchemy import func
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.session.query(
            func.count(TranslationUsageLog.id).label('total_requests'),
            func.sum(TranslationUsageLog.total_tokens).label('total_tokens'),
            func.sum(TranslationUsageLog.prompt_tokens).label('total_prompt_tokens'),
            func.sum(TranslationUsageLog.completion_tokens).label('total_completion_tokens'),
            func.avg(TranslationUsageLog.total_tokens).label('avg_tokens_per_request')
        ).filter(
            TranslationUsageLog.user_id == user_id,
            TranslationUsageLog.created_at >= cutoff_date
        )
        
        result = query.first()
        
        return {
            'period_days': days,
            'total_requests': result.total_requests or 0,
            'total_tokens': result.total_tokens or 0,
            'total_prompt_tokens': result.total_prompt_tokens or 0,
            'total_completion_tokens': result.total_completion_tokens or 0,
            'avg_tokens_per_request': float(result.avg_tokens_per_request or 0)
        }
    
    # Announcement operations (admin only)
    
    def get_announcements(
        self,
        active_only: bool = True,
        limit: int = 10
    ) -> List[Announcement]:
        """
        Get announcements.
        
        Args:
            active_only: Only return active announcements
            limit: Maximum announcements to return
            
        Returns:
            List of announcements
        """
        query = self.session.query(Announcement)
        
        if active_only:
            query = query.filter(Announcement.is_active == True)
        
        return query.order_by(
            desc(Announcement.created_at)
        ).limit(limit).all()
    
    async def create_announcement(
        self,
        message: str,
        is_active: bool,
        admin_user: User
    ) -> Announcement:
        """
        Create a new announcement.
        
        Args:
            message: Announcement message
            is_active: Whether announcement is active
            admin_user: User creating the announcement (must be admin)
            
        Returns:
            Created announcement
            
        Raises:
            PermissionError: If user is not an admin
        """
        if not self.is_admin(admin_user):
            raise PermissionError("Only admins can create announcements")
        
        async with SqlAlchemyUoW(self.session) as uow:
            announcement = Announcement(
                message=message,
                is_active=is_active,
                created_at=datetime.utcnow()
            )
            self.session.add(announcement)
            await uow.commit()
            return announcement
    
    async def update_announcement(
        self,
        announcement_id: int,
        message: Optional[str],
        is_active: Optional[bool],
        admin_user: User
    ) -> Announcement:
        """
        Update an announcement.
        
        Args:
            announcement_id: ID of announcement to update
            message: New message (optional)
            is_active: New active status (optional)
            admin_user: User updating the announcement (must be admin)
            
        Returns:
            Updated announcement
            
        Raises:
            PermissionError: If user is not an admin
            ValueError: If announcement not found
        """
        if not self.is_admin(admin_user):
            raise PermissionError("Only admins can update announcements")
        
        async with SqlAlchemyUoW(self.session) as uow:
            announcement = self.session.query(Announcement).get(announcement_id)
            if not announcement:
                raise ValueError(f"Announcement {announcement_id} not found")
            
            if message is not None:
                announcement.message = message
            if is_active is not None:
                announcement.is_active = is_active
            
            await uow.commit()
            return announcement
    
    async def delete_announcement(
        self,
        announcement_id: int,
        admin_user: User
    ) -> None:
        """
        Delete an announcement.
        
        Args:
            announcement_id: ID of announcement to delete
            admin_user: User deleting the announcement (must be admin)
            
        Raises:
            PermissionError: If user is not an admin
            ValueError: If announcement not found
        """
        if not self.is_admin(admin_user):
            raise PermissionError("Only admins can delete announcements")
        
        async with SqlAlchemyUoW(self.session) as uow:
            announcement = self.session.query(Announcement).get(announcement_id)
            if not announcement:
                raise ValueError(f"Announcement {announcement_id} not found")
            
            self.session.delete(announcement)
            await uow.commit()
    
    # SSE support methods for announcements
    
    def get_active_announcement(self) -> Optional[Announcement]:
        """Get the currently active announcement."""
        return self.session.query(Announcement).filter(
            Announcement.is_active == True
        ).order_by(desc(Announcement.created_at)).first()
    
    def deactivate_announcement(self, announcement_id: int) -> Optional[Announcement]:
        """Deactivate a specific announcement."""
        announcement = self.session.query(Announcement).filter(
            Announcement.id == announcement_id
        ).first()
        
        if not announcement:
            raise ValueError("Announcement not found")
        
        announcement.is_active = False
        self.session.commit()
        return announcement
    
    def deactivate_all_announcements(self) -> int:
        """Deactivate all active announcements."""
        count = self.session.query(Announcement).filter(
            Announcement.is_active == True
        ).update({"is_active": False})
        self.session.commit()
        return count
    
    @staticmethod
    def format_announcement_for_sse(
        announcement: Optional[Announcement],
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
    def format_announcement_for_json(announcement: Announcement) -> dict:
        """Format an announcement for JSON response."""
        return {
            "id": announcement.id,
            "message": announcement.message,
            "is_active": announcement.is_active,
            "created_at": announcement.created_at.isoformat()
        }
    
    @staticmethod
    def should_send_announcement_update(
        current: Optional[Announcement],
        last_sent: Optional[Announcement]
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


# Import sqlalchemy func for usage summary
from sqlalchemy import func