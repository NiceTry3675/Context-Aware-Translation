"""
Post-Edit Module

This module provides functionality to post-edit translations based on validation reports,
automatically fixing identified issues using AI-powered correction.

The PostEditEngine works as a separate post-processing step after translation is complete,
analyzing validation reports and applying targeted corrections.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from tqdm import tqdm
from core.prompts.manager import PromptManager


class PostEditEngine:
    """Handles post-editing of translations based on validation reports."""
    
    def __init__(self, ai_model, verbose: bool = False):
        """
        Initialize the post-edit engine.
        
        Args:
            ai_model: The AI model to use for post-editing
            verbose: Whether to print verbose output
        """
        self.ai_model = ai_model
        self.verbose = verbose
        
        # Create post-edit log directory
        self.postedit_log_dir = Path('logs/postedit_logs')
        self.postedit_log_dir.mkdir(parents=True, exist_ok=True)
    
    def load_validation_report(self, report_path: str) -> Dict[str, Any]:
        """
        Load validation report from JSON file.
        
        Args:
            report_path: Path to the validation report JSON file
            
        Returns:
            Dictionary containing validation report data
        """
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def identify_segments_needing_edit(self,
                                       validation_report: Dict[str, Any],
                                       selected_cases: Dict[int, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Identify segments that need post-editing based on validation results and selected structured cases.
        
        Args:
            validation_report: The loaded validation report
            selected_cases: Optional mask per segment index -> boolean[] indicating which structured cases to fix
            
        Returns:
            List of segments that need editing with their issues
        """
        segments_to_edit = []
        
        for result in validation_report.get('detailed_results', []):
            segment_idx = result['segment_index']
            cases = result.get('structured_cases') or []
            if not cases:
                continue
            # Apply selection mask if provided
            mask = None
            if selected_cases and segment_idx in selected_cases:
                mask = selected_cases.get(segment_idx)
            chosen_cases = []
            for i, case in enumerate(cases):
                if mask is None or (isinstance(mask, list) and i < len(mask) and mask[i]):
                    chosen_cases.append(case)
            if not chosen_cases:
                continue
            # Build a normalized record for editing
            segments_to_edit.append({
                'segment_index': segment_idx,
                'structured_cases': chosen_cases,
            })
        
        return segments_to_edit
    
    def generate_edit_prompt(self,
                            segment_data: Dict[str, Any],
                            source_text: str,
                            translated_text: str,
                            glossary: Dict[str, str]) -> str:
        """
        Generate a specific prompt for fixing the identified issues.
        
        Args:
            segment_data: Validation result data for the segment
            source_text: Original source text
            translated_text: Current translation
            glossary: Translation glossary
            
        Returns:
            Formatted prompt for post-editing
        """
        # Get the post-edit prompt template
        prompt_template = PromptManager.POST_EDIT_CORRECTION
        
        # Format structured cases for the prompt
        issues_text = "**Issues to Fix (structured):**\n"
        for case in segment_data.get('structured_cases', []):
            cur = case.get('current_korean_sentence')
            src = case.get('problematic_source_sentence')
            why = case.get('reason')
            fix = case.get('corrected_korean_sentence')
            issues_text += f"- 현재: {cur}\n  원문: {src}\n  이유: {why}\n"
            if fix:
                issues_text += f"  수정안: {fix}\n"
        issues_text += "\n"
        
        # Format glossary for reference
        glossary_text = "\n".join([f"{k}: {v}" for k, v in glossary.items()]) if glossary else "N/A"
        
        # Build the prompt
        prompt = prompt_template.format(
            source_text=source_text,
            current_translation=translated_text,
            issues_found=issues_text,
            glossary_terms=glossary_text
        )
        
        return prompt
    
    def post_edit_segment(self,
                         segment_data: Dict[str, Any],
                         source_text: str,
                         translated_text: str,
                         glossary: Dict[str, str]) -> str:
        """
        Post-edit a single segment to fix identified issues.
        
        Args:
            segment_data: Validation result data for the segment
            source_text: Original source text
            translated_text: Current translation
            glossary: Translation glossary
            
        Returns:
            Post-edited translation text
        """
        prompt = self.generate_edit_prompt(segment_data, source_text, translated_text, glossary)
        
        if self.verbose:
            print(f"Post-editing segment {segment_data['segment_index']}...")
            if segment_data.get('structured_cases'):
                print(f"  - Fixing {len(segment_data['structured_cases'])} validation issues")
        
        try:
            # Call AI model for post-editing
            edited_text = self.ai_model.generate_text(prompt)
            
            # Clean up the response (remove any markdown formatting if present)
            edited_text = edited_text.strip()
            if edited_text.startswith('```'):
                # Remove code block markers if present
                lines = edited_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines[-1] == '```':
                    lines = lines[:-1]
                edited_text = '\n'.join(lines)
            
            return edited_text
            
        except Exception as e:
            print(f"Warning: Post-edit failed for segment {segment_data['segment_index']}: {e}")
            # Return original translation if post-edit fails
            return translated_text
    
    def post_edit_document(self,
                          translation_document,
                          validation_report_path: str,
                          selected_cases: Dict[int, Any] | None = None,
                          progress_callback=None,
                          job_id: Optional[int] = None) -> List[str]:
        """
        Post-edit an entire translation document based on validation report.
        
        Args:
            translation_document: The TranslationDocument object
            validation_report_path: Path to the validation report JSON file
            selected_cases: Optional mask per segment index -> boolean[] indicating which structured cases to fix
            progress_callback: Optional callback function for progress updates
            job_id: Optional job ID for logging purposes
            
        Returns:
            List of post-edited translations
        """
        # Load validation report
        validation_report = self.load_validation_report(validation_report_path)
        
        # Identify segments needing edit based on structured case selection
        segments_to_edit = self.identify_segments_needing_edit(validation_report, selected_cases)
        segments_to_edit_idx = {s['segment_index'] for s in segments_to_edit}
        
        if not segments_to_edit:
            print("No segments require post-editing. Translation quality is good!")
            # Still create a comprehensive log even if no edits were needed
            complete_log = self._create_complete_log(
                translation_document, 
                translation_document.translated_segments, 
                validation_report,
                segments_to_edit_idx,
            )
            summary = {
                'segments_edited': 0,
                'total_segments': len(translation_document.translated_segments),
                'edit_percentage': 0.0,
            }
            self._save_postedit_log(complete_log, summary, translation_document.user_base_filename, job_id)
            return translation_document.translated_segments
        
        print(f"\n{'='*60}")
        print(f"Starting Post-Edit Process")
        print(f"{'='*60}")
        print(f"Total segments: {len(translation_document.translated_segments)}")
        print(f"Segments to edit: {len(segments_to_edit)}")
        print(f"{'='*60}\n")
        
        # Create a copy of translated segments for editing
        edited_segments = translation_document.translated_segments.copy()
        
        # Post-edit each problematic segment
        with tqdm(total=len(segments_to_edit), desc="Post-editing segments", unit="segment") as pbar:
            for segment_data in segments_to_edit:
                segment_idx = segment_data['segment_index']
                
                # Get source and current translation
                source_text = translation_document.segments[segment_idx].text
                current_translation = edited_segments[segment_idx]
                
                # Update progress bar
                pbar.set_description(f"Post-editing segment {segment_idx}")
                
                # Perform post-edit
                edited_translation = self.post_edit_segment(
                    segment_data=segment_data,
                    source_text=source_text,
                    translated_text=current_translation,
                    glossary=translation_document.glossary
                )
                
                # Update the segment
                edited_segments[segment_idx] = edited_translation

                if progress_callback:
                    progress = int(((pbar.n + 1) / len(segments_to_edit)) * 100)
                    progress_callback(progress)
                
                pbar.update(1)
        
        # Create comprehensive log with all segments
        complete_log = self._create_complete_log(
            translation_document, 
            edited_segments, 
            validation_report,
            segments_to_edit_idx,
        )
        
        # Calculate summary
        summary = {
            'segments_edited': len(segments_to_edit),
            'total_segments': len(translation_document.translated_segments),
            'edit_percentage': (len(segments_to_edit) / len(translation_document.translated_segments) * 100),
        }
        
        # Save post-edit log
        self._save_postedit_log(complete_log, summary, translation_document.user_base_filename, job_id)
        
        # Print summary
        self._print_summary(summary)
        
        # Update the translation document with edited segments
        translation_document.translated_segments = edited_segments
        
        return edited_segments
    
    def _create_complete_log(self, 
                            translation_document,
                            edited_segments: List[str],
                            validation_report: Dict[str, Any],
                            edited_indices: set) -> List[Dict[str, Any]]:
        """
        Create a comprehensive log containing all segments with their complete translations.
        
        Args:
            translation_document: The TranslationDocument object
            edited_segments: The edited translations
            validation_report: The validation report data
            edited_indices: Set of segment indices that were edited
            
        Returns:
            List of all segments with complete information
        """
        complete_log = []
        
        # Create a mapping of validation results by segment index
        validation_by_idx = {}
        for result in validation_report.get('detailed_results', []):
            validation_by_idx[result['segment_index']] = result
        
        # Process all segments
        for idx in range(len(translation_document.segments)):
            source_text = translation_document.segments[idx].text
            original_translation = translation_document.translated_segments[idx]
            edited_translation = edited_segments[idx]
            was_edited = idx in edited_indices
            
            # Get validation data for this segment
            validation_data = validation_by_idx.get(idx, {})
            
            segment_entry = {
                'segment_index': idx,
                'was_edited': was_edited,
                'source_text': source_text,
                'original_translation': original_translation,
                'edited_translation': edited_translation,
                'validation_status': validation_data.get('status', 'N/A'),
                'structured_cases': validation_data.get('structured_cases', []),
            }
            
            # Add change summary if edited
            if was_edited:
                segment_entry['changes_made'] = self._detect_changes(
                    original_translation, 
                    edited_translation
                )
            
            complete_log.append(segment_entry)
        
        return complete_log
    
    def _detect_changes(self, original: str, edited: str) -> Dict[str, Any]:
        """
        Detect and summarize changes between original and edited translations.
        
        Args:
            original: Original translation
            edited: Edited translation
            
        Returns:
            Dictionary summarizing the changes
        """
        changes = {
            'text_changed': original != edited,
            'length_change': len(edited) - len(original),
            'original_length': len(original),
            'edited_length': len(edited)
        }
        
        # Could add more sophisticated change detection here
        # (e.g., word-level diff, specific change patterns, etc.)
        
        return changes
    
    def _save_postedit_log(self, complete_log: List[Dict], summary: Dict[str, Any], base_filename: str, job_id: Optional[int] = None):
        """Save comprehensive post-edit log to file."""
        # Include job ID if provided to match the retrieval pattern
        if job_id is not None:
            log_filename = f"{job_id}_{base_filename}_postedit_log.json"
        else:
            log_filename = f"{base_filename}_postedit_log.json"
        
        log_path = self.postedit_log_dir / log_filename
        
        log_data = {
            'summary': summary,
            'segments': complete_log  # Changed from 'edits' to 'segments' for clarity
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nPost-edit log saved to: {log_path}")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print post-edit summary."""
        print(f"\n{'='*60}")
        print(f"Post-Edit Summary")
        print(f"{'='*60}")
        print(f"Segments edited: {summary['segments_edited']}/{summary['total_segments']} ({summary['edit_percentage']:.1f}%)")
        # Detailed per-type counts are no longer tracked in simplified flow
        print(f"{'='*60}")
        print("✅ Post-editing completed successfully!")