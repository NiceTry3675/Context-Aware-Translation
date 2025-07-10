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

    class Config:
        from_attributes = True
