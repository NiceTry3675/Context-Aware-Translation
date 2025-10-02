"""Export domain schemas."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import datetime


class ExportRequest(BaseModel):
    """Base export request schema."""
    format: str
    job_id: int


class PDFExportRequest(ExportRequest):
    """PDF export request with specific options."""
    format: Literal["pdf"] = "pdf"
    include_source: bool = True
    include_illustrations: bool = True
    page_size: Literal["A4", "Letter"] = "A4"


class DownloadRequest(BaseModel):
    """Download request for job outputs."""
    job_id: int
    format: Optional[str] = None  # Auto-detect from job


class LogDownloadRequest(BaseModel):
    """Log download request."""
    job_id: int
    log_type: Literal["prompts", "context"]


class GlossaryDownloadRequest(BaseModel):
    """Glossary download request."""
    job_id: int
    structured: bool = False


class SegmentDownloadRequest(BaseModel):
    """Segment download request."""
    job_id: int
    offset: int = 0
    limit: int = 3


class ContentDownloadRequest(BaseModel):
    """Content download request for raw translation content."""
    job_id: int
    include_source: bool = True


class ExportResponse(BaseModel):
    """Base export response."""
    success: bool
    message: Optional[str] = None
    file_path: Optional[str] = None
    filename: Optional[str] = None
    media_type: Optional[str] = None


class SegmentResponse(BaseModel):
    """Response for segment data."""
    segments: List[Dict[str, Any]]
    total_count: int
    offset: int
    limit: int
    has_more: bool


class ContentResponse(BaseModel):
    """Response for job content."""
    job_id: int
    filename: str
    content: str
    source_content: Optional[str] = None
    completed_at: Optional[str] = None