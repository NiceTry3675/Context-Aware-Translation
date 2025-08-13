"""
Structured-only translation validation.

This validator uses Gemini Structured Output with a minimal schema to
produce deterministic JSON results that are consumed directly by the
frontend and post-edit modules (no legacy arrays, no raw_response).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from core.validation.structured import make_response_schema
from core.prompts.manager import PromptManager


class ValidationResult:
    """Represents the result of a translation validation (per segment)."""

    def __init__(self, segment_index: int, source_text: str, translated_text: str):
        self.segment_index = segment_index
        self.source_text = source_text
        self.translated_text = translated_text
        self.status = "PENDING"
        self.structured_cases: Optional[List[Dict[str, Any]]] = None

    def has_issues(self) -> bool:
        return bool(self.structured_cases and len(self.structured_cases) > 0)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            'segment_index': self.segment_index,
            'status': self.status,
            'source_preview': self.source_text[:100] + '...' if len(self.source_text) > 100 else self.source_text,
            'translated_preview': self.translated_text[:100] + '...' if len(self.translated_text) > 100 else self.translated_text,
        }
        if self.structured_cases is not None:
            result['structured_cases'] = self.structured_cases
        return result


class TranslationValidator:
    """Structured-output based validator (no legacy regex)."""

    def __init__(self, ai_model, verbose: bool = False):
        self.ai_model = ai_model
        self.verbose = verbose
        self.validation_log_dir = Path('validation_logs')
        self.validation_log_dir.mkdir(exist_ok=True)

    def validate_segment(
        self,
        *,
        source_text: str,
        translated_text: str,
        glossary: Dict[str, str],
        segment_index: int,
        quick_mode: bool = False,
    ) -> ValidationResult:
        result = ValidationResult(segment_index, source_text, translated_text)

        glossary_text = "\n".join(f"{k}: {v}" for k, v in (glossary or {}).items()) if glossary else "N/A"
        # Build prompt via prompts.yaml to increase cohesion
        prompt_template = (
            PromptManager.VALIDATION_STRUCTURED_QUICK if quick_mode else PromptManager.VALIDATION_STRUCTURED_COMPREHENSIVE
        )
        prompt = prompt_template.format(
            source_text=source_text,
            translated_text=translated_text,
            glossary_terms=glossary_text,
        )
        schema = make_response_schema()

        if self.verbose:
            print(f"Validating segment {segment_index} (structured)...")

        try:
            data = self.ai_model.generate_structured(prompt, schema)
            cases = (data or {}).get('cases', [])
            result.structured_cases = cases

            # 새 단순화 스키마에 맞춰, 결과는 전체 리포트에서 요약만 사용
            # per-segment 객체에는 structured_cases만 저장하고, legacy 필드는 비워둠
            result.status = "FAIL" if (cases and len(cases) > 0) else "PASS"

        except Exception as e:
            print(f"Warning: Structured validation failed for segment {segment_index}: {e}")
            result.status = "ERROR"

        return result

    def validate_job(
        self,
        translation_job,
        *,
        sample_rate: float = 1.0,
        quick_mode: bool = False,
        progress_callback=None,
    ) -> Tuple[List[ValidationResult], Dict[str, Any]]:
        results: List[ValidationResult] = []
        total_segments = len(translation_job.segments)
        if total_segments != len(translation_job.translated_segments):
            print(
                f"Warning: Segment count mismatch! Source: {total_segments}, Translated: {len(translation_job.translated_segments)}"
            )
            total_segments = min(total_segments, len(translation_job.translated_segments))

        segments_to_validate = max(1, int(total_segments * sample_rate))
        if sample_rate < 1.0:
            if segments_to_validate == 1:
                indices = [total_segments // 2]
            else:
                step = (total_segments - 1) / (segments_to_validate - 1)
                indices = [int(i * step) for i in range(segments_to_validate)]
        else:
            indices = range(total_segments)

        job_validation_dir = self.validation_log_dir / f"{translation_job.user_base_filename}_segments"
        job_validation_dir.mkdir(exist_ok=True)

        print(f"\n{'='*60}")
        print("Starting Translation Validation (Structured)")
        print(f"{'='*60}")
        print(f"Total segments: {total_segments}")
        print(f"Segments to validate: {segments_to_validate}")
        print(f"Validation mode: {'Quick' if quick_mode else 'Comprehensive'}")
        print(f"Segment reports directory: {job_validation_dir}")
        print(f"{'='*60}\n")

        # No tqdm dependency here to keep CLI simple in some environments
        for i, idx in enumerate(indices):
            source_text = translation_job.segments[idx].text
            translated_text = translation_job.translated_segments[idx]

            print(f"Validating segment {idx} ({i+1}/{segments_to_validate})...")
            res = self.validate_segment(
                source_text=source_text,
                translated_text=translated_text,
                glossary=translation_job.glossary,
                segment_index=idx,
                quick_mode=quick_mode,
            )
            results.append(res)
            self._save_segment_report(res, job_validation_dir, idx)
            if progress_callback:
                progress = int(((i + 1) / segments_to_validate) * 100)
                progress_callback(progress)

        summary = self._calculate_summary(results, total_segments, segments_to_validate)
        self._save_validation_report(results, summary, translation_job.user_base_filename)
        self._print_detailed_summary(summary, results)
        return results, summary

    def _calculate_summary(self, results: List[ValidationResult], total_segments: int, validated_segments: int) -> Dict[str, Any]:
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        errors = sum(1 for r in results if r.status == "ERROR")

        def normalize_severity(s: Any) -> int:
            if isinstance(s, int):
                return max(1, min(3, s))
            if isinstance(s, str):
                t = s.lower()
                if t in {"critical", "high", "severe"}: return 3
                if t in {"major", "medium", "moderate", "important"}: return 2
                if t in {"minor", "low", "trivial"}: return 1
                try:
                    n = int(s)
                    return max(1, min(3, n))
                except Exception:
                    return 2
            return 2

        total_critical = 0
        total_minor = 0
        total_missing = 0
        total_added = 0
        total_name_issues = 0

        for r in results:
            for c in (r.structured_cases or []):
                sev = normalize_severity(c.get('severity'))
                dim = (c.get('dimension') or c.get('issue_type') or 'other')
                if sev == 3:
                    total_critical += 1
                if sev == 1:
                    total_minor += 1
                if dim == 'completeness':
                    total_missing += 1
                elif dim == 'addition':
                    total_added += 1
                elif dim == 'name_consistency':
                    total_name_issues += 1
        return {
            'total_segments': total_segments,
            'validated_segments': validated_segments,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': (passed / validated_segments * 100) if validated_segments > 0 else 0,
            'total_critical_issues': total_critical,
            'total_minor_issues': total_minor,
            'total_missing_content': total_missing,
            'total_added_content': total_added,
            'total_name_inconsistencies': total_name_issues,
            'segments_with_issues': [r.segment_index for r in results if r.has_issues()],
        }

    def _save_validation_report(self, results: List[ValidationResult], summary: Dict[str, Any], base_filename: str):
        report_path = self.validation_log_dir / f"{base_filename}_validation_report.json"
        report = {
            'summary': summary,
            'detailed_results': [r.to_dict() for r in results],
        }
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nValidation report saved to: {report_path}")

    def _save_segment_report(self, result: ValidationResult, output_dir: Path, segment_idx: int):
        segment_report_path = output_dir / f"segment_{segment_idx:04d}_validation.json"
        segment_report = {
            'segment_index': segment_idx,
            'status': result.status,
            'validation_result': result.to_dict(),
            'timestamp': datetime.now().isoformat(),
        }
        # raw_response is intentionally not persisted
        import json
        with open(segment_report_path, 'w', encoding='utf-8') as f:
            json.dump(segment_report, f, ensure_ascii=False, indent=2)

    def _print_detailed_summary(self, summary: Dict[str, Any], results: List[ValidationResult]):
        print(f"\n{'='*60}")
        print("Validation Summary")
        print(f"{'='*60}")
        print(f"Segments validated: {summary['validated_segments']}/{summary['total_segments']}")
        print(f"Pass rate: {summary['pass_rate']:.1f}%")
        print(f"  - Passed: {summary['passed']}")
        print(f"  - Failed: {summary['failed']}")
        print(f"  - Errors: {summary['errors']}")
        if summary['total_critical_issues'] > 0:
            print(f"\n🔴 Critical Issues: {summary['total_critical_issues']}")
        if summary['total_missing_content'] > 0:
            print(f"⚠️  Missing Content: {summary['total_missing_content']} items")
        if summary['total_added_content'] > 0:
            print(f"➕ Added Content: {summary['total_added_content']} items")
        if summary['total_name_inconsistencies'] > 0:
            print(f"👤 Name Inconsistencies: {summary['total_name_inconsistencies']}")
        if summary['total_minor_issues'] > 0:
            print(f"💡 Minor Issues: {summary['total_minor_issues']}")
        if summary['segments_with_issues']:
            print(f"\n📋 Segments with issues: {summary['segments_with_issues'][:10]}")
            if len(summary['segments_with_issues']) > 10:
                print(f"  ... and {len(summary['segments_with_issues']) - 10} more")
        print(f"{'='*60}")


