from typing import Protocol, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.domains.user.models import User
from backend.domains.shared.repository import SqlAlchemyRepository


class UserRepository(Protocol):
    """Protocol for User repository operations."""
    
    def get(self, id: int) -> Optional[User]:
        """Get a user by ID."""
        ...
    
    def get_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """Get a user by Clerk user ID."""
        ...
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        ...
    
    def create_or_update_from_clerk(
        self,
        clerk_user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None
    ) -> User:
        """Create or update a user from Clerk webhook data."""
        ...
    
    def update_role(self, id: int, role: str) -> bool:
        """Update a user's role (admin/user)."""
        ...
    
    def list_admins(self) -> List[User]:
        """Get all users with admin role."""
        ...
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user has admin role."""
        ...


class SqlAlchemyUserRepository(SqlAlchemyRepository[User]):
    """SQLAlchemy implementation of UserRepository with Clerk integration."""
    
    def __init__(self, session: Session):
        """Initialize with a SQLAlchemy session."""
        super().__init__(session, User)
    
    def get_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """Get a user by Clerk user ID."""
        return self.session.query(User).filter(
            User.clerk_user_id == clerk_user_id
        ).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        return self.session.query(User).filter(
            User.email == email
        ).first()
    
    def create_or_update_from_clerk(
        self,
        clerk_user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None
    ) -> User:
        """
        Create or update a user from Clerk webhook data.
        
        This method is typically called from the Clerk webhook handler
        when a user signs up or updates their profile.
        """
        user = self.get_by_clerk_id(clerk_user_id)
        
        if user:
            # Update existing user
            if email is not None:
                user.email = email
            if name is not None:
                user.name = name
            user.updated_at = datetime.utcnow()
        else:
            # Create new user
            user = User(
                clerk_user_id=clerk_user_id,
                email=email,
                name=name,
                role="user",  # Default role
                created_at=datetime.utcnow()
            )
            self.session.add(user)
        
        self.session.flush()
        return user
    
    def update_role(self, id: int, role: str) -> bool:
        """
        Update a user's role.
        
        Args:
            id: User ID
            role: New role (should be 'admin' or 'user')
            
        Returns:
            True if successful, False if user not found
        """
        if role not in ["admin", "user"]:
            raise ValueError(f"Invalid role: {role}. Must be 'admin' or 'user'")
        
        user = self.get(id)
        if user:
            user.role = role
            user.updated_at = datetime.utcnow()
            self.session.flush()
            return True
        return False
    
    def list_admins(self) -> List[User]:
        """Get all users with admin role."""
        return self.session.query(User).filter(
            User.role == "admin"
        ).order_by(User.created_at).all()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user has admin role."""
        user = self.get(user_id)
        return user is not None and user.role == "admin"
    
    def get_recent_users(self, limit: int = 10) -> List[User]:
        """Get recently created users."""
        return self.session.query(User).order_by(
            desc(User.created_at)
        ).limit(limit).all()
    
    def search_by_name_or_email(self, query: str, limit: int = 20) -> List[User]:
        """Search users by name or email."""
        search_pattern = f"%{query}%"
        return self.session.query(User).filter(
            (User.name.ilike(search_pattern)) | 
            (User.email.ilike(search_pattern))
        ).limit(limit).all()
    
    def get_user_statistics(self, user_id: int) -> dict:
        """
        Get statistics for a user.
        
        Returns:
            Dictionary with user statistics like job count, post count, etc.
        """
        user = self.get(user_id)
        if not user:
            return {}
        
        # These counts would be more efficient with dedicated count queries
        # but for now we'll use the relationship counts
        return {
            "job_count": len(user.jobs) if user.jobs else 0,
            "post_count": len(user.posts) if user.posts else 0,
            "comment_count": len(user.comments) if user.comments else 0,
            "created_at": user.created_at,
            "role": user.role,
        }
    
    def sync_with_clerk(self, clerk_data: dict) -> User:
        """
        Sync user data from Clerk webhook payload.
        
        Args:
            clerk_data: Dictionary containing Clerk user data
                Expected keys: id, email_addresses, first_name, last_name
        
        Returns:
            Updated or created User instance
        """
        clerk_user_id = clerk_data.get("id")
        if not clerk_user_id:
            raise ValueError("Missing Clerk user ID in webhook data")
        
        # Extract email (Clerk provides array of email addresses)
        email_addresses = clerk_data.get("email_addresses", [])
        primary_email = None
        for email_obj in email_addresses:
            if email_obj.get("id") == clerk_data.get("primary_email_address_id"):
                primary_email = email_obj.get("email_address")
                break
        
        # If no primary email, use the first one
        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get("email_address")
        
        # Extract name
        first_name = clerk_data.get("first_name", "")
        last_name = clerk_data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or None
        
        return self.create_or_update_from_clerk(
            clerk_user_id=clerk_user_id,
            email=primary_email,
            name=full_name
        )