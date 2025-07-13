import re
import os
import time
from tqdm import tqdm
from .models.gemini import GeminiModel
from ..prompts.builder import PromptBuilder
from ..config.builder import DynamicConfigBuilder
from .job import TranslationJob
from ..prompts.manager import PromptManager
from ..errors import ProhibitedException
from ..errors import prohibited_content_logger
from ..utils.retry import retry_on_prohibited_segment
from ..prompts.sanitizer import PromptSanitizer
from sqlalchemy.orm import Session
# Import crud only if backend is available
try:
    from backend import crud
except ImportError:
    crud = None

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
        """
        Translates all segments in a given TranslationJob.
        """
        prompt_log_dir = "debug_prompts"
        context_log_dir = "context_log"
        os.makedirs(prompt_log_dir, exist_ok=True)
        os.makedirs(context_log_dir, exist_ok=True)
        
        # job_id를 파일명에 포함하여 고유성 보장
        prompt_log_path = os.path.join(prompt_log_dir, f"prompts_job_{self.job_id}_{job.base_filename}.txt")
        context_log_path = os.path.join(context_log_dir, f"context_job_{self.job_id}_{job.base_filename}.txt")

        with open(prompt_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {job.base_filename}\n\n")
        with open(context_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {job.base_filename}\n\n")

        if not job.segments:
            print("No segments to translate. Exiting.")
            return

        core_narrative_style = ""
        if self.initial_core_style:
            # 사용자가 제공한 포맷팅된 스타일을 그대로 사용
            print("\n--- Using User-Defined Core Narrative Style... ---")
            core_narrative_style = self.initial_core_style
            print(f"Style defined as: {core_narrative_style}")
        else:
            # 기존 방식대로 스타일 분석
            core_narrative_style = self._define_core_style(job.segments[0].text, job.base_filename)
        
        with open(context_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- Core Narrative Style Defined ---\n")
            f.write(f"{core_narrative_style}\n")
            f.write("="*50 + "\n\n")

        total_segments = len(job.segments)
        for i, segment_info in enumerate(tqdm(job.segments, desc="Translating Segments")):
            segment_index = i + 1
            
            # --- Progress Update ---
            progress = int((i / total_segments) * 100)
            if crud and self.db and self.job_id:
                crud.update_job_progress(self.db, self.job_id, progress)
            # -----------------------

            updated_glossary, updated_styles, style_deviation = self.dyn_config_builder.build_dynamic_guides(
                segment_text=segment_info.text,
                core_narrative_style=core_narrative_style,
                current_glossary=job.glossary,
                current_character_styles=job.character_styles,
                job_base_filename=job.base_filename,
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

            # 5. Generate translation with retry logic
            translated_text = ""
            soft_retry_attempts = 3
            original_prompt = prompt
            
            for retry_attempt in range(soft_retry_attempts + 1):
                try:
                    if retry_attempt > 0:
                        # Create softer prompt for retry
                        prompt = PromptSanitizer.create_softer_prompt(original_prompt, retry_attempt)
                        print(f"\nRetrying with softer prompt (attempt {retry_attempt}/{soft_retry_attempts})...")
                        time.sleep(2)  # Brief delay between retries
                    
                    # The gemini_model's generate_text will handle retries for retriable errors
                    # and will immediately raise an exception for non-retriable ones.
                    model_response = self.gemini_api.generate_text(prompt) 
                    translated_text = _extract_translation_from_response(model_response)
                    
                    if retry_attempt > 0:
                        print(f"Successfully translated with softer prompt on attempt {retry_attempt}")
                    break  # Success, exit retry loop
                    
                except ProhibitedException as e:
                    if retry_attempt < soft_retry_attempts:
                        # Will retry with softer prompt
                        print(f"\nProhibitedException caught: {e}")
                        print("Will retry with a softer prompt...")
                        continue
                    else:
                        # All retries exhausted
                        # Handle prohibited content using the centralized logger
                        e.source_text = segment_info.text
                        e.context = {
                            'segment_index': segment_index,
                            'glossary': contextual_glossary,
                            'character_styles': job.character_styles,
                            'style_deviation': style_deviation,
                            'soft_retry_attempts': soft_retry_attempts
                        }
                        log_path = prohibited_content_logger.log_prohibited_content(e, job.base_filename, segment_index)
                        print(f"\nAll soft retry attempts failed. Translation blocked for segment {segment_index}.")
                        print(f"Log saved to: {log_path}")
                        
                        # Try minimal prompt as last resort
                        try:
                            print("Attempting minimal prompt as last resort...")
                            minimal_prompt = PromptSanitizer.create_minimal_prompt(segment_info.text, "Korean")
                            model_response = self.gemini_api.generate_text(minimal_prompt)
                            translated_text = _extract_translation_from_response(model_response)
                            print("Successfully translated with minimal prompt.")
                        except:
                            translated_text = f"[TRANSLATION_BLOCKED: Content safety filter triggered]"

                except Exception as e:
                    error_message = str(e)
                    print(f"Translation failed for segment {segment_index}. Error: {error_message}")
                    translated_text = f"[TRANSLATION_FAILED: {error_message}]"
                
                # If it's a non-retriable error, we want to stop the entire job.
                if "API key not valid" in error_message or "PermissionDenied" in error_message or "InvalidArgument" in error_message:
                    print("Non-retriable error detected. Aborting the entire translation job.")
                    # We re-raise the exception to be caught by the top-level handler in main.py
                    # which will then mark the entire job as FAILED.
                    raise e

            # 6. Save the result
            job.append_translated_segment(translated_text, segment_info)

        job.save_final_output()

        print(f"\n--- Translation Complete! ---")
        print(f"Output: {job.output_filename}")

    def _define_core_style(self, sample_text: str, job_base_filename: str = "unknown") -> str:
        """Analyzes the first segment to define the core narrative style for the novel."""
        print("\n--- Defining Core Narrative Style... ---")
        try:
            prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=sample_text)
            style = self.gemini_api.generate_text(prompt)
            print(f"Style defined as: {style}")
            return style
        except ProhibitedException as e:
            # Log the prohibited content error
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="core_style_definition",
                prompt=prompt,
                source_text=sample_text,
                error_message=str(e),
                job_filename=job_base_filename
            )
            print(f"Warning: Core style definition blocked by safety settings. Log saved to: {log_path}")
            print("Falling back to default narrative style.")
            return "A standard, neutral literary style ('평서체')."
        except Exception as e:
            print(f"Warning: Could not define narrative style. Falling back to default. Error: {e}")
            return "A standard, neutral literary style ('평서체')."

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