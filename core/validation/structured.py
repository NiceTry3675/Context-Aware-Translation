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
# Single source of truth for categories (dimensions)
# --------------------
DIMENSIONS_DEF: Dict[str, str] = {
    "completeness": "원문 내용 누락/부분 누락",
    "accuracy": "의미/뉘앙스/사실/용어 오류 (mistranslation 포함)",
    "addition": "원문에 없는 내용이 번역에 추가됨",
    "name_consistency": "고유명사가 용어집과 불일치",
    "dialogue_style": "대화체 높임/격식 등 말투 부적절",
    "flow": "어색하거나 부자연스러운 한국어 표현",
    "other": "상기 범주에 명확히 속하지 않는 기타 문제",
}


# --------------------
# Response schema (JSON Schema for Gemini)
# --------------------
def make_response_schema(dim_def: Dict[str, str] | None = None) -> Dict[str, Any]:
    dim_def = dim_def or DIMENSIONS_DEF
    allowed = list(dim_def.keys())
    # Gemini Structured Output uses a simplified schema subset. Avoid unsupported
    # keywords like minimum/maximum, and prefer enum or type-only constraints.
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
                        "issue_type": {
                            "type": "string",
                            "description": "이슈 유형",
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
    reason = str(case.get("reason", "")).strip()
    return reason if reason else "(no reason provided)"


def map_cases_to_v1_fields(cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Map structured cases to the legacy fields used by the frontend/report.

    Returns a dict with keys: critical_issues, minor_issues, missing_content,
    added_content, name_inconsistencies
    """
    critical: List[str] = []
    minor: List[str] = []
    missing: List[str] = []
    added: List[str] = []
    names: List[str] = []

    for case in cases or []:
        dimension = str(case.get("dimension", "")).strip()
        severity = int(case.get("severity", 0) or 0)
        msg = _case_to_message(case)

        if dimension == "completeness":
            missing.append(msg)
        elif dimension == "addition":
            added.append(msg)
        elif dimension == "name_consistency":
            names.append(msg)
        else:
            # accuracy/dialogue_style/flow/other → severity-based routing
            if severity >= 3:
                critical.append(msg)
            else:
                minor.append(msg)

    return {
        "critical_issues": critical,
        "minor_issues": minor,
        "missing_content": missing,
        "added_content": added,
        "name_inconsistencies": names,
    }


