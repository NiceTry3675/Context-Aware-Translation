"""
Validation schemas for structured output.

This module centralizes:
- Pydantic models for structured validation response
- JSON schema builder for the structured validation response (backward compatibility)
- Validation response wrapper model

Legacy/compatibility fields are removed. The schema is intentionally minimal and
stable for direct frontend consumption and post-edit automation.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field, model_validator


# --------------------
# Pydantic Models for Validation
# --------------------
class ValidationResult(BaseModel):
    """Represents the result of a translation validation (per segment)."""
    
    segment_index: int = Field(..., description="Index of the segment in the translation")
    source_text: str = Field(..., description="Original source text")
    translated_text: str = Field(..., description="Translated text")
    status: str = Field(default="PENDING", description="Validation status: PENDING, PASS, FAIL, or ERROR")
    structured_cases: Optional[List[ValidationCase]] = Field(default=None, description="List of validation issues found")

    def has_issues(self) -> bool:
        return bool(self.structured_cases and len(self.structured_cases) > 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dict for JSON serialization."""
        result: Dict[str, Any] = {
            'segment_index': self.segment_index,
            'status': self.status,
            'source_text': self.source_text,
            'translated_text': self.translated_text,
        }
        if self.structured_cases is not None:
            result['structured_cases'] = [case.model_dump() for case in self.structured_cases]
        return result
class ValidationCase(BaseModel):
    """Individual validation issue found in translation."""
    
    # Core fields (required)
    current_korean_sentence: str = Field(..., description="문제가 되는 현재 한국어 문장 (최대 1~2문장)")
    problematic_source_sentence: str = Field(..., description="대응하는 원문 문장 (최대 1~2문장)")
    reason: str = Field(..., description="왜 문제인지")
    dimension: Literal["completeness", "accuracy", "addition", "name_consistency", "dialogue_style", "flow", "other"] = Field(..., description="이슈 차원(카테고리)")
    severity: Literal["1", "2", "3"] = Field(..., description="이슈의 심각도. 1(사소함), 2(중대함), 3(치명적) 중 하나의 숫자로 표기.")
    recommend_korean_sentence: str = Field(..., description="권장 수정 번역문")
    
    # Optional fields
    tags: List[str] = Field(default_factory=list, description="보조 라벨(예: terminology, formality, punctuation)")

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_keys(cls, data: Any):
        """Accept legacy 'corrected_korean_sentence' as 'recommend_korean_sentence'."""
        if isinstance(data, dict):
            if (
                'recommend_korean_sentence' not in data
                and 'corrected_korean_sentence' in data
            ):
                data = dict(data)
                data['recommend_korean_sentence'] = data.pop('corrected_korean_sentence')
        return data


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


# --------------------
# Response schema (JSON Schema for Gemini) - Backward compatibility
# --------------------
def make_validation_response_schema() -> Dict[str, Any]:
    """
    Create JSON schema for validation response.
    
    Gemini Structured Output uses a simplified schema subset. Avoid unsupported
    keywords like minimum/maximum. Prefer enum or type-only constraints.
    """
    return {
        "type": "object",
        "properties": {
            "cases": {
                "type": "array",
                "description": "발견된 이슈 목록. 없으면 빈 배열.",
                "items": {
                    "type": "object",
                    "properties": {
                        # 핵심 필드(필수)
                        "current_korean_sentence": {
                            "type": "string",
                            "description": "문제가 되는 현재 한국어 문장 (최대 1~2문장)",
                        },
                        "problematic_source_sentence": {
                            "type": "string",
                            "description": "대응하는 원문 문장 (최대 1~2문장)",
                        },
                        "reason": {
                            "type": "string",
                            "description": "왜 문제인지",
                        },
                        "recommend_korean_sentence": {
                            "type": "string",
                            "description": "권장 수정 번역문",
                        },
                        # 차원(enum) – enum으로 직접 관리
                        "dimension": {
                            "type": "string",
                            "enum": [
                                "completeness",
                                "accuracy",
                                "addition",
                                "name_consistency",
                                "dialogue_style",
                                "flow",
                                "other",
                            ],
                            "description": "이슈 차원(카테고리)",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["1", "2", "3"],
                            "description": "이슈의 심각도. 1(사소함), 2(중대함), 3(치명적) 중 하나의 숫자로 표기.",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "보조 라벨(예: terminology, formality, punctuation)",
                        },
                    },
                    "required": [
                        "current_korean_sentence",
                        "problematic_source_sentence",
                        "recommend_korean_sentence",
                        "reason",
                        "dimension",
                        "severity",
                    ],
                },
            }
        },
        "required": ["cases"],
    }


# Legacy alias for backward compatibility
make_response_schema = make_validation_response_schema


# Re-export all items
__all__ = [
    "ValidationResult",
    "ValidationCase",
    "ValidationResponse",
    "make_validation_response_schema",
    "make_response_schema",  # Legacy alias
]