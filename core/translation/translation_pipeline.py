"""
Translation Pipeline Module

This module orchestrates the entire translation process, managing the segment-by-segment
translation workflow with context awareness, style consistency, and error handling.
"""

import re
import os
import time
from tqdm import tqdm
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .models.gemini import GeminiModel
from .translation_document import TranslationDocument
from .style_analyzer import StyleAnalyzer
from ..prompts.builder import PromptBuilder
from ..prompts.manager import PromptManager
from ..prompts.sanitizer import PromptSanitizer
from ..config.builder import DynamicConfigBuilder
from ..errors import ProhibitedException, TranslationError
from ..errors import prohibited_content_logger


def get_segment_ending(segment_text: str, max_chars: int) -> str:
    """
    Extracts the very end of a text segment to be used as immediate context,
    ensuring the length does not exceed max_chars and avoiding mid-word cuts.
    """
    if not segment_text or max_chars <= 0:
        return ""
    if len(segment_text) <= max_chars:
        return segment_text
    context = segment_text[-max_chars:]
    first_space_pos = context.find(' ')
    if first_space_pos > -1:
        return context[first_space_pos+1:]
    return context


def _extract_translation_from_response(response: str) -> str:
    """Returns the model's response, stripping any leading/trailing whitespace."""
    return response.strip()


class TranslationPipeline:
    """
    Main orchestrator for the translation process.
    
    This class manages the entire translation workflow, including:
    - Style analysis and definition
    - Segment-by-segment translation
    - Context management and glossary updates
    - Error handling and retries
    - Progress tracking and database updates
    """
    
    def __init__(self, 
                 gemini_api: GeminiModel, 
                 dyn_config_builder: DynamicConfigBuilder, 
                 db: Optional[Session] = None,
                 job_id: Optional[int] = None,
                 initial_core_style: Optional[str] = None):
        """
        Initialize the translation pipeline.
        
        Args:
            gemini_api: The Gemini API model instance
            dyn_config_builder: Dynamic configuration builder for glossary and styles
            db: Optional database session for progress tracking
            job_id: Optional job ID for database updates
            initial_core_style: Optional pre-defined core narrative style
        """
        self.gemini_api = gemini_api
        self.dyn_config_builder = dyn_config_builder
        self.prompt_builder = PromptBuilder(PromptManager.MAIN_TRANSLATION)
        self.style_analyzer = StyleAnalyzer(gemini_api)
        self.db = db
        self.job_id = job_id
        self.initial_core_style = initial_core_style
        
        # Initialize logging directories
        self._init_logging_dirs()
    
    def _init_logging_dirs(self):
        """Initialize logging directories."""
        self.prompt_log_dir = "logs/debug_prompts"
        self.context_log_dir = "logs/context_log"
        os.makedirs(self.prompt_log_dir, exist_ok=True)
        os.makedirs(self.context_log_dir, exist_ok=True)
    
    def translate_document(self, document: TranslationDocument):
        """
        Main entry point for translating a document.
        
        Args:
            document: The TranslationDocument to translate
        """
        start_time = time.time()
        error_type = None
        original_text = ""
        translated_text_final = ""
        
        try:
            self._translate_document_internal(document)
            original_text = "\n".join(s.text for s in document.segments)
            translated_text_final = "\n".join(document.translated_segments)
        except TranslationError as e:
            error_type = e.__class__.__name__
            raise e
        finally:
            if self.db and self.job_id:
                self._record_usage_log(start_time, original_text, translated_text_final, error_type)
    
    def _translate_document_internal(self, document: TranslationDocument):
        """
        Internal method to handle the main translation logic.
        
        Args:
            document: The TranslationDocument to translate
        """
        # Set up logging paths
        prompt_log_path = os.path.join(self.prompt_log_dir, 
                                       f"prompts_job_{self.job_id}_{document.user_base_filename}.txt")
        context_log_path = os.path.join(self.context_log_dir, 
                                        f"context_job_{self.job_id}_{document.user_base_filename}.txt")
        
        self._init_log_files(prompt_log_path, context_log_path, document.user_base_filename)
        
        if not document.segments:
            print("No segments to translate. Exiting.")
            return
        
        # Define core narrative style
        core_narrative_style = self._define_core_style(document)
        self._log_core_style(context_log_path, core_narrative_style)
        
        # Translate segments
        total_segments = len(document.segments)
        for i, segment_info in enumerate(tqdm(document.segments, desc="Translating Segments")):
            segment_index = i + 1
            
            # Update progress
            self._update_progress(i, total_segments)
            
            # Build dynamic guides (glossary and character styles)
            updated_glossary, updated_styles, style_deviation = self._build_dynamic_guides(
                document, segment_info, segment_index, core_narrative_style
            )
            
            # Prepare context for translation
            contextual_glossary = self._get_contextual_glossary(updated_glossary, segment_info.text)
            immediate_context_source = get_segment_ending(document.get_previous_segment(i), max_chars=1500)
            immediate_context_ko = get_segment_ending(document.get_previous_translation(i), max_chars=500)
            
            # Build translation prompt
            prompt = self._build_translation_prompt(
                segment_info, contextual_glossary, updated_styles,
                core_narrative_style, style_deviation,
                immediate_context_source, immediate_context_ko
            )
            
            # Log context and prompt
            self._log_segment_context(context_log_path, segment_index, document,
                                     contextual_glossary, immediate_context_source,
                                     immediate_context_ko, style_deviation)
            self._log_prompt(prompt_log_path, segment_index, prompt)
            
            # Translate segment with retries
            translated_text = self._translate_segment_with_retries(
                prompt, segment_info, segment_index, document, 
                contextual_glossary, style_deviation
            )
            
            # Append translation and save progress
            document.append_translated_segment(translated_text, segment_info)
            document.save_partial_output()
        
        # Save final output
        document.save_final_output()
        
        # Update database with final data
        self._finalize_translation(document)
        
        print(f"\n--- Translation Complete! ---")
        print(f"Output: {document.output_filename}")
    
    def _define_core_style(self, document: TranslationDocument) -> str:
        """
        Define the core narrative style for the document.
        
        Args:
            document: The document to analyze
            
        Returns:
            Core narrative style description
        """
        if self.initial_core_style:
            print("\n--- Using User-Defined Core Narrative Style... ---")
            print(f"Style defined as: {self.initial_core_style}")
            return self.initial_core_style
        else:
            return self.style_analyzer.define_core_style(
                document.filepath, 
                document.user_base_filename
            )
    
    def _build_dynamic_guides(self, document: TranslationDocument, segment_info: Any,
                             segment_index: int, core_narrative_style: str) -> tuple:
        """
        Build dynamic glossary and character style guides for the segment.
        
        Returns:
            Tuple of (updated_glossary, updated_styles, style_deviation)
        """
        updated_glossary, updated_styles, style_deviation = self.dyn_config_builder.build_dynamic_guides(
            segment_text=segment_info.text,
            core_narrative_style=core_narrative_style,
            current_glossary=document.glossary,
            current_character_styles=document.character_styles,
            job_base_filename=document.user_base_filename,
            segment_index=segment_index
        )
        
        # Update document with new guides
        document.glossary = updated_glossary
        document.character_styles = updated_styles
        
        return updated_glossary, updated_styles, style_deviation
    
    def _get_contextual_glossary(self, glossary: Dict[str, str], segment_text: str) -> Dict[str, str]:
        """
        Filter glossary to only include terms present in the current segment.
        """
        return {
            key: value for key, value in glossary.items() 
            if re.search(r'\b' + re.escape(key) + r'\b', segment_text, re.IGNORECASE)
        }
    
    def _build_translation_prompt(self, segment_info: Any, contextual_glossary: Dict[str, str],
                                 character_styles: Dict[str, str], core_narrative_style: str,
                                 style_deviation: str, immediate_context_source: str,
                                 immediate_context_ko: str) -> str:
        """Build the translation prompt for a segment."""
        return self.prompt_builder.build_translation_prompt(
            core_narrative_style=core_narrative_style,
            style_deviation_info=style_deviation,
            glossary=contextual_glossary,
            character_styles=character_styles,
            source_segment=segment_info.text,
            prev_segment_source=immediate_context_source,
            prev_segment_ko=immediate_context_ko,
            protagonist_name=self.dyn_config_builder.character_style_manager.protagonist_name
        )
    
    def _translate_segment_with_retries(self, original_prompt: str, segment_info: Any,
                                       segment_index: int, document: TranslationDocument,
                                       contextual_glossary: dict, style_deviation: str) -> str:
        """
        Translate a segment with retry logic for prohibited content.
        
        Returns:
            Translated text for the segment
        """
        soft_retry_attempts = 3
        prompt = original_prompt
        
        for retry_attempt in range(soft_retry_attempts + 1):
            try:
                if retry_attempt > 0:
                    prompt = PromptSanitizer.create_softer_prompt(original_prompt, retry_attempt)
                    print(f"\nRetrying with softer prompt (attempt {retry_attempt}/{soft_retry_attempts})...")
                    time.sleep(2)
                
                model_response = self.gemini_api.generate_text(prompt)
                translated_text = _extract_translation_from_response(model_response)
                
                if retry_attempt > 0:
                    print(f"Successfully translated with softer prompt on attempt {retry_attempt}")
                return translated_text
                
            except ProhibitedException as e:
                if retry_attempt < soft_retry_attempts:
                    print(f"\nProhibitedException caught: {e}. Will retry with a softer prompt...")
                    continue
                else:
                    return self._handle_final_prohibited_exception(
                        e, segment_info, segment_index, document,
                        contextual_glossary, style_deviation, soft_retry_attempts
                    )
            
            except TranslationError as e:
                print(f"Translation failed for segment {segment_index}. Error: {e}")
                raise e
        
        raise TranslationError(f"Failed to translate segment {segment_index} after all retries.")
    
    def _handle_final_prohibited_exception(self, e: ProhibitedException, segment_info: Any,
                                          segment_index: int, document: TranslationDocument,
                                          contextual_glossary: dict, style_deviation: str,
                                          soft_retry_attempts: int) -> str:
        """Handle the final prohibited content exception after all retries."""
        e.source_text = segment_info.text
        e.context = {
            'segment_index': segment_index,
            'glossary': contextual_glossary,
            'character_styles': document.character_styles,
            'style_deviation': style_deviation,
            'soft_retry_attempts': soft_retry_attempts
        }
        
        log_path = prohibited_content_logger.log_prohibited_content(
            e, document.user_base_filename, segment_index
        )
        print(f"\nAll soft retry attempts failed. Log saved to: {log_path}")
        
        try:
            print("Attempting minimal prompt as last resort...")
            minimal_prompt = PromptSanitizer.create_minimal_prompt(segment_info.text, "Korean")
            model_response = self.gemini_api.generate_text(minimal_prompt)
            return _extract_translation_from_response(model_response)
        except Exception as final_e:
            print(f"Minimal prompt also failed: {final_e}")
            raise e from final_e
    
    def _update_progress(self, current_index: int, total_segments: int):
        """Update translation progress in the database."""
        progress = int((current_index / total_segments) * 100)
        if self.db and self.job_id:
            from backend import crud
            crud.update_job_progress(self.db, self.job_id, progress)
    
    def _finalize_translation(self, document: TranslationDocument):
        """Finalize translation by updating database with results."""
        if self.db and self.job_id:
            from backend import crud
            
            # Update glossary
            crud.update_job_final_glossary(self.db, self.job_id, document.glossary)
            
            # Save translation segments for segment view
            segments_data = []
            for i, (source_segment, translated_segment) in enumerate(
                zip(document.segments, document.translated_segments)
            ):
                segments_data.append({
                    "segment_index": i,
                    "source_text": source_segment.text,
                    "translated_text": translated_segment
                })
            crud.update_job_translation_segments(self.db, self.job_id, segments_data)
    
    def _record_usage_log(self, start_time: float, original_text: str,
                         translated_text: str, error_type: Optional[str]):
        """Record usage statistics to the database."""
        end_time = time.time()
        duration = int(end_time - start_time)
        
        from backend import crud, schemas
        
        log_data = schemas.TranslationUsageLogCreate(
            job_id=self.job_id,
            original_length=len(original_text),
            translated_length=len(translated_text),
            translation_duration_seconds=duration,
            model_used=self.gemini_api.model_name,
            error_type=error_type
        )
        crud.create_translation_usage_log(self.db, log_data)
        print("\n--- Usage log has been recorded. ---")
    
    # Logging helper methods
    def _init_log_files(self, prompt_log_path: str, context_log_path: str, filename: str):
        """Initialize log files with headers."""
        with open(prompt_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {filename}\n\n")
        with open(context_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {filename}\n\n")
    
    def _log_core_style(self, context_log_path: str, core_narrative_style: str):
        """Log the core narrative style."""
        with open(context_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- Core Narrative Style Defined ---\n")
            f.write(f"{core_narrative_style}\n")
            f.write("="*50 + "\n\n")
    
    def _log_prompt(self, prompt_log_path: str, segment_index: int, prompt: str):
        """Log the translation prompt."""
        with open(prompt_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n")
            f.write(prompt)
            f.write("\n\n" + "="*50 + "\n\n")
    
    def _log_segment_context(self, log_path: str, segment_index: int, document: TranslationDocument,
                            contextual_glossary: dict, immediate_context_source: str,
                            immediate_context_ko: str, style_deviation: str):
        """Log the context for a segment translation."""
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- CONTEXT FOR SEGMENT {segment_index} ---\n\n")
            f.write("### Narrative Style Deviation:\n")
            f.write(f"{style_deviation}\n\n")
            f.write("### Contextual Glossary (For This Segment):\n")
            if contextual_glossary:
                for key, value in contextual_glossary.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- None relevant to this segment.\n")
            f.write("\n")
            f.write("### Cumulative Glossary (Full):\n")
            if document.glossary:
                for key, value in document.glossary.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- Empty\n")
            f.write("\n")
            f.write("### Cumulative Character Styles:\n")
            if document.character_styles:
                for key, value in document.character_styles.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- Empty\n")
            f.write("\n")
            f.write("### Immediate language Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_source or 'N/A'}\n\n")
            f.write("### Immediate Korean Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_ko or 'N/A'}\n\n")
            f.write("="*50 + "\n\n")