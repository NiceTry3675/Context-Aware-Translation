from sqlalchemy.orm import Session
from . import models, schemas, auth
from typing import Optional

# --- Helper functions for private content access control ---

def can_view_private_post(post: models.Post, current_user: Optional[models.User]) -> bool:
    """Check if user can view a private post"""
    if not post.is_private:
        return True
    if not current_user:
        return False
    # Author can view their own private post
    if post.author_id == current_user.id:
        return True
    # Admin can view any private post
    if auth.is_admin_sync(current_user):
        return True
    return False

def can_view_private_comment(comment: models.Comment, current_user: Optional[models.User]) -> bool:
    """Check if user can view a private comment"""
    if not comment.is_private:
        return True
    if not current_user:
        return False
    # 1. Comment author can view their own private comment
    if comment.author_id == current_user.id:
        return True
    # 2. Post author can view any private comment on their post
    # Ensure comment.post is loaded to prevent extra DB queries
    if comment.post and comment.post.author_id == current_user.id:
        return True
    # 3. Admin can view any private comment
    if auth.is_admin_sync(current_user):
        return True
    return False

def filter_private_posts(posts: list[models.Post], current_user: Optional[models.User]) -> list[models.Post]:
    """Filter out private posts that user cannot view"""
    return [post for post in posts if can_view_private_post(post, current_user)]

def filter_private_comments(comments: list[models.Comment], current_user: Optional[models.User]) -> list[models.Comment]:
    """Filter out private comments that user cannot view"""
    return [comment for comment in comments if can_view_private_comment(comment, current_user)]

def get_job(db: Session, job_id: int):
    return db.query(models.TranslationJob).filter(models.TranslationJob.id == job_id).first()

def get_jobs_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.TranslationJob).filter(
        models.TranslationJob.owner_id == user_id
    ).order_by(
        models.TranslationJob.created_at.desc()
    ).offset(skip).limit(limit).all()

def create_translation_job(db: Session, job: schemas.TranslationJobCreate):
    db_job = models.TranslationJob(filename=job.filename, owner_id=job.owner_id, status="PENDING", progress=0)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def update_job_status(db: Session, job_id: int, status: str, error_message: str | None = None):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = status
        if status == "COMPLETED":
            db_job.progress = 100
        elif status == "FAILED":
            db_job.progress = -1 # -1 to indicate an error state
            db_job.error_message = error_message
        db.commit()
        db.refresh(db_job)
    return db_job

def update_job_progress(db: Session, job_id: int, progress: int):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.progress = progress
        db.commit()
        db.refresh(db_job)
    return db_job

def update_job_filepath(db: Session, job_id: int, filepath: str):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.filepath = filepath
        db.commit()
        db.refresh(db_job)
    return db_job

def update_job_final_glossary(db: Session, job_id: int, glossary: dict):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.final_glossary = glossary
        db.commit()
        db.refresh(db_job)
    return db_job

def update_job_translation_segments(db: Session, job_id: int, segments: list):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.translation_segments = segments
        db.commit()
        db.refresh(db_job)
    return db_job


def update_job_validation_progress(db: Session, job_id: int, progress: int):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.validation_progress = progress
        db.commit()
        db.refresh(db_job)
    return db_job


def update_job_post_edit_progress(db: Session, job_id: int, progress: int):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.post_edit_progress = progress
        db.commit()
        db.refresh(db_job)
    return db_job


def create_translation_usage_log(db: Session, log_data: schemas.TranslationUsageLogCreate):
    db_log = models.TranslationUsageLog(**log_data.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

# Announcement CRUD functions

def get_active_announcement(db: Session) -> models.Announcement | None:
    return db.query(models.Announcement).filter(models.Announcement.is_active == True).order_by(models.Announcement.created_at.desc()).first()

def create_announcement(db: Session, announcement: schemas.AnnouncementCreate) -> models.Announcement:
    # Deactivate all other announcements first
    updated_count = db.query(models.Announcement).update({models.Announcement.is_active: False})
    print(f"🔇 {updated_count}개의 기존 공지를 비활성화했습니다.")
    
    db_announcement = models.Announcement(**announcement.dict())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    
    print(f"📢 새 공지 생성: ID {db_announcement.id}, 메시지: {db_announcement.message[:50]}...")
    return db_announcement

def deactivate_announcement(db: Session, announcement_id: int) -> models.Announcement | None:
    # 특정 공지 비활성화 (기존 동작 유지)
    db_announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
    if db_announcement:
        was_active = db_announcement.is_active
        db_announcement.is_active = False
        db.commit()
        db.refresh(db_announcement)
        
        if was_active:
            print(f"🔇 공지 비활성화: ID {announcement_id}")
        else:
            print(f"ℹ️ 이미 비활성화된 공지: ID {announcement_id}")
    else:
        print(f"❌ 공지를 찾을 수 없음: ID {announcement_id}")
        
    return db_announcement

def deactivate_all_announcements(db: Session) -> int:
    """모든 활성 공지를 비활성화합니다."""
    updated_count = db.query(models.Announcement).filter(models.Announcement.is_active == True).update({models.Announcement.is_active: False})
    db.commit()
    
    print(f"🔇 모든 공지 비활성화 완료: {updated_count}개의 공지가 비활성화되었습니다.")
    return updated_count

# --- User CRUD functions ---

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_clerk_id(db: Session, clerk_id: str):
    return db.query(models.User).filter(models.User.clerk_user_id == clerk_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(clerk_user_id=user.clerk_user_id, email=user.email, name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, clerk_id: str, user_update: schemas.UserUpdate):
    db_user = get_user_by_clerk_id(db, clerk_id)
    if db_user:
        update_data = user_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, clerk_id: str):
    db_user = get_user_by_clerk_id(db, clerk_id)
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

# --- Community Board CRUD functions ---

# PostCategory CRUD
def get_post_categories(db: Session):
    return db.query(models.PostCategory).order_by(models.PostCategory.order).all()

def create_post_category(db: Session, category: schemas.PostCategoryCreate):
    db_category = models.PostCategory(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def get_post_category_by_name(db: Session, name: str):
    return db.query(models.PostCategory).filter(models.PostCategory.name == name).first()

# Post CRUD
def get_posts(
    db: Session, 
    category_id: int = None, 
    skip: int = 0, 
    limit: int = 20,
    search: str = None
):
    from sqlalchemy.orm import joinedload
    
    query = db.query(models.Post).options(
        joinedload(models.Post.author),
        joinedload(models.Post.category)
    )
    
    if category_id:
        query = query.filter(models.Post.category_id == category_id)
    
    if search:
        query = query.filter(
            (models.Post.title.contains(search)) | 
            (models.Post.content.contains(search))
        )
    
    # Order by pinned first, then by created_at
    query = query.order_by(
        models.Post.is_pinned.desc(),
        models.Post.created_at.desc()
    )
    
    return query.offset(skip).limit(limit).all()

def get_post(db: Session, post_id: int):
    from sqlalchemy.orm import joinedload
    
    return db.query(models.Post).options(
        joinedload(models.Post.author),
        joinedload(models.Post.category),
        joinedload(models.Post.comments)
    ).filter(models.Post.id == post_id).first()

def create_post(db: Session, post: schemas.PostCreate, author_id: int):
    db_post = models.Post(**post.dict(), author_id=author_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def update_post(db: Session, post_id: int, post_update: schemas.PostUpdate):
    db_post = get_post(db, post_id)
    if db_post:
        update_data = post_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_post, key, value)
        db.commit()
        db.refresh(db_post)
    return db_post

def delete_post(db: Session, post_id: int):
    db_post = get_post(db, post_id)
    if db_post:
        db.delete(db_post)
        db.commit()
    return db_post

def increment_post_view_count(db: Session, post_id: int):
    db_post = get_post(db, post_id)
    if db_post:
        db_post.view_count += 1
        db.commit()
        db.refresh(db_post)
    return db_post

# Comment CRUD
def get_comments(db: Session, post_id: int):
    from sqlalchemy.orm import joinedload
    
    return db.query(models.Comment).options(
        joinedload(models.Comment.author),
        joinedload(models.Comment.post)  # Eagerly load the post relationship
    ).filter(
        models.Comment.post_id == post_id,
        models.Comment.parent_id == None  # Only top-level comments
    ).order_by(models.Comment.created_at).all()

def get_comment(db: Session, comment_id: int):
    from sqlalchemy.orm import joinedload
    
    return db.query(models.Comment).options(
        joinedload(models.Comment.author)
    ).filter(models.Comment.id == comment_id).first()

def create_comment(db: Session, comment: schemas.CommentCreate, author_id: int):
    db_comment = models.Comment(**comment.dict(), author_id=author_id)
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

def update_comment(db: Session, comment_id: int, comment_update: schemas.CommentUpdate):
    db_comment = get_comment(db, comment_id)
    if db_comment:
        db_comment.content = comment_update.content
        db.commit()
        db.refresh(db_comment)
    return db_comment

def delete_comment(db: Session, comment_id: int):
    db_comment = get_comment(db, comment_id)
    if db_comment:
        db.delete(db_comment)
        db.commit()
    return db_comment

def count_post_comments(db: Session, post_id: int):
    return db.query(models.Comment).filter(models.Comment.post_id == post_id).count()

def count_posts(db: Session, category_id: int = None, search: str = None) -> int:
    """Count posts with optional filtering, using an efficient COUNT query."""
    query = db.query(models.Post)
    if category_id:
        query = query.filter(models.Post.category_id == category_id)
    if search:
        query = query.filter(
            (models.Post.title.contains(search)) | 
            (models.Post.content.contains(search))
        )
    return query.count()

def get_comment_counts_for_posts(db: Session, post_ids: list[int]) -> dict[int, int]:
    """Get comment counts for a list of posts in a single query."""
    if not post_ids:
        return {}
    
    from sqlalchemy import func
    
    result = db.query(
        models.Comment.post_id,
        func.count(models.Comment.id).label('comment_count')
    ).filter(
        models.Comment.post_id.in_(post_ids)
    ).group_by(
        models.Comment.post_id
    ).all()
    
    return {post_id: count for post_id, count in result}
