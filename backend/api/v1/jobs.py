"""Translation job management API endpoints - thin router layer."""

from typing import List

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, Depends, Form, Response
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...models import User
from ...schemas import TranslationJob
from ...domains.translation.routes import TranslationRoutes

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=List[TranslationJob])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """List all translation jobs for the current user."""
    return TranslationRoutes.list_jobs(db, current_user, skip, limit)


@router.post("/jobs", response_model=TranslationJob)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite"),
    # Optional per-task model overrides
    translation_model_name: str | None = Form(None),
    style_model_name: str | None = Form(None),
    glossary_model_name: str | None = Form(None),
    style_data: str = Form(None),
    glossary_data: str = Form(None),
    segment_size: int = Form(15000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Create a new translation job."""
    return await TranslationRoutes.create_job(
        db=db,
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
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a translation job."""
    return TranslationRoutes.get_job(db, job_id)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Delete a translation job and its associated files."""
    await TranslationRoutes.delete_job(db, current_user, job_id)
    return Response(status_code=204)