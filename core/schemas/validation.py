"""
Validation schemas for structured output.

This module re-exports validation schemas from core.validation.structured
to maintain backward compatibility while centralizing schemas.
"""

from typing import Dict, Any

# Re-export from existing validation module
from ..validation.structured import (
    ValidationCase,
    make_response_schema as make_validation_response_schema,
)

# Create a ValidationResponse model for consistency
from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationResponse(BaseModel):
    """Response model for validation results."""
    
    cases: List[ValidationCase] = Field(
        default_factory=list,
        description="List of validation issues found. Empty list if no issues."
    )
    
    def has_issues(self) -> bool:
        """Check if there are any validation issues."""
        return len(self.cases) > 0
    
    def get_critical_issues(self) -> List[ValidationCase]:
        """Get only critical issues (severity 3)."""
        return [c for c in self.cases if c.severity == "3"]
    
    def get_issues_by_dimension(self, dimension: str) -> List[ValidationCase]:
        """Get issues filtered by dimension."""
        return [c for c in self.cases if c.dimension == dimension]


# Re-export all items
__all__ = [
    "ValidationCase",
    "ValidationResponse",
    "make_validation_response_schema",
]