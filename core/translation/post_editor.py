"""
Post-Edit Module

This module provides functionality to post-edit translations based on validation reports,
automatically fixing identified issues using AI-powered correction.
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
        self.postedit_log_dir = Path('postedit_logs')
        self.postedit_log_dir.mkdir(exist_ok=True)
    
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
    
    def identify_segments_needing_edit(self, validation_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify segments that need post-editing based on validation results.
        
        Args:
            validation_report: The loaded validation report
            
        Returns:
            List of segments that need editing with their issues
        """
        segments_to_edit = []
        
        for result in validation_report.get('detailed_results', []):
            # Only process segments that have actual issues
            if result['status'] == 'FAIL' and (
                result.get('critical_issues', []) or
                result.get('missing_content', []) or
                result.get('added_content', []) or
                result.get('name_inconsistencies', [])
            ):
                segments_to_edit.append(result)
        
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
        
        # Format issues for the prompt
        issues_text = ""
        
        if segment_data.get('critical_issues'):
            issues_text += "**Critical Issues to Fix:**\n"
            for issue in segment_data['critical_issues']:
                issues_text += f"- {issue}\n"
            issues_text += "\n"
        
        if segment_data.get('missing_content'):
            issues_text += "**Missing Content (must be added to translation):**\n"
            for content in segment_data['missing_content']:
                issues_text += f"- {content}\n"
            issues_text += "\n"
        
        if segment_data.get('added_content'):
            issues_text += "**Added Content (should be removed if not in source):**\n"
            for content in segment_data['added_content']:
                issues_text += f"- {content}\n"
            issues_text += "\n"
        
        if segment_data.get('name_inconsistencies'):
            issues_text += "**Name Inconsistencies (must follow glossary):**\n"
            for issue in segment_data['name_inconsistencies']:
                issues_text += f"- {issue}\n"
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
            if segment_data.get('critical_issues'):
                print(f"  - Fixing {len(segment_data['critical_issues'])} critical issues")
            if segment_data.get('missing_content'):
                print(f"  - Adding {len(segment_data['missing_content'])} missing content pieces")
        
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
    
    def post_edit_job(self,
                     translation_job,
                     validation_report_path: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        Post-edit an entire translation job based on validation report.
        
        Args:
            translation_job: The TranslationJob object
            validation_report_path: Path to the validation report JSON file
            
        Returns:
            Tuple of (post-edited translations, summary statistics)
        """
        # Load validation report
        validation_report = self.load_validation_report(validation_report_path)
        
        # Identify segments needing edit
        segments_to_edit = self.identify_segments_needing_edit(validation_report)
        
        if not segments_to_edit:
            print("No segments require post-editing. Translation quality is good!")
            return translation_job.translated_segments, {'segments_edited': 0}
        
        print(f"\n{'='*60}")
        print(f"Starting Post-Edit Process")
        print(f"{'='*60}")
        print(f"Total segments: {len(translation_job.translated_segments)}")
        print(f"Segments to edit: {len(segments_to_edit)}")
        print(f"{'='*60}\n")
        
        # Create a copy of translated segments for editing
        edited_segments = translation_job.translated_segments.copy()
        edit_log = []
        
        # Post-edit each problematic segment
        with tqdm(total=len(segments_to_edit), desc="Post-editing segments", unit="segment") as pbar:
            for segment_data in segments_to_edit:
                segment_idx = segment_data['segment_index']
                
                # Get source and current translation
                source_text = translation_job.segments[segment_idx].text
                current_translation = edited_segments[segment_idx]
                
                # Update progress bar
                pbar.set_description(f"Post-editing segment {segment_idx}")
                
                # Perform post-edit
                edited_translation = self.post_edit_segment(
                    segment_data=segment_data,
                    source_text=source_text,
                    translated_text=current_translation,
                    glossary=translation_job.glossary
                )
                
                # Update the segment
                edited_segments[segment_idx] = edited_translation
                
                # Log the edit
                edit_log.append({
                    'segment_index': segment_idx,
                    'issues_fixed': {
                        'critical': len(segment_data.get('critical_issues', [])),
                        'missing_content': len(segment_data.get('missing_content', [])),
                        'added_content': len(segment_data.get('added_content', [])),
                        'name_inconsistencies': len(segment_data.get('name_inconsistencies', []))
                    },
                    'original_translation': current_translation[:100] + '...' if len(current_translation) > 100 else current_translation,
                    'edited_translation': edited_translation[:100] + '...' if len(edited_translation) > 100 else edited_translation
                })
                
                pbar.update(1)
        
        # Calculate summary
        summary = {
            'segments_edited': len(segments_to_edit),
            'total_segments': len(translation_job.translated_segments),
            'edit_percentage': (len(segments_to_edit) / len(translation_job.translated_segments) * 100),
            'issues_addressed': {
                'critical': sum(len(s.get('critical_issues', [])) for s in segments_to_edit),
                'missing_content': sum(len(s.get('missing_content', [])) for s in segments_to_edit),
                'added_content': sum(len(s.get('added_content', [])) for s in segments_to_edit),
                'name_inconsistencies': sum(len(s.get('name_inconsistencies', [])) for s in segments_to_edit)
            }
        }
        
        # Save post-edit log
        self._save_postedit_log(edit_log, summary, translation_job.user_base_filename)
        
        # Print summary
        self._print_summary(summary)
        
        # Update the translation job with edited segments
        translation_job.translated_segments = edited_segments
        
        return edited_segments, summary
    
    def _save_postedit_log(self, edit_log: List[Dict], summary: Dict[str, Any], base_filename: str):
        """Save post-edit log to file."""
        log_path = self.postedit_log_dir / f"{base_filename}_postedit_log.json"
        
        log_data = {
            'summary': summary,
            'edits': edit_log
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
        print(f"\nIssues addressed:")
        print(f"  🔴 Critical issues: {summary['issues_addressed']['critical']}")
        print(f"  ⚠️  Missing content: {summary['issues_addressed']['missing_content']}")
        print(f"  ➕ Added content: {summary['issues_addressed']['added_content']}")
        print(f"  👤 Name inconsistencies: {summary['issues_addressed']['name_inconsistencies']}")
        print(f"{'='*60}")
        print("✅ Post-editing completed successfully!")