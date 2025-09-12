"""
Structured-only translation validation.

This validator uses Gemini Structured Output with a minimal schema to
produce deterministic JSON results that are consumed directly by the
frontend and post-edit modules (no legacy arrays, no raw_response).
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple, Any

from core.schemas.validation import ValidationCase, ValidationResult, make_validation_response_schema as make_response_schema
from core.prompts.manager import PromptManager
# Logging handled by service; no direct logger usage here


class TranslationValidator:
    """Structured-output based validator (no legacy regex)."""

    def __init__(self, ai_model, verbose: bool = False):
        self.ai_model = ai_model
        self.verbose = verbose

    def validate_segment(
        self,
        *,
        source_text: str,
        translated_text: str,
        glossary: Dict[str, str],
        segment_index: int,
        quick_mode: bool = False,
    ) -> ValidationResult:
        # Create ValidationResult using Pydantic model
        result = ValidationResult(
            segment_index=segment_index,
            source_text=source_text,
            translated_text=translated_text
        )

        # Filter glossary to only include terms that appear in the source text
        if glossary:
            contextual_glossary = {
                key: value for key, value in glossary.items()
                if re.search(r'\b' + re.escape(key) + r'\b', source_text, re.IGNORECASE)
            }
            if self.verbose and len(glossary) > 0:
                print(f"  Filtered glossary: {len(glossary)} → {len(contextual_glossary)} terms")
        else:
            contextual_glossary = {}
        
        glossary_text = "\n".join(f"{k}: {v}" for k, v in contextual_glossary.items()) if contextual_glossary else "N/A"
        # Build prompt via prompts.yaml to increase cohesion
        prompt_template = (
            PromptManager.VALIDATION_STRUCTURED_QUICK if quick_mode else PromptManager.VALIDATION_STRUCTURED_COMPREHENSIVE
        )
        prompt = prompt_template.format(
            source_text=source_text,
            translated_text=translated_text,
            glossary_terms=glossary_text,
        )

        if self.verbose:
            print(f"Validating segment {segment_index} (structured)...")

        try:
            # Use JSON schema for compatibility with Gemini API
            response_schema = make_response_schema()
            response = self.ai_model.generate_structured(prompt, response_schema)
            
            if self.verbose:
                print(f"[VALIDATOR DEBUG] Segment {segment_index} response: {response}")
            
            # Response is a dict when using JSON schema
            cases = (response or {}).get('cases', [])
            
            if self.verbose and not cases:
                print(f"[VALIDATOR DEBUG] Segment {segment_index}: No issues found (PASS)")
            elif self.verbose:
                print(f"[VALIDATOR DEBUG] Segment {segment_index}: Found {len(cases)} issues")
                
            # Convert dict cases to ValidationCase models
            result.structured_cases = [ValidationCase(**case) for case in cases] if cases else None
            result.status = "FAIL" if cases else "PASS"

        except Exception as e:
            print(f"Warning: Structured validation failed for segment {segment_index}: {e}")
            result.status = "ERROR"

        return result

    def validate_document(
        self,
        document,
        *,
        sample_rate: float = 1.0,
        quick_mode: bool = False,
        progress_callback=None,
    ) -> Tuple[List[ValidationResult], Dict[str, Any]]:
        results: List[ValidationResult] = []
        total_segments = len(document.segments)
        print(f"[VALIDATOR] Starting validation - source segments: {total_segments}, translated segments: {len(document.translated_segments)}")
        if total_segments != len(document.translated_segments):
            print(
                f"Warning: Segment count mismatch! Source: {total_segments}, Translated: {len(document.translated_segments)}"
            )
            total_segments = min(total_segments, len(document.translated_segments))

        segments_to_validate = max(1, int(total_segments * sample_rate))
        if sample_rate < 1.0:
            if segments_to_validate == 1:
                indices = [total_segments // 2]
            else:
                step = (total_segments - 1) / (segments_to_validate - 1)
                indices = [int(i * step) for i in range(segments_to_validate)]
        else:
            indices = range(total_segments)

        # Progress tracking handled by centralized logging
        
        if self.verbose:
            print(f"\n{'='*60}")
            print("Starting Translation Validation (Structured)")
            print(f"{'='*60}")
            print(f"Total segments: {total_segments}")
            print(f"Segments to validate: {segments_to_validate}")
            print(f"Validation mode: {'Quick' if quick_mode else 'Comprehensive'}")
            print(f"{'='*60}\n")

        # Process segments with centralized progress tracking
        print(f"[VALIDATOR] Will validate {segments_to_validate} segments, indices: {list(indices)[:5]}...")
        for i, idx in enumerate(indices):
            source_text = document.segments[idx].text
            translated_text = document.translated_segments[idx]

            if self.verbose:
                print(f"Validating segment {idx} ({i+1}/{segments_to_validate})...")
            
            res = self.validate_segment(
                source_text=source_text,
                translated_text=translated_text,
                glossary=document.glossary,
                segment_index=idx,
                quick_mode=quick_mode,
            )
            results.append(res)
            
            if progress_callback:
                progress = int(((i + 1) / segments_to_validate) * 100)
                progress_callback(progress)

        print(f"[VALIDATOR] Validation complete - {len(results)} results collected")
        summary = self._calculate_summary(results, total_segments, segments_to_validate)
        
        if self.verbose:
            self._print_detailed_summary(summary, results)
        return results, summary

    def _calculate_summary(self, results: List[ValidationResult], total_segments: int, validated_segments: int) -> Dict[str, Any]:
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        errors = sum(1 for r in results if r.status == "ERROR")

        def normalize_severity(s: str) -> int:
            """Convert severity string to integer (1, 2, or 3)."""
            try:
                return int(s)
            except (ValueError, TypeError):
                return 2  # Default to major if invalid

        severity_counts = {1: 0, 2: 0, 3: 0}
        dimension_counts = {
            'completeness': 0,
            'accuracy': 0,
            'addition': 0,
            'name_consistency': 0,
            'dialogue_style': 0,
            'flow': 0,
            'other': 0,
        }

        for r in results:
            for c in (r.structured_cases or []):
                sev = normalize_severity(c.severity)
                dim = c.dimension
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
                if dim not in dimension_counts:
                    dimension_counts[dim] = 0
                dimension_counts[dim] += 1
        return {
            'total_segments': total_segments,
            'validated_segments': validated_segments,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': (passed / validated_segments * 100) if validated_segments > 0 else 0,
            'case_counts_by_severity': {
                '1': severity_counts.get(1, 0),
                '2': severity_counts.get(2, 0),
                '3': severity_counts.get(3, 0),
            },
            'case_counts_by_dimension': dimension_counts,
            'segments_with_cases': [r.segment_index for r in results if r.has_issues()],
        }

    # Removed centralized logging duplication; the service persists the report

    def _print_detailed_summary(self, summary: Dict[str, Any], results: List[ValidationResult]):
        print(f"\n{'='*60}")
        print("Validation Summary")
        print(f"{'='*60}")
        print(f"Segments validated: {summary['validated_segments']}/{summary['total_segments']}")
        print(f"Pass rate: {summary['pass_rate']:.1f}%")
        print(f"  - Passed: {summary['passed']}")
        print(f"  - Failed: {summary['failed']}")
        print(f"  - Errors: {summary['errors']}")
        sev = summary.get('case_counts_by_severity', {})
        dim = summary.get('case_counts_by_dimension', {})
        print(f"\nSeverity counts: minor={sev.get('1', 0)}, major={sev.get('2', 0)}, critical={sev.get('3', 0)}")
        if dim:
            print("By dimension:")
            for k in ['completeness','accuracy','addition','name_consistency','dialogue_style','flow','other']:
                if k in dim:
                    print(f"  - {k}: {dim[k]}")
        segs = summary.get('segments_with_cases', [])
        if segs:
            print(f"\n📋 Segments with cases: {segs[:10]}")
            if len(segs) > 10:
                print(f"  ... and {len(segs) - 10} more")
        print(f"{'='*60}")
