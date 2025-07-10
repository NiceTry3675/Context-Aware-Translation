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

def update_job_status(db: Session, job_id: int, status: str):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = status
        if status == "COMPLETED":
            db_job.progress = 100
        elif status == "FAILED":
            db_job.progress = -1 # -1 to indicate an error state
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