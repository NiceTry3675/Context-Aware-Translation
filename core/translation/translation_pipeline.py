"""
Translation Pipeline Module

This module orchestrates the entire translation process, managing the segment-by-segment
translation workflow with context awareness, style consistency, and error handling.
"""

import re
import time
from tqdm import tqdm
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .models.gemini import GeminiModel
from .models.openrouter import OpenRouterModel
from .document import TranslationDocument
from .style_analyzer import StyleAnalyzer
from .progress_tracker import ProgressTracker
from ..prompts.builder import PromptBuilder
from ..prompts.manager import PromptManager
from ..prompts.sanitizer import PromptSanitizer
from ..config.builder import DynamicConfigBuilder
from ..errors import ProhibitedException, TranslationError
from ..errors import prohibited_content_logger
from ..utils.logging import TranslationLogger


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
                 gemini_api: GeminiModel | OpenRouterModel, 
                 dyn_config_builder: DynamicConfigBuilder, 
                 db: Optional[Session] = None,
                 job_id: Optional[int] = None,
                 initial_core_style: Optional[str] = None,
                 style_model_api: Optional[GeminiModel | OpenRouterModel] = None):
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
        # Allow a different model for style analysis if provided
        self.style_analyzer = StyleAnalyzer(style_model_api or gemini_api, job_id)
        self.progress_tracker = ProgressTracker(db, job_id)
        self.initial_core_style = initial_core_style
        
        # Logger will be initialized with document filename later
        self.job_id = job_id
        self.logger = None
    
    
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
            model_name = getattr(self.gemini_api, 'model_name', 'unknown_model')
            self.progress_tracker.record_usage_log(
                original_text, translated_text_final, 
                model_name, error_type
            )
    
    def _translate_document_internal(self, document: TranslationDocument):
        """
        Internal method to handle the main translation logic.
        
        Args:
            document: The TranslationDocument to translate
        """
        # Initialize logging for this document
        self.logger = TranslationLogger(self.job_id, document.user_base_filename)
        self.logger.initialize_session()
        
        if not document.segments:
            print("No segments to translate. Exiting.")
            return
        
        # Define core narrative style
        core_narrative_style = self._define_core_style(document)
        self.logger.log_core_narrative_style(core_narrative_style)
        
        # Translate segments
        total_segments = len(document.segments)
        for i, segment_info in enumerate(tqdm(document.segments, desc="Translating Segments")):
            segment_index = i + 1
            
            # Update progress
            self.progress_tracker.update_progress(i, total_segments)
            
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
            context_data = {
                'style_deviation': style_deviation,
                'contextual_glossary': contextual_glossary,
                'full_glossary': document.glossary,
                'character_styles': document.character_styles,
                'immediate_context_source': immediate_context_source,
                'immediate_context_ko': immediate_context_ko
            }
            self.logger.log_segment_context(segment_index, context_data)
            self.logger.log_translation_prompt(segment_index, prompt)
            
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
        self.progress_tracker.finalize_translation(
            document.segments, document.translated_segments, document.glossary
        )
        
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
                error_msg = f"Translation failed for segment {segment_index}. Error: {e}"
                print(error_msg)
                
                # Log error using centralized logger
                if self.logger:
                    self.logger.log_error(e, segment_index, "translate_segment")
                
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
        
        # Log using centralized logger
        if self.logger:
            self.logger.log_error(e, segment_index, "prohibited_content_final")
        
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
            
            # Log the final failure
            if self.logger:
                self.logger.log_error(final_e, segment_index, "minimal_prompt_failed")
            
            raise e from final_e
    
    
    
    
