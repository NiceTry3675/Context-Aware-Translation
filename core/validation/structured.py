"""
Structured validation utilities for Gemini Structured Output (EN → KO validation).

This module centralizes:
- Pydantic models for structured validation response
- JSON schema builder for the structured validation response (backward compatibility)
- Minimal helpers used by the validator

Legacy/compatibility fields are removed. The schema is intentionally minimal and
stable for direct frontend consumption and post-edit automation.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field


# --------------------
# Pydantic Models for Validation
# --------------------
class ValidationCase(BaseModel):
    """Individual validation issue found in translation."""
    
    # Core fields (required)
    current_korean_sentence: str = Field(..., description="문제가 되는 현재 한국어 문장")
    problematic_source_sentence: str = Field(..., description="대응하는 원문 문장")
    reason: str = Field(..., description="왜 문제인지")
    dimension: Literal[
        "completeness",
        "accuracy",
        "addition",
        "name_consistency",
        "dialogue_style",
        "flow",
        "other"
    ] = Field(..., description="이슈 차원(카테고리)")
    severity: int = Field(..., ge=1, le=3, description="이슈의 심각도. 1(사소함), 2(중대함), 3(치명적) 중 하나의 숫자로 표기.")
    
    # Optional fields
    corrected_korean_sentence: Optional[str] = Field(None, description="권장 수정 번역문")
    tags: List[str] = Field(default_factory=list, description="보조 라벨(예: terminology, formality, punctuation)")


class ValidationResponse(BaseModel):
    """Complete validation response containing all found issues."""
    
    cases: List[ValidationCase] = Field(
        default_factory=list,
        description="발견된 이슈 목록. 없으면 빈 배열."
    )


# --------------------
# Response schema (JSON Schema for Gemini) - Backward compatibility
# --------------------
def make_response_schema() -> Dict[str, Any]:
    # Gemini Structured Output uses a simplified schema subset. Avoid unsupported
    # keywords like minimum/maximum. Prefer enum or type-only constraints.
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
                            "description": "문제가 되는 현재 한국어 문장",
                        },
                        "problematic_source_sentence": {
                            "type": "string",
                            "description": "대응하는 원문 문장",
                        },
                        "reason": {
                            "type": "string",
                            "description": "왜 문제인지",
                        },
                        "corrected_korean_sentence": {
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
                            "type": "integer",
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
                        "reason",
                        "dimension",
                        "severity",
                    ],
                },
            }
        },
        "required": ["cases"],
    }


# (Removed) Prompt builder – we now exclusively use prompts.yaml via PromptManager


# --------------------
# Helper(s)
# --------------------
def _case_to_message(case: Dict[str, Any]) -> str:
    """Kept for potential logging; not used for legacy mapping anymore."""
    reason = str(case.get("reason", "")).strip()
    return reason if reason else "(no reason provided)"


