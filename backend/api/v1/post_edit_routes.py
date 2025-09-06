"""Post-edit API endpoints - thin router layer."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...domains.user.models import User
from ...domains.post_edit.schemas import PostEditRequest
from ...domains.post_edit.routes import PostEditRoutes

router = APIRouter(tags=["post-edit"])


@router.put("/jobs/{job_id}/post-edit")
async def trigger_post_edit(
    job_id: int,
    request: PostEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Trigger post-editing on a validated translation job."""
    return await PostEditRoutes.trigger_post_edit(db, current_user, job_id, request)


@router.get("/jobs/{job_id}/post-edit-log", response_model=None)
async def get_post_edit_log(
    job_id: int,
    structured: bool = False,  # Optional parameter to return structured response
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Get the post-edit log for a job."""
    return await PostEditRoutes.get_post_edit_log(db, current_user, job_id, structured)