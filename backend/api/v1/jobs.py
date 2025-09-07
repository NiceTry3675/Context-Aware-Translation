"""Translation job management API endpoints - thin router layer."""

from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, Depends, Form, Response
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_required_user, is_admin
from backend.domains.user.models import User
from backend.domains.translation.schemas import TranslationJob
from backend.domains.translation.service import TranslationDomainService

router = APIRouter(tags=["jobs"])


def get_translation_service(db: Session = Depends(get_db)) -> TranslationDomainService:
    """Dependency injection for TranslationDomainService."""
    return TranslationDomainService(lambda: db)


@router.get("/jobs", response_model=List[TranslationJob])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
):
    """List all translation jobs for the current user."""
    return service.list_jobs(current_user.id, skip=skip, limit=limit)


@router.post("/jobs", response_model=TranslationJob)
def create_job(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    translation_model_name: Optional[str] = Form(None),
    style_model_name: Optional[str] = Form(None),
    glossary_model_name: Optional[str] = Form(None),
    style_data: Optional[str] = Form(None),
    glossary_data: Optional[str] = Form(None),
    segment_size: int = Form(15000),
    current_user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
):
    """Create a new translation job."""
    return service.create_job(
        user=current_user,
        file=file,
        api_key=api_key,
        model_name=model_name,
        translation_model_name=translation_model_name,
        style_model_name=style_model_name,
        glossary_model_name=glossary_model_name,
        style_data=style_data,
        glossary_data=glossary_data,
        segment_size=segment_size
    )


@router.get("/jobs/{job_id}", response_model=TranslationJob)
def get_job(
    job_id: int,
    service: TranslationDomainService = Depends(get_translation_service)
):
    """Get a translation job."""
    return service.get_job(job_id)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_required_user),
    service: TranslationDomainService = Depends(get_translation_service)
):
    """Delete a translation job and its associated files."""
    user_is_admin = await is_admin(current_user)
    service.delete_job(current_user, job_id, is_admin=user_is_admin)
    return Response(status_code=204)