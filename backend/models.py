from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    role = Column(String, default="user")  # "user" or "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    jobs = relationship("TranslationJob", back_populates="owner")
    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="author")

class TranslationJob(Base):
    __tablename__ = "translation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    status = Column(String, default="PENDING")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    error_message = Column(String, nullable=True)
    filepath = Column(String, nullable=True)

    # --- Add these lines ---
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Start as nullable for existing jobs
    owner = relationship("User", back_populates="jobs")
    final_glossary = Column(JSON, nullable=True)
    # -----------------------
    
    # Validation and Post-Edit fields
    validation_enabled = Column(Boolean, default=False)
    validation_status = Column(String, nullable=True)  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    validation_progress = Column(Integer, default=0)  # Progress percentage 0-100
    validation_sample_rate = Column(Integer, default=100)  # Percentage 0-100
    quick_validation = Column(Boolean, default=False)
    validation_report_path = Column(String, nullable=True)
    validation_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    post_edit_enabled = Column(Boolean, default=False)
    post_edit_status = Column(String, nullable=True)  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    post_edit_progress = Column(Integer, default=0) # Progress percentage 0-100
    post_edit_log_path = Column(String, nullable=True)
    post_edit_completed_at = Column(DateTime(timezone=True), nullable=True)

class TranslationUsageLog(Base):
    __tablename__ = "translation_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("translation_jobs.id"), index=True)
    original_length = Column(Integer)
    translated_length = Column(Integer)
    translation_duration_seconds = Column(Integer)
    model_used = Column(String)
    error_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Community Board Models
class PostCategory(Base):
    __tablename__ = "post_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "notice", "suggestion", "qna", "free"
    display_name = Column(String, nullable=False)  # e.g., "공지사항", "건의사항", "Q&A", "자유게시판"
    description = Column(String, nullable=True)
    is_admin_only = Column(Boolean, default=False)  # Only admin can post
    order = Column(Integer, default=0)  # Display order
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    posts = relationship("Post", back_populates="category")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("post_categories.id"), nullable=False)
    is_pinned = Column(Boolean, default=False)  # Pinned posts appear at the top
    is_private = Column(Boolean, default=False)  # Private posts visible only to author and admin
    view_count = Column(Integer, default=0)
    images = Column(JSON, default=list)  # Store image URLs as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    author = relationship("User", back_populates="posts")
    category = relationship("PostCategory", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)  # For nested comments
    is_private = Column(Boolean, default=False)  # Private comments visible only to author and admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    parent = relationship("Comment", remote_side=[id])
    replies = relationship("Comment", back_populates="parent", cascade="all, delete-orphan")
