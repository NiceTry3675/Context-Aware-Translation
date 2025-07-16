import re
import os
import time
from tqdm import tqdm
from .models.gemini import GeminiModel
from ..prompts.builder import PromptBuilder
from ..config.builder import DynamicConfigBuilder
from .job import TranslationJob, SegmentInfo
from ..prompts.manager import PromptManager
from ..errors import ProhibitedException, TranslationError
from ..errors import prohibited_content_logger
from ..prompts.sanitizer import PromptSanitizer
from sqlalchemy.orm import Session

try:
    from backend import crud, schemas
except ImportError:
    crud = None
    schemas = None

def get_segment_ending(segment_text: str, max_chars: int) -> str:
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
    return response.strip()

class TranslationEngine:
    def __init__(self, gemini_api: GeminiModel, dyn_config_builder: DynamicConfigBuilder, db: Session, job_id: int, initial_core_style: str = None, resume_from_segment: int = 0, initial_context: dict = None):
        self.gemini_api = gemini_api
        self.dyn_config_builder = dyn_config_builder
        self.prompt_builder = PromptBuilder(PromptManager.MAIN_TRANSLATION)
        self.db = db
        self.job_id = job_id
        self.initial_core_style = initial_core_style
        self.resume_from_segment = resume_from_segment
        self.initial_context = initial_context or {}

    def translate_job(self, job: TranslationJob):
        start_time = time.time()
        error_type = None
        total_original_length = 0
        total_translated_length = 0
        try:
            total_original_length, total_translated_length = self._translate_job_internal(job)
        except TranslationError as e:
            error_type = e.__class__.__name__
            raise e
        finally:
            if crud and self.db and self.job_id:
                end_time = time.time()
                duration = int(end_time - start_time)
                log_data = schemas.TranslationUsageLogCreate(
                    job_id=self.job_id,
                    original_length=total_original_length,
                    translated_length=total_translated_length,
                    translation_duration_seconds=duration,
                    model_used=self.gemini_api.model_name,
                    error_type=error_type
                )
                crud.create_translation_usage_log(self.db, log_data)
                print("\n--- Usage log has been recorded. ---")

    def _translate_job_internal(self, job: TranslationJob) -> tuple[int, int]:
        prompt_log_dir, context_log_dir = "debug_prompts", "context_log"
        os.makedirs(prompt_log_dir, exist_ok=True)
        os.makedirs(context_log_dir, exist_ok=True)
        
        prompt_log_path = os.path.join(prompt_log_dir, f"prompts_job_{self.job_id}_{job.user_base_filename}.txt")
        context_log_path = os.path.join(context_log_dir, f"context_job_{self.job_id}_{job.user_base_filename}.txt")

        # If resuming, open files in append mode, otherwise write mode.
        file_open_mode = 'a' if self.resume_from_segment > 0 else 'w'
        with open(prompt_log_path, file_open_mode, encoding='utf-8') as f_prompt, open(context_log_path, file_open_mode, encoding='utf-8') as f_context:
            if file_open_mode == 'w':
                f_prompt.write(f"# PROMPT LOG FOR: {job.user_base_filename}\n\n")
                f_context.write(f"# CONTEXT LOG FOR: {job.user_base_filename}\n\n")

        segments_list = list(job.stream_segments())
        total_segments = len(segments_list)

        if total_segments == 0:
            print("No segments to translate. Exiting.")
            return 0, 0

        # Restore context if resuming
        if self.initial_context:
            print(f"--- Resuming job, restoring context from segment {self.resume_from_segment} ---")
            job.glossary = self.initial_context.get("glossary", {})
            job.character_styles = self.initial_context.get("character_styles", {})

        first_segment = segments_list[0]
        core_narrative_style = self.initial_core_style or self._define_core_style(first_segment.text, job.user_base_filename)
        if file_open_mode == 'w':
            with open(context_log_path, 'a', encoding='utf-8') as f: 
                f.write(f"--- Core Narrative Style Defined ---\n{core_narrative_style}\n{'='*50}\n\n")

        total_original_length = 0
        total_translated_length = 0
        prev_segment_text = ""
        prev_translated_text = ""

        # Slicing the list to start from the resume point
        segments_to_process = segments_list[self.resume_from_segment:]

        for i, segment_info in enumerate(tqdm(segments_to_process, desc="Translating Segments")):
            segment_index = self.resume_from_segment + i + 1
            
            iterator = self._process_segment(segment_info, segment_index, core_narrative_style, job, context_log_path, prompt_log_path, prev_segment_text, prev_translated_text)
            translated_text = next(iterator)
            job.append_translated_segment(translated_text)

            # Save state and progress to DB after each successful segment translation
            if crud and self.db and self.job_id:
                crud.update_job_state(self.db, self.job_id, segment_index, job.glossary, job.character_styles)
                progress = int((segment_index / total_segments) * 100)
                crud.update_job_progress(self.db, self.job_id, progress)
            
            total_original_length += len(segment_info.text)
            total_translated_length += len(translated_text)
            
            prev_segment_text = segment_info.text
            prev_translated_text = translated_text

        job.finalize_translation()
        print(f"\n--- Translation Complete! ---")
        print(f"Output: {job.output_filename}")
        return total_original_length, total_translated_length

    def _process_segment(self, segment_info: SegmentInfo, segment_index: int, core_narrative_style: str, job: TranslationJob, context_log_path: str, prompt_log_path: str, prev_segment_text: str, prev_translated_text: str):
        updated_glossary, updated_styles, style_deviation = self.dyn_config_builder.build_dynamic_guides(
            segment_text=segment_info.text, core_narrative_style=core_narrative_style,
            current_glossary=job.glossary, current_character_styles=job.character_styles,
            job_base_filename=job.user_base_filename, segment_index=segment_index
        )
        job.glossary = updated_glossary
        job.character_styles = updated_styles

        contextual_glossary = {k: v for k, v in job.glossary.items() if re.search(r'\b' + re.escape(k) + r'\b', segment_info.text, re.IGNORECASE)}
        
        immediate_context_en = get_segment_ending(prev_segment_text, max_chars=1500)
        immediate_context_ko = get_segment_ending(prev_translated_text, max_chars=500)
        
        prompt = self.prompt_builder.build_translation_prompt(
            core_narrative_style=core_narrative_style, style_deviation_info=style_deviation,
            glossary=contextual_glossary, character_styles=job.character_styles,
            source_segment=segment_info.text, prev_segment_en=immediate_context_en, prev_segment_ko=immediate_context_ko,
            protagonist_name=self.dyn_config_builder.character_style_manager.protagonist_name
        )

        self._write_context_log(context_log_path, segment_index, job, contextual_glossary, immediate_context_en, immediate_context_ko, style_deviation)
        with open(prompt_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n{prompt}\n\n{'='*50}\n\n")

        translated_text = self._translate_segment_with_retries(prompt, segment_info, segment_index, job, contextual_glossary, style_deviation)
        yield translated_text

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
                if retry_attempt > 0: print(f"Successfully translated with softer prompt on attempt {retry_attempt}")
                return translated_text
            except ProhibitedException as e:
                if retry_attempt < soft_retry_attempts:
                    print(f"\nProhibitedException caught: {e}. Will retry with a softer prompt...")
                    continue
                else:
                    e.source_text = segment_info.text
                    e.context = {
                        'segment_index': segment_index, 'glossary': contextual_glossary,
                        'character_styles': job.character_styles, 'style_deviation': style_deviation,
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
                        raise e from final_e
            except TranslationError as e:
                print(f"Translation failed for segment {segment_index}. Error: {e}")
                raise e
        raise TranslationError(f"Failed to translate segment {segment_index} after all retries.")

    def _define_core_style(self, sample_text: str, job_base_filename: str = "unknown") -> str:
        print("\n--- Defining Core Narrative Style... ---")
        prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=sample_text)
        try:
            style = self.gemini_api.generate_text(prompt)
            print(f"Style defined as: {style}")
            return style
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="core_style_definition", prompt=prompt, source_text=sample_text,
                error_message=str(e), job_filename=job_base_filename
            )
            print(f"Warning: Core style definition blocked. Log: {log_path}. Falling back to default.")
            return "A standard, neutral literary style ('평서체')."
        except Exception as e:
            print(f"Warning: Could not define narrative style. Falling back to default. Error: {e}")
            raise TranslationError(f"Failed to define core style: {e}") from e

    def _write_context_log(self, log_path: str, segment_index: int, job: TranslationJob, contextual_glossary: dict, immediate_context_en: str, immediate_context_ko: str, style_deviation: str):
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- CONTEXT FOR SEGMENT {segment_index} ---\n\n")
            f.write(f"### Narrative Style Deviation:\n{style_deviation}\n\n")
            f.write("### Contextual Glossary (For This Segment):\n")
            f.write("\n".join([f"- {k}: {v}" for k, v in contextual_glossary.items()]) if contextual_glossary else "- None relevant to this segment.")
            f.write("\n\n### Cumulative Glossary (Full):\n")
            f.write("\n".join([f"- {k}: {v}" for k, v in job.glossary.items()]) if job.glossary else "- Empty")
            f.write("\n\n### Cumulative Character Styles:\n")
            f.write("\n".join([f"- {k}: {v}" for k, v in job.character_styles.items()]) if job.character_styles else "- Empty")
            f.write(f"\n\n### Immediate language Context (Previous Segment Ending):\n{immediate_context_en or 'N/A'}\n\n")
            f.write(f"### Immediate Korean Context (Previous Segment Ending):\n{immediate_context_ko or 'N/A'}\n\n{'='*50}\n\n")
