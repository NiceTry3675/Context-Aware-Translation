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
from .illustration import IllustrationGenerator
from .usage_tracker import TokenUsageCollector
from ..prompts.builder import PromptBuilder
from ..prompts.manager import PromptManager
from ..prompts.sanitizer import PromptSanitizer
from ..config.builder import DynamicConfigBuilder
from ..schemas.illustration import IllustrationConfig, IllustrationBatch
from shared.errors import ProhibitedException, TranslationError
from shared.errors import ProhibitedContentLogger
from shared.utils.logging import TranslationLogger


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
                 style_model_api: Optional[GeminiModel | OpenRouterModel] = None,
                 illustration_config: Optional[IllustrationConfig] = None,
                 illustration_api_key: Optional[str] = None,
                 usage_collector: Optional[TokenUsageCollector] = None):
        """
        Initialize the translation pipeline.
        
        Args:
            gemini_api: The Gemini API model instance
            dyn_config_builder: Dynamic configuration builder for glossary and styles
            db: Optional database session for progress tracking
            job_id: Optional job ID for database updates
            initial_core_style: Optional pre-defined core narrative style
            style_model_api: Optional different model for style analysis
            illustration_config: Optional configuration for illustration generation
            illustration_api_key: Optional API key for illustration generation
        """
        self.gemini_api = gemini_api
        self.dyn_config_builder = dyn_config_builder
        self.prompt_builder = PromptBuilder(PromptManager.MAIN_TRANSLATION)
        # Allow a different model for style analysis if provided
        self.style_analyzer = StyleAnalyzer(style_model_api or gemini_api, job_id)
        self.progress_tracker = ProgressTracker(db, job_id)
        self.initial_core_style = initial_core_style
        self.usage_collector = usage_collector
        
        # Logger will be initialized with document filename later
        self.job_id = job_id
        self.logger = None
        
        # Initialize illustration generator if configured
        self.illustration_config = illustration_config
        self.illustration_generator = None
        if illustration_config and illustration_config.enabled and illustration_api_key:
            try:
                self.illustration_generator = IllustrationGenerator(
                    api_key=illustration_api_key,
                    job_id=job_id,
                    enable_caching=illustration_config.cache_enabled
                )
                print("Illustration generation enabled")
            except ImportError as e:
                print(f"Warning: Could not initialize illustration generator: {e}")
                self.illustration_generator = None
    
    
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
            token_events = self.usage_collector.events() if self.usage_collector else None
            self.progress_tracker.record_usage_log(
                original_text, translated_text_final,
                model_name, error_type,
                token_events=token_events
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
        
        # Initialize job-specific prohibited content logger
        self.prohibited_logger = ProhibitedContentLogger(job_id=self.job_id)
        
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
            # Get previous context for world atmosphere analysis
            previous_context = None
            if i > 0 and document.segments:
                previous_context = document.segments[i-1].text
            
            updated_glossary, updated_styles, style_deviation, world_atmosphere = self._build_dynamic_guides(
                document, segment_info, segment_index, core_narrative_style, previous_context
            )

            # Save world_atmosphere to segment_info for later use (e.g., illustrations)
            if world_atmosphere:
                segment_info.world_atmosphere = world_atmosphere.model_dump()

            # Prepare context for translation
            contextual_glossary = self._get_contextual_glossary(updated_glossary, segment_info.text)
            immediate_context_source = get_segment_ending(document.get_previous_segment(i), max_chars=1500)
            immediate_context_ko = get_segment_ending(document.get_previous_translation(i), max_chars=500)
            
            # Build translation prompt
            prompt = self._build_translation_prompt(
                segment_info, contextual_glossary, updated_styles,
                core_narrative_style, style_deviation,
                immediate_context_source, immediate_context_ko, world_atmosphere
            )
            
            # Log context and prompt
            context_data = {
                'style_deviation': style_deviation,
                'world_atmosphere': world_atmosphere.to_prompt_format() if world_atmosphere else None,
                'contextual_glossary': contextual_glossary,
                'full_glossary': document.glossary,
                'character_styles': document.character_styles,
                'immediate_context_source': immediate_context_source,
                'immediate_context_ko': immediate_context_ko
            }
            self.logger.log_segment_context(segment_index, context_data)
            self.logger.log_translation_prompt(segment_index, prompt)
            
            # Track segment translation time
            segment_start_time = time.time()

            # Translate segment with retries
            translated_text = self._translate_segment_with_retries(
                prompt, segment_info, segment_index, document,
                contextual_glossary, style_deviation
            )

            # Calculate translation time
            segment_translation_time = time.time() - segment_start_time

            # Log segment input/output
            if self.logger:
                metadata = {
                    "world_atmosphere": world_atmosphere.model_dump() if world_atmosphere else None,
                    "glossary_used": contextual_glossary,
                    "style_deviation": style_deviation,
                    "translation_time": segment_translation_time,
                    "chapter_title": segment_info.chapter_title,
                    "chapter_filename": segment_info.chapter_filename
                }
                self.logger.log_segment_io(
                    segment_index=segment_index,
                    source_text=segment_info.text,
                    translated_text=translated_text,
                    metadata=metadata
                )

            # Append translation and save progress
            document.append_translated_segment(translated_text, segment_info)
            
            # Generate illustration if enabled
            if self.illustration_generator and self._should_generate_illustration(segment_info, i):
                self._generate_segment_illustration(
                    segment_info, i, document.glossary,
                    core_narrative_style, style_deviation, world_atmosphere,
                    character_styles=updated_styles
                )
            
            document.save_partial_output()
        
        # Persist segments to DB before final file save to avoid DB omissions
        self.progress_tracker.finalize_translation(
            document.segments, document.translated_segments, document.glossary
        )

        # Save final output (file I/O after DB write)
        document.save_final_output()
        
        # Generate illustration batch report if illustrations were created
        if self.illustration_generator:
            illustration_metadata = self.illustration_generator.get_illustration_metadata()
            self.logger.log_debug(f"Illustration generation complete: {illustration_metadata}")
        
        # Finalization already performed above to prevent omissions
        
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
                             segment_index: int, core_narrative_style: str,
                             previous_context: Optional[str] = None) -> tuple:
        """
        Build dynamic glossary and character style guides for the segment.
        
        Returns:
            Tuple of (updated_glossary, updated_styles, style_deviation, world_atmosphere)
        """
        updated_glossary, updated_styles, style_deviation, world_atmosphere = self.dyn_config_builder.build_dynamic_guides(
            segment_text=segment_info.text,
            core_narrative_style=core_narrative_style,
            current_glossary=document.glossary,
            current_character_styles=document.character_styles,
            job_base_filename=document.user_base_filename,
            segment_index=segment_index,
            previous_context=previous_context
        )
        
        # Update document with new guides
        document.glossary = updated_glossary
        document.character_styles = updated_styles
        
        return updated_glossary, updated_styles, style_deviation, world_atmosphere
    
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
                                 immediate_context_ko: str, world_atmosphere=None) -> str:
        """Build the translation prompt for a segment."""
        # Add world atmosphere to core narrative style if available
        enhanced_narrative_style = core_narrative_style
        if world_atmosphere:
            enhanced_narrative_style = f"{core_narrative_style}\n\n{world_atmosphere.to_prompt_format()}"
        
        return self.prompt_builder.build_translation_prompt(
            core_narrative_style=enhanced_narrative_style,
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
        
        log_path = self.prohibited_logger.log_prohibited_content(
            e, document.user_base_filename, segment_index
        )
        print(f"\nAll soft retry attempts failed. Log saved to: {log_path}")
        
        try:
            print("Attempting minimal prompt as last resort...")
            minimal_prompt = PromptSanitizer.create_minimal_prompt(segment_info.text, "Korean")
            model_response = self.gemini_api.generate_text(minimal_prompt)
            translated_text = _extract_translation_from_response(model_response)

            # Log segment with error recovery info
            if self.logger:
                metadata = {
                    "error_recovered": True,
                    "error_type": "ProhibitedContent",
                    "error_message": str(e),
                    "soft_retry_attempts": soft_retry_attempts,
                    "used_minimal_prompt": True
                }
                self.logger.log_segment_io(
                    segment_index=segment_index,
                    source_text=segment_info.text,
                    translated_text=translated_text,
                    metadata=metadata
                )

            return translated_text
        except Exception as final_e:
            print(f"Minimal prompt also failed: {final_e}")

            # Log segment failure
            if self.logger:
                self.logger.log_segment_io(
                    segment_index=segment_index,
                    source_text=segment_info.text,
                    translated_text=None,
                    error=f"Unrecoverable error: {str(final_e)}"
                )
                self.logger.log_error(final_e, segment_index, "minimal_prompt_failed")

            raise e from final_e
    
    def _should_generate_illustration(self, segment_info: Any, segment_index: int) -> bool:
        """
        Determine if an illustration should be generated for this segment.
        
        Args:
            segment_info: The segment information
            segment_index: Index of the current segment
            
        Returns:
            Boolean indicating if illustration should be generated
        """
        if not self.illustration_config or not self.illustration_config.enabled:
            return False
        
        # Check maximum illustrations limit
        if self.illustration_config.max_illustrations:
            current_count = len(self.illustration_generator.cache_manager.cache) if self.illustration_generator and self.illustration_generator.cache_manager.cache else 0
            if current_count >= self.illustration_config.max_illustrations:
                return False
        
        # Check minimum segment length
        if len(segment_info.text) < self.illustration_config.min_segment_length:
            return False
        
        # Check if we should skip dialogue-heavy segments
        if self.illustration_config.skip_dialogue_heavy:
            # Simple heuristic: count quotation marks
            quote_count = segment_info.text.count('"') + segment_info.text.count("'")
            if quote_count > len(segment_info.text) / 50:  # More than 1 quote per 50 chars
                return False
        
        # Check segments_per_illustration setting
        if self.illustration_config.segments_per_illustration > 1:
            # Only generate for every Nth segment
            if segment_index % self.illustration_config.segments_per_illustration != 0:
                return False
        
        return True
    
    def _generate_segment_illustration(self, segment_info: Any, segment_index: int,
                                     glossary: Dict[str, str], core_style: str,
                                     style_deviation: str, world_atmosphere=None,
                                     character_styles: Optional[Dict[str, str]] = None):
        """
        Generate an illustration for the current segment.

        Args:
            segment_info: The segment information
            segment_index: Index of the current segment
            glossary: Current glossary
            core_style: Core narrative style
            style_deviation: Style deviation for this segment
            world_atmosphere: World and atmosphere analysis for the segment
            character_styles: Optional character styles dictionary
        """
        if not self.illustration_generator:
            return
        
        try:
            # Build style hints from configuration and narrative style
            style_hints = self.illustration_config.style_hints
            if not style_hints and core_style:
                style_hints = f"Literary illustration matching: {core_style[:100]}"
            
            # Generate the illustration
            illustration_path, prompt = self.illustration_generator.generate_illustration(
                segment_text=segment_info.text,
                segment_index=segment_index,
                style_hints=style_hints,
                glossary=glossary,
                world_atmosphere=world_atmosphere,
                character_styles=character_styles
            )
            
            if illustration_path:
                # Update segment info with illustration data
                segment_info.illustration_path = illustration_path
                segment_info.illustration_prompt = prompt
                segment_info.illustration_status = "generated"
                
                print(f"✓ Generated illustration for segment {segment_index}")
                
                # Log the generation
                if self.logger:
                    self.logger.log_debug(
                        f"Illustration generated for segment {segment_index}: {illustration_path}"
                    )
            else:
                segment_info.illustration_status = "failed"
                print(f"✗ Failed to generate illustration for segment {segment_index}")
                
        except Exception as e:
            segment_info.illustration_status = "failed"
            print(f"Error generating illustration for segment {segment_index}: {e}")
            if self.logger:
                self.logger.log_error(e, segment_index, "illustration_generation")
    
    
    
