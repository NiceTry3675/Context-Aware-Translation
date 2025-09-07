"""
Validation domain routes with business logic.

This module contains the business logic for validation operations,
separated from the API routing layer.
"""

import os
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.domains.user.models import User
from backend.domains.translation.models import TranslationJob
from backend.domains.translation.repository import SqlAlchemyTranslationJobRepository
from backend.domains.shared.model_factory import ModelAPIFactory
from backend.celery_tasks.validation import process_validation_task
from backend.auth import is_admin
from .schemas import ValidationRequest, StructuredValidationReport, ValidationResponse


class ValidationRoutes:
    """Business logic for validation-related operations."""
    
    @staticmethod
    async def trigger_validation(
        db: Session,
        user: User,
        job_id: int,
        request: ValidationRequest
    ):
        """
        Trigger validation on a completed translation job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            request: Validation request parameters
            
        Returns:
            Dict with message and job_id
            
        Raises:
            HTTPException: If job not found, not authorized, or invalid status
        """
        print(f"[VALIDATION API] Received validation request for job {job_id}")
        print(f"[VALIDATION API] User: {user.clerk_user_id if user else 'None'}")
        print(f"[VALIDATION API] Request params: quick={request.quick_validation}, rate={request.validation_sample_rate}")
        
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            print(f"[VALIDATION API] Job {job_id} not found")
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership or admin role
        user_is_admin = await is_admin(user)
        if not db_job.owner or (db_job.owner.clerk_user_id != user.clerk_user_id and not user_is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to validate this job")
        
        if db_job.status != "COMPLETED":
            raise HTTPException(status_code=400, detail=f"Can only validate completed jobs. Current status: {db_job.status}")
        
        # If an api_key is provided, ensure it's a Gemini-style key since validation uses Gemini Structured Output
        if request.api_key and not ModelAPIFactory.is_gemini_key(request.api_key):
            raise HTTPException(status_code=400, detail="Validation requires a Gemini API key (GEMINI Structured Output).")
        
        # Convert validation_sample_rate from 0-1 to 0-100 for storage
        validation_sample_rate_percent = int(request.validation_sample_rate * 100)
        
        # Update job with validation settings
        db_job.validation_enabled = True
        db_job.validation_status = "PENDING"
        db_job.quick_validation = request.quick_validation
        db_job.validation_sample_rate = validation_sample_rate_percent
        db.commit()
        
        # Start validation using Celery
        # Determine validation mode based on quick_validation flag
        validation_mode = "quick" if request.quick_validation else "comprehensive"
        
        process_validation_task.delay(
            job_id=job_id,
            api_key=request.api_key,
            model_name=request.model_name,
            validation_mode=validation_mode,
            sample_rate=validation_sample_rate_percent / 100.0,  # Convert percentage to decimal
            user_id=user.id
        )
        
        return {"message": "Validation started", "job_id": job_id}
    
    @staticmethod
    async def get_validation_report(
        db: Session,
        user: User,
        job_id: int,
        structured: bool = False
    ):
        """
        Get the validation report for a job.
        
        Args:
            db: Database session
            user: Current user
            job_id: Job ID
            structured: If True, returns a StructuredValidationReport
            
        Returns:
            Either raw JSON report or StructuredValidationReport
            
        Raises:
            HTTPException: If job not found, not authorized, or report not available
        """
        print(f"--- [API] Getting validation report for job {job_id} ---")
        repo = SqlAlchemyTranslationJobRepository(db)
        db_job = repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check ownership or admin role
        user_is_admin = await is_admin(user)
        if not db_job.owner or (db_job.owner.clerk_user_id != user.clerk_user_id and not user_is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to access this validation report")
        
        if db_job.validation_status != "COMPLETED":
            print(f"--- [API] Validation not completed. Status: {db_job.validation_status} ---")
            raise HTTPException(status_code=400, detail=f"Validation not completed. Current status: {db_job.validation_status}")
        
        print(f"--- [API] Validation report path: {db_job.validation_report_path} ---")
        if not db_job.validation_report_path or not os.path.exists(db_job.validation_report_path):
            print(f"--- [API] Report not found at path: {db_job.validation_report_path} ---")
            raise HTTPException(status_code=404, detail="Validation report not found")
        
        # Read and return the JSON report
        with open(db_job.validation_report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        print(f"--- [API] Successfully loaded validation report with {len(report.get('detailed_results', []))} results ---")
        
        # If structured response requested, parse and return StructuredValidationReport
        if structured:
            # Extract all validation cases from detailed results
            all_cases = []
            for result in report.get('detailed_results', []):
                cases = result.get('structured_cases', [])
                if not cases and result.get('validation_result'):
                    cases = result['validation_result'].get('structured_cases', [])
                if cases:
                    all_cases.extend(cases)
            
            # Create ValidationResponse from cases
            validation_response = ValidationResponse(cases=all_cases)
            
            # Return structured report
            return StructuredValidationReport.from_validation_response(
                response=validation_response,
                summary=report.get('summary', {}),
                results=report.get('detailed_results', [])
            )
        
        # Default: return raw report
        return report