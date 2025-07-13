from sqlalchemy.orm import Session
from . import models, schemas

def get_job(db: Session, job_id: int):
    return db.query(models.TranslationJob).filter(models.TranslationJob.id == job_id).first()

def create_translation_job(db: Session, job: schemas.TranslationJobCreate):
    db_job = models.TranslationJob(filename=job.filename, status="PENDING", progress=0)
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
    db.query(models.Announcement).update({models.Announcement.is_active: False})
    db_announcement = models.Announcement(**announcement.dict())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    return db_announcement

def deactivate_announcement(db: Session, announcement_id: int) -> models.Announcement | None:
    db_announcement = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
    if db_announcement:
        db_announcement.is_active = False
        db.commit()
        db.refresh(db_announcement)
    return db_announcement
