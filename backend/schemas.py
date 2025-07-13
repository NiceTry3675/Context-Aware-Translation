from pydantic import BaseModel
import datetime

class TranslationJobBase(BaseModel):
    filename: str

class TranslationJobCreate(TranslationJobBase):
    pass

class TranslationJob(TranslationJobBase):
    id: int
    status: str
    progress: int
    created_at: datetime.datetime
    completed_at: datetime.datetime | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True

class TranslationUsageLogBase(BaseModel):
    job_id: int
    original_length: int
    translated_length: int
    translation_duration_seconds: int
    model_used: str
    error_type: str | None = None

class TranslationUsageLogCreate(TranslationUsageLogBase):
    pass

class TranslationUsageLog(TranslationUsageLogBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class AnnouncementBase(BaseModel):
    message: str
    is_active: bool = True

class AnnouncementCreate(AnnouncementBase):
    pass

class Announcement(AnnouncementBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True
