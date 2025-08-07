"""
Translation Validation Module

This module provides functionality to validate the quality of translations
by comparing source text with translated text using AI-powered analysis.
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from tqdm import tqdm
from core.prompts.manager import PromptManager


class ValidationResult:
    """Represents the result of a translation validation."""
    
    def __init__(self, segment_index: int, source_text: str, translated_text: str):
        self.segment_index = segment_index
        self.source_text = source_text
        self.translated_text = translated_text
        self.status = "PENDING"
        self.critical_issues = []
        self.minor_issues = []
        self.missing_content = []
        self.added_content = []
        self.name_inconsistencies = []
        self.raw_response = ""
    
    def parse_response(self, response_text: str):
        """Parse the validation response from the AI model with improved extraction."""
        self.raw_response = response_text
        
        # Enhanced parsing with multiple patterns
        # Check for status
        status_patterns = [
            r'\*\*Status\*\*[:\s]*([A-Z]+)',
            r'Status[:\s]*([A-Z]+)',
            r'\bPASS\b',
            r'\bFAIL\b'
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                if 'PASS' in match.group(0).upper():
                    self.status = "PASS"
                    break
                elif 'FAIL' in match.group(0).upper():
                    self.status = "FAIL"
                    break
        
        # Extract issues using multiple patterns
        sections = {
            'critical': ['Critical Issues?', 'Major Problems?', 'Critical'],
            'minor': ['Minor Issues?', 'Minor Suggestions?', 'Minor'],
            'missing': ['Missing Content', 'Untranslated Content', 'Omitted Content'],
            'added': ['Added Content', 'Extra Content', 'Additions'],
            'names': ['Name Inconsistencies', 'Character Names?', 'Name Issues']
        }
        
        for section_key, patterns in sections.items():
            for pattern in patterns:
                # Create regex pattern for section - improved to handle embedded bold text
                # Look for the section header and capture everything until the next main section or end
                section_regex = rf'\*\*{pattern}\*\*[:\s]*\n((?:(?!\n\*\*[A-Z][^\*]+\*\*:).)*?)(?=\n\*\*[A-Z][^\*]+\*\*:|$)'
                match = re.search(section_regex, response_text, re.IGNORECASE | re.DOTALL)
                
                if match:
                    content = match.group(1).strip()
                    
                    # Check if content explicitly says "None" or similar
                    if re.match(r'^(none|n/a|nil|\(none\)|\(empty\)|no issues?)\.?$', content, re.IGNORECASE):
                        # Skip this section as it has no issues
                        continue
                    
                    # Extract bullet points - handle * bullet points specifically
                    # Match lines starting with *, -, •, or numbers
                    items = re.findall(r'^[\*\-•\d]+\.?\s+(.+?)(?=\n[\*\-•\d]+\.?\s|\n\n|$)', content, re.MULTILINE | re.DOTALL)
                    
                    # If no bullet points found, try to split by newlines
                    if not items and content and not re.match(r'^(none|n/a)', content, re.IGNORECASE):
                        items = [line.strip() for line in content.split('\n') if line.strip()]
                    
                    for item in items:
                        item_text = item.strip()
                        # Skip empty or placeholder entries
                        if item_text and not re.match(r'^(none|n/a|nil|\(none\)|\(empty\)|no issues?|N/A)\.?$', item_text, re.IGNORECASE):
                            if section_key == 'critical':
                                self.critical_issues.append(item_text)
                            elif section_key == 'minor':
                                self.minor_issues.append(item_text)
                            elif section_key == 'missing':
                                self.missing_content.append(item_text)
                            elif section_key == 'added':
                                self.added_content.append(item_text)
                            elif section_key == 'names':
                                self.name_inconsistencies.append(item_text)
                    break
        
        # If status wasn't found but we have issues, set to FAIL
        if self.status == "PENDING" and self.has_issues():
            self.status = "FAIL"
        elif self.status == "PENDING" and not self.has_issues():
            self.status = "PASS"
    
    def has_issues(self) -> bool:
        """Check if validation found any issues."""
        return (len(self.critical_issues) > 0 or 
                len(self.missing_content) > 0 or 
                len(self.added_content) > 0 or 
                len(self.name_inconsistencies) > 0)
    
    def to_dict(self) -> Dict:
        """Convert validation result to dictionary."""
        result = {
            'segment_index': self.segment_index,
            'status': self.status,
            'critical_issues': self.critical_issues,
            'minor_issues': self.minor_issues,
            'missing_content': self.missing_content,
            'added_content': self.added_content,
            'name_inconsistencies': self.name_inconsistencies,
            'source_preview': self.source_text[:100] + '...' if len(self.source_text) > 100 else self.source_text,
            'translated_preview': self.translated_text[:100] + '...' if len(self.translated_text) > 100 else self.translated_text
        }
        
        # Include raw response for debugging if status is FAIL but no issues captured
        if self.status == "FAIL" and not self.has_issues():
            result['debug_raw_response'] = self.raw_response
            
        return result


class TranslationValidator:
    """Validates translation quality by comparing source and translated text."""
    
    def __init__(self, ai_model, verbose: bool = False):
        """
        Initialize the validator.
        
        Args:
            ai_model: The AI model to use for validation
            verbose: Whether to print verbose output
        """
        self.ai_model = ai_model
        self.verbose = verbose
        
        # Create validation log directory
        self.validation_log_dir = Path('validation_logs')
        self.validation_log_dir.mkdir(exist_ok=True)
    
    def validate_segment(self, 
                         source_text: str, 
                         translated_text: str,
                         glossary: Dict[str, str],
                         segment_index: int,
                         quick_mode: bool = False) -> ValidationResult:
        """
        Validate a single translation segment.
        
        Args:
            source_text: The original source text
            translated_text: The translated Korean text
            glossary: The glossary terms for reference
            segment_index: The index of the segment being validated
            quick_mode: Use quick validation instead of comprehensive
            
        Returns:
            ValidationResult object containing validation findings
        """
        result = ValidationResult(segment_index, source_text, translated_text)
        
        # Format glossary for prompt
        glossary_text = "\n".join([f"{k}: {v}" for k, v in glossary.items()]) if glossary else "N/A"
        
        # Choose validation prompt template
        if quick_mode:
            prompt_template = PromptManager.VALIDATION_QUICK
        else:
            prompt_template = PromptManager.VALIDATION_COMPREHENSIVE
        
        # Build validation prompt by formatting the template
        prompt = prompt_template.format(
            source_text=source_text,
            translated_text=translated_text,
            glossary_terms=glossary_text
        )
        
        if self.verbose:
            print(f"Validating segment {segment_index}...")
        
        try:
            # Call AI model for validation - using generate_text method
            response = self.ai_model.generate_text(prompt)  # GeminiModel uses generate_text
            result.parse_response(response)
            
            if self.verbose:
                if result.has_issues():
                    print(f"  - Issues found in segment {segment_index}")
                elif result.status == "FAIL":
                    print(f"  - Segment {segment_index} failed but no issues parsed (check debug_raw_response in report)")
                    print(f"    Raw response preview: {response[:150]}...")
                
        except Exception as e:
            print(f"Warning: Validation failed for segment {segment_index}: {e}")
            result.status = "ERROR"
            result.critical_issues.append(f"Validation error: {str(e)}")
        
        return result
    
    def validate_job(self, 
                    translation_job,
                    sample_rate: float = 1.0,
                    quick_mode: bool = False,
                    progress_callback=None) -> Tuple[List[ValidationResult], Dict[str, Any]]:
        """
        Validate an entire translation job.
        
        Args:
            translation_job: The TranslationJob object containing segments and translations
            sample_rate: Percentage of segments to validate (0.0 to 1.0)
            quick_mode: Use quick validation instead of comprehensive
            
        Returns:
            Tuple of (list of ValidationResult objects, summary statistics)
        """
        results = []
        total_segments = len(translation_job.segments)
        
        if total_segments != len(translation_job.translated_segments):
            print(f"Warning: Segment count mismatch! Source: {total_segments}, Translated: {len(translation_job.translated_segments)}")
            total_segments = min(total_segments, len(translation_job.translated_segments))
        
        # Calculate segments to validate
        segments_to_validate = max(1, int(total_segments * sample_rate))
        
        if sample_rate < 1.0:
            # Sample evenly across the document without numpy
            if segments_to_validate == 1:
                indices = [total_segments // 2]  # Middle segment
            else:
                step = (total_segments - 1) / (segments_to_validate - 1)
                indices = [int(i * step) for i in range(segments_to_validate)]
        else:
            indices = range(total_segments)
        
        # Create subdirectory for this job's segment reports
        job_validation_dir = self.validation_log_dir / f"{translation_job.user_base_filename}_segments"
        job_validation_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"Starting Translation Validation")
        print(f"{'='*60}")
        print(f"Total segments: {total_segments}")
        print(f"Segments to validate: {segments_to_validate}")
        print(f"Validation mode: {'Quick' if quick_mode else 'Comprehensive'}")
        print(f"Segment reports directory: {job_validation_dir}")
        print(f"{'='*60}\n")
        
        # Validate each selected segment with progress bar
        with tqdm(total=segments_to_validate, desc="Validating segments", unit="segment") as pbar:
            for i, idx in enumerate(indices):
                source_text = translation_job.segments[idx].text
                translated_text = translation_job.translated_segments[idx]
                
                # Update progress bar description
                pbar.set_description(f"Validating segment {idx}")
                
                result = self.validate_segment(
                    source_text=source_text,
                    translated_text=translated_text,
                    glossary=translation_job.glossary,
                    segment_index=idx,
                    quick_mode=quick_mode
                )
                
                results.append(result)
                
                # Save individual segment validation report
                self._save_segment_report(result, job_validation_dir, idx)
                
                # Show issues immediately if found
                if result.has_issues() and self.verbose:
                    self._print_segment_issues(result)
                
                # Update progress callback if provided
                if progress_callback:
                    progress = int(((i + 1) / segments_to_validate) * 100)
                    progress_callback(progress)
                
                pbar.update(1)
        
        # Calculate summary statistics
        summary = self._calculate_summary(results, total_segments, segments_to_validate)
        
        # Save validation report
        self._save_validation_report(results, summary, translation_job.user_base_filename)
        
        # Print detailed summary with example issues
        self._print_detailed_summary(summary, results)
        
        return results, summary
    
    def _calculate_summary(self, results: List[ValidationResult], total_segments: int, validated_segments: int) -> Dict[str, Any]:
        """Calculate summary statistics from validation results."""
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        errors = sum(1 for r in results if r.status == "ERROR")
        
        total_critical = sum(len(r.critical_issues) for r in results)
        total_minor = sum(len(r.minor_issues) for r in results)
        total_missing = sum(len(r.missing_content) for r in results)
        total_added = sum(len(r.added_content) for r in results)
        total_name_issues = sum(len(r.name_inconsistencies) for r in results)
        
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
            'segments_with_issues': [r.segment_index for r in results if r.has_issues()]
        }
    
    def _save_validation_report(self, results: List[ValidationResult], summary: Dict[str, Any], base_filename: str):
        """Save validation report to file."""
        report_path = self.validation_log_dir / f"{base_filename}_validation_report.json"
        
        report = {
            'summary': summary,
            'detailed_results': [r.to_dict() for r in results]
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\nValidation report saved to: {report_path}")
    
    def _save_segment_report(self, result: ValidationResult, output_dir: Path, segment_idx: int):
        """Save individual segment validation report."""
        segment_report_path = output_dir / f"segment_{segment_idx:04d}_validation.json"
        
        # Create a detailed segment report
        segment_report = {
            'segment_index': segment_idx,
            'status': result.status,
            'validation_result': result.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        # If there's a raw response and it failed, include the full response
        if result.status == "FAIL" and result.raw_response:
            segment_report['full_raw_response'] = result.raw_response
        
        with open(segment_report_path, 'w', encoding='utf-8') as f:
            json.dump(segment_report, f, ensure_ascii=False, indent=2)
    
    def _print_segment_issues(self, result: ValidationResult):
        """Print issues for a specific segment."""
        print(f"\n📍 Segment {result.segment_index} Issues:")
        
        if result.critical_issues:
            print("  🔴 Critical Issues:")
            for issue in result.critical_issues[:3]:  # Show first 3 issues
                print(f"     - {issue[:100]}..." if len(issue) > 100 else f"     - {issue}")
        
        if result.missing_content:
            print("  ⚠️  Missing Content:")
            for content in result.missing_content[:2]:
                print(f"     - {content[:100]}..." if len(content) > 100 else f"     - {content}")
        
        if result.added_content:
            print("  ➕ Added Content:")
            for content in result.added_content[:2]:
                print(f"     - {content[:100]}..." if len(content) > 100 else f"     - {content}")
        
        if result.name_inconsistencies:
            print("  👤 Name Inconsistencies:")
            for issue in result.name_inconsistencies[:2]:
                print(f"     - {issue[:100]}..." if len(issue) > 100 else f"     - {issue}")
        
        if result.minor_issues:
            print("  💡 Minor Issues:")
            for issue in result.minor_issues[:2]:
                print(f"     - {issue[:100]}..." if len(issue) > 100 else f"     - {issue}")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print validation summary to console."""
        print(f"\n{'='*60}")
        print(f"Validation Summary")
        print(f"{'='*60}")
        print(f"Segments validated: {summary['validated_segments']}/{summary['total_segments']}")
        print(f"Pass rate: {summary['pass_rate']:.1f}%")
        print(f"  - Passed: {summary['passed']}")
        print(f"  - Failed: {summary['failed']}")
        print(f"  - Errors: {summary['errors']}")
        
        # Show detailed issue counts
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
        
        # Overall assessment with more detail
        if summary['pass_rate'] >= 95:
            print("✅ Translation quality: EXCELLENT")
        elif summary['pass_rate'] >= 85:
            print("✅ Translation quality: GOOD")
        elif summary['pass_rate'] >= 70:
            print("⚠️  Translation quality: NEEDS REVIEW")
            print("   Consider reviewing segments with issues before publishing.")
        else:
            print("❌ Translation quality: POOR - Manual review required")
            print("   Significant issues found. Please review the validation report.")
    
    def _print_detailed_summary(self, summary: Dict[str, Any], results: List[ValidationResult]):
        """Print detailed validation summary with example issues."""
        self._print_summary(summary)
        
        # Show sample issues from failed segments
        failed_results = [r for r in results if r.status == "FAIL" and r.has_issues()]
        
        if failed_results and len(failed_results) > 0:
            print(f"\n{'='*60}")
            print("Sample Issues Found (first 3 segments with problems):")
            print(f"{'='*60}")
            
            for result in failed_results[:3]:
                print(f"\n📍 Segment {result.segment_index}:")
                print(f"   Source: {result.source_text[:80]}..." if len(result.source_text) > 80 else f"   Source: {result.source_text}")
                
                issues_shown = False
                
                if result.critical_issues:
                    print(f"   🔴 Critical: {result.critical_issues[0][:100]}..." if len(result.critical_issues[0]) > 100 else f"   🔴 Critical: {result.critical_issues[0]}")
                    issues_shown = True
                    
                if result.missing_content and not issues_shown:
                    print(f"   ⚠️  Missing: {result.missing_content[0][:100]}..." if len(result.missing_content[0]) > 100 else f"   ⚠️  Missing: {result.missing_content[0]}")
                    issues_shown = True
                    
                if result.name_inconsistencies and not issues_shown:
                    print(f"   👤 Names: {result.name_inconsistencies[0][:100]}..." if len(result.name_inconsistencies[0]) > 100 else f"   👤 Names: {result.name_inconsistencies[0]}")
                    issues_shown = True
                    
                if result.minor_issues and not issues_shown:
                    print(f"   💡 Minor: {result.minor_issues[0][:100]}..." if len(result.minor_issues[0]) > 100 else f"   💡 Minor: {result.minor_issues[0]}")
            
            print(f"\n{'='*60}")