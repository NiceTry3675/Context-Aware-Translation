"""Validation domain schemas."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Import core schemas directly
from core.schemas import (
    ValidationCase,
    ValidationResponse,
)


class ValidationRequest(BaseModel):
    """Request schema for validation operations."""
    quick_validation: bool = False
    validation_sample_rate: float = 1.0  # 0.0 to 1.0
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    api_provider: Optional[str] = None
    vertex_project_id: Optional[str] = None
    vertex_location: Optional[str] = None
    vertex_service_account: Optional[str] = None


class StructuredValidationReport(BaseModel):
    """Validation report with structured data from core schemas."""
    summary: Dict[str, Any]
    detailed_results: List[Dict[str, Any]]
    validation_response: Optional[ValidationResponse] = None  # Core schema
    
    @classmethod
    def from_validation_response(cls, response: ValidationResponse, summary: Dict, results: List):
        """Create report from core ValidationResponse"""
        return cls(
            summary=summary,
            detailed_results=results,
            validation_response=response
        )
