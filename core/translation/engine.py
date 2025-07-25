import re
import os
import time
from tqdm import tqdm
from .models.gemini import GeminiModel
from ..prompts.builder import PromptBuilder
from ..config.builder import DynamicConfigBuilder
from .job import TranslationJob
from ..prompts.manager import PromptManager
from ..errors import ProhibitedException, TranslationError
from ..errors import prohibited_content_logger
from ..utils.retry import retry_on_prohibited_segment
from ..prompts.sanitizer import PromptSanitizer
from .style_analyzer import extract_sample_text, analyze_narrative_style_with_api
from sqlalchemy.orm import Session
# Import crud and schemas only if backend is available
try:
    from backend import crud, schemas
except ImportError:
    crud = None
    schemas = None

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

class TranslationEngine:
    """
    Orchestrates the entire translation process, segment by segment.
    """
    def __init__(self, gemini_api: GeminiModel, dyn_config_builder: DynamicConfigBuilder, db: Session, job_id: int, initial_core_style: str = None):
        self.gemini_api = gemini_api
        self.dyn_config_builder = dyn_config_builder
        self.prompt_builder = PromptBuilder(PromptManager.MAIN_TRANSLATION)
        self.db = db
        self.job_id = job_id
        self.initial_core_style = initial_core_style

    def translate_job(self, job: TranslationJob):
        start_time = time.time()
        error_type = None
        original_text = ""
        translated_text_final = ""
        try:
            self._translate_job_internal(job)
            original_text = "\n".join(s.text for s in job.segments)
            translated_text_final = "\n".join(job.translated_segments)
        except TranslationError as e:
            error_type = e.__class__.__name__
            # Re-raise the exception to be handled by the main runner
            raise e
        finally:
            if crud and self.db and self.job_id:
                end_time = time.time()
                duration = int(end_time - start_time)
                
                log_data = schemas.TranslationUsageLogCreate(
                    job_id=self.job_id,
                    original_length=len(original_text),
                    translated_length=len(translated_text_final),
                    translation_duration_seconds=duration,
                    model_used=self.gemini_api.model_name,
                    error_type=error_type
                )
                crud.create_translation_usage_log(self.db, log_data)
                print("\n--- Usage log has been recorded. ---")


    def _translate_job_internal(self, job: TranslationJob):
        """
        Internal method to handle the main translation logic.
        """
        prompt_log_dir = "debug_prompts"
        context_log_dir = "context_log"
        os.makedirs(prompt_log_dir, exist_ok=True)
        os.makedirs(context_log_dir, exist_ok=True)
        
        prompt_log_path = os.path.join(prompt_log_dir, f"prompts_job_{self.job_id}_{job.user_base_filename}.txt")
        context_log_path = os.path.join(context_log_dir, f"context_job_{self.job_id}_{job.user_base_filename}.txt")

        with open(prompt_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {job.user_base_filename}\n\n")
        with open(context_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {job.user_base_filename}\n\n")

        if not job.segments:
            print("No segments to translate. Exiting.")
            return

        core_narrative_style = ""
        if self.initial_core_style:
            print("\n--- Using User-Defined Core Narrative Style... ---")
            core_narrative_style = self.initial_core_style
            print(f"Style defined as: {core_narrative_style}")
        else:
            core_narrative_style = self._define_core_style(job.filepath, job.user_base_filename)
        
        with open(context_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- Core Narrative Style Defined ---\n")
            f.write(f"{core_narrative_style}\n")
            f.write("="*50 + "\n\n")

        total_segments = len(job.segments)
        for i, segment_info in enumerate(tqdm(job.segments, desc="Translating Segments")):
            segment_index = i + 1
            
            progress = int((i / total_segments) * 100)
            if crud and self.db and self.job_id:
                crud.update_job_progress(self.db, self.job_id, progress)

            updated_glossary, updated_styles, style_deviation = self.dyn_config_builder.build_dynamic_guides(
                segment_text=segment_info.text,
                core_narrative_style=core_narrative_style,
                current_glossary=job.glossary,
                current_character_styles=job.character_styles,
                job_base_filename=job.user_base_filename,
                segment_index=segment_index
            )
            job.glossary = updated_glossary
            job.character_styles = updated_styles

            contextual_glossary = {
                key: value for key, value in job.glossary.items() 
                if re.search(r'\b' + re.escape(key) + r'\b', segment_info.text, re.IGNORECASE)
            }
            
            immediate_context_en = get_segment_ending(job.get_previous_segment(i), max_chars=1500)
            immediate_context_ko = get_segment_ending(job.get_previous_translation(i), max_chars=500)
            
            prompt = self.prompt_builder.build_translation_prompt(
                core_narrative_style=core_narrative_style,
                style_deviation_info=style_deviation,
                glossary=contextual_glossary,
                character_styles=job.character_styles,
                source_segment=segment_info.text,
                prev_segment_en=immediate_context_en,
                prev_segment_ko=immediate_context_ko,
                protagonist_name=self.dyn_config_builder.character_style_manager.protagonist_name
            )

            self._write_context_log(
                log_path=context_log_path,
                segment_index=segment_index,
                job=job,
                contextual_glossary=contextual_glossary,
                immediate_context_en=immediate_context_en,
                immediate_context_ko=immediate_context_ko,
                style_deviation=style_deviation
            )
            with open(prompt_log_path, 'a', encoding='utf-8') as f:
                f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n")
                f.write(prompt)
                f.write("\n\n" + "="*50 + "\n\n")

            translated_text = self._translate_segment_with_retries(prompt, segment_info, segment_index, job, contextual_glossary, style_deviation)
            job.append_translated_segment(translated_text, segment_info)

            # Save intermediate progress after each segment
            job.save_partial_output()

        job.save_final_output()

        print(f"\n--- Translation Complete! ---")
        print(f"Output: {job.output_filename}")

    def _translate_segment_with_retries(self, original_prompt: str, segment_info, segment_index: int, job: TranslationJob, contextual_glossary: dict, style_deviation: str) -> str:
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
                    e.source_text = segment_info.text
                    e.context = {
                        'segment_index': segment_index,
                        'glossary': contextual_glossary,
                        'character_styles': job.character_styles,
                        'style_deviation': style_deviation,
                        'soft_retry_attempts': soft_retry_attempts
                    }
                    log_path = prohibited_content_logger.log_prohibited_content(e, job.user_base_filename, segment_index)
                    print(f"\nAll soft retry attempts failed. Log saved to: {log_path}")
                    
                    try:
                        print("Attempting minimal prompt as last resort...")
                        minimal_prompt = PromptSanitizer.create_minimal_prompt(segment_info.text, "Korean")
                        model_response = self.gemini_api.generate_text(minimal_prompt)
                        return _extract_translation_from_response(model_response)
                    except Exception as final_e:
                        print(f"Minimal prompt also failed: {final_e}")
                        # Raise the original ProhibitedException to be logged
                        raise e from final_e

            except TranslationError as e:
                # For other translation errors, we re-raise them to be caught by the main job handler
                print(f"Translation failed for segment {segment_index}. Error: {e}")
                raise e

        # This part should not be reached if retries are handled correctly
        raise TranslationError(f"Failed to translate segment {segment_index} after all retries.")

    def _define_core_style(self, file_path: str, job_base_filename: str = "unknown") -> str:
        """Analyzes the first segment to define the core narrative style for the novel."""
        print("\n--- Defining Core Narrative Style... ---")
        # Extract the sample text using the centralized function
        sample_text = extract_sample_text(file_path, method="first_segment", count=15000)
        try:
            style = analyze_narrative_style_with_api(sample_text, self.gemini_api, job_base_filename)
            print(f"Style defined as: {style}")
            return style
        except Exception as e:
            print(f"Warning: Could not define narrative style. Falling back to default. Error: {e}")
            raise TranslationError(f"Failed to define core style: {e}") from e

    def _write_context_log(self, log_path: str, segment_index: int, job: TranslationJob, contextual_glossary: dict, immediate_context_en: str, immediate_context_ko: str, style_deviation: str):
        """Writes a human-readable summary of the context to a log file."""
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
            if job.glossary:
                for key, value in job.glossary.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- Empty\n")
            f.write("\n")
            f.write("### Cumulative Character Styles:\n")
            if job.character_styles:
                for key, value in job.character_styles.items():
                    f.write(f"- {key}: {value}\n")
            else:
                f.write("- Empty\n")
            f.write("\n")
            f.write("### Immediate language Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_en or 'N/A'}\n\n")
            f.write("### Immediate Korean Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_ko or 'N/A'}\n\n")
            f.write("="*50 + "\n\n")