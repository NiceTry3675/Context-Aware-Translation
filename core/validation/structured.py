"""
Structured validation utilities for Gemini Structured Output (EN → KO validation).

This module centralizes:
- The definition of validation dimensions (single source of truth)
- JSON schema builder for response validation
- A prompt builder that pairs with the schema
- Mapping functions to convert structured cases to the existing report shape
"""

from __future__ import annotations

from typing import Dict, List, Any


# --------------------
# Allowed dimensions are enumerated directly in the schema enum for simplicity
# --------------------


# --------------------
# Response schema (JSON Schema for Gemini)
# --------------------
def make_response_schema(dim_def: Dict[str, str] | None = None) -> Dict[str, Any]:
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
                        # 차원(enum) – DIMENSIONS_DEF 제거, enum으로 직접 관리
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
                        # 과거 호환을 위한 선택 필드
                        "issue_type": {
                            "type": "string",
                            "description": "이슈 유형(구버전 호환)",
                        },
                        "severity": {
                            "type": "integer",
                            "description": "1=minor, 2=major, 3=critical",
                        },
                    },
                    "required": ["current_korean_sentence", "problematic_source_sentence", "reason"],
                },
            }
        },
        "required": ["cases"],
    }


# (Removed) Prompt builder – we now exclusively use prompts.yaml via PromptManager


# --------------------
# 4) Mapping: structured cases -> legacy report fields
# --------------------
def _case_to_message(case: Dict[str, Any]) -> str:
    """Kept for potential logging; not used for legacy mapping anymore."""
    reason = str(case.get("reason", "")).strip()
    return reason if reason else "(no reason provided)"


