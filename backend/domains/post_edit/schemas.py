"""Post-Edit domain schemas."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Import core schemas directly
from core.schemas import ValidationCase


class PostEditRequest(BaseModel):
    """Request schema for post-editing operations."""
    # Structured validation selection: per-segment boolean array
    # { [segmentIndex]: boolean[] }
    selected_cases: Optional[dict] = None
    # Optional per-case overrides for reason/recommendation
    # { [segmentIndex]: Array<{ reason?: string, recommend_korean_sentence?: string }> }
    modified_cases: Optional[dict] = None
    # Selection policy: when True, unspecified cases are treated as selected (default)
    default_select_all: bool = True
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    api_provider: Optional[str] = None
    vertex_project_id: Optional[str] = None
    vertex_location: Optional[str] = None
    vertex_service_account: Optional[str] = None


class PostEditSegment(BaseModel):
    """Individual segment in post-edit log."""
    segment_index: int
    was_edited: bool
    source_text: str
    original_translation: str
    edited_translation: str
    validation_status: str
    structured_cases: Optional[List[ValidationCase]] = None
    changes_made: Optional[Dict[str, Any]] = None
    

class StructuredPostEditLog(BaseModel):
    """Post-edit log with structured data from core."""
    summary: Dict[str, Any]
    segments: List[PostEditSegment]
    validation_cases_fixed: Optional[List[ValidationCase]] = None  # Cases that were fixed
    
    @classmethod
    def from_json_log(cls, log_data: Dict[str, Any]):
        """Create structured log from JSON file."""
        segments = [PostEditSegment(**seg) for seg in log_data.get('segments', [])]
        
        # Extract fixed validation cases
        fixed_cases = []
        for seg in segments:
            if seg.was_edited and seg.structured_cases:
                fixed_cases.extend(seg.structured_cases)
        
        return cls(
            summary=log_data.get('summary', {}),
            segments=segments,
            validation_cases_fixed=fixed_cases if fixed_cases else None
        )
