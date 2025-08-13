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
# 1) Single source of truth for categories (dimensions)
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


def _dimension_one_liners(dim_def: Dict[str, str]) -> str:
    return "\n".join(f"{k}: {v}" for k, v in dim_def.items())


# --------------------
# 2) Response schema (JSON Schema for Gemini)
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
                        "dimension": {
                            "type": "string",
                            "enum": allowed,
                            "description": f"이슈 차원. 허용값: {' | '.join(allowed)}",
                        },
                        "severity": {
                            "type": "integer",
                            "description": "1=minor, 2=major, 3=critical",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "보조 라벨(예: terminology, formality, punctuation)",
                        },
                        "problematic_source_sentence": {
                            "type": "string",
                            "description": "문제가 되는 원문 문장",
                        },
                        "current_korean_sentence": {
                            "type": "string",
                            "description": "문제가 되는 현재 한국어 문장",
                        },
                        "reason": {
                            "type": "string",
                            "description": "왜 문제인지(의미 왜곡/누락/추가/형식/자연스러움 등)",
                        },
                        "corrected_korean_sentence": {
                            "type": "string",
                            "description": "수정 제안된 한국어 문장",
                        },
                    },
                    "required": ["dimension", "severity", "reason"],
                },
            }
        },
        "required": ["cases"],
    }


# --------------------
# 3) Prompt builder (short, synced with schema via DIMENSIONS_DEF)
# --------------------
def build_validation_prompt(
    *,
    source_text: str,
    translated_text: str,
    glossary_terms: str | None = None,
    source_sentences_json: str | None = None,  # optional: JSON string of [{id, text}]
    translation_sentences_json: str | None = None,  # optional: JSON string of [{id, text}]
) -> str:
    return (
        "ROLE: Expert translation quality validator for EN → KO.\n"
        "TASK: Identify every issue and return JSON that matches the response schema. No extra commentary.\n\n"
        "INPUTS\n"
        "- Source Text (raw):\n---\n"
        f"{source_text}\n---\n"
        "- Korean Translation (raw):\n---\n"
        f"{translated_text}\n---\n"
        "- Glossary (authoritative for names/terms):\n"
        f"{glossary_terms or '(none)'}\n"
        + (f"- Source sentences with IDs (optional):\n{source_sentences_json}\n" if source_sentences_json else "")
        + (f"- Translation sentences with IDs (optional):\n{translation_sentences_json}\n" if translation_sentences_json else "")
        + "\nDIMENSIONS (choose one per case)\n"
        + _dimension_one_liners(DIMENSIONS_DEF)
        + "\n\nSEVERITY (1=minor, 2=major, 3=critical)\n"
        "- 3: 의미 변경/큰 누락/정체성 깨지는 이름 불일치 등 치명적 오류\n"
        "- 2: 의미/스타일 문제로 이해는 가능하나 수정보완 필요\n"
        "- 1: 맞춤법·구두점·미세한 표현 개선\n\n"
        "FIELD RULES\n"
        "- Required per case: dimension, severity, reason.\n"
        "- corrected_korean_sentence: 재작성 가능한 경우 최종 문장 1개만 제공(설명/따옴표 금지). 불가하면 생략.\n"
        "- problematic_source_sentence/current_korean_sentence: 해당할 때만. addition 유형은 보통 원문 문장이 없음.\n"
        "- source_id/translation_id: 문장 ID를 입력으로 받은 경우에만 포함(스팬 대신 ID 우선).\n"
        "- tags: 선택(예: terminology, formality, punctuation).\n"
        "- 해당하지 않는 필드는 완전히 생략(N/A 금지).\n\n"
        "CHECKLIST\n"
        "1) Completeness(누락)  2) Accuracy(의미/용어)  3) Addition(추가)\n"
        "4) Name consistency  5) Dialogue style  6) Flow\n\n"
        "OUTPUT\n"
        "- Return JSON only; the API enforces the schema."
    )


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


