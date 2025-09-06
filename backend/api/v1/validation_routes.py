"""Validation API endpoints - thin router layer."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...dependencies import get_db, get_required_user
from ...domains.user.models import User
from ...domains.validation.schemas import ValidationRequest
from ...domains.validation import get_validation_routes

router = APIRouter(tags=["validation"])


@router.put("/jobs/{job_id}/validation")
async def trigger_validation(
    job_id: int,
    request: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Trigger validation on a completed translation job."""
    ValidationRoutes = get_validation_routes()
    return await ValidationRoutes.trigger_validation(db, current_user, job_id, request)


@router.get("/jobs/{job_id}/validation-report", response_model=None)
async def get_validation_report(
    job_id: int,
    structured: bool = False,  # Optional parameter to return structured response
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user)
):
    """Get the validation report for a job."""
    ValidationRoutes = get_validation_routes()
    return await ValidationRoutes.get_validation_report(db, current_user, job_id, structured)