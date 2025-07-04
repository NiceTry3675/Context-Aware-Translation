import re
import os
from tqdm import tqdm
from gemini_model import GeminiModel
from prompt_builder import PromptBuilder
from dynamic_config_builder import DynamicConfigBuilder
from translation_job import TranslationJob
from prompt_manager import PromptManager

def get_segment_ending(segment_text: str, max_chars: int) -> str:
    """
    Extracts the very end of a text segment to be used as immediate context,
    ensuring the length does not exceed max_chars and avoiding mid-word cuts.
    """
    if not segment_text or max_chars <= 0:
        return ""

    # If the text is already short enough, return it as is.
    if len(segment_text) <= max_chars:
        return segment_text

    # Take the last `max_chars` characters as a starting point.
    context = segment_text[-max_chars:]

    # Find the first space from the beginning of the truncated context
    # to avoid starting with a partial word.
    first_space_pos = context.find(' ')
    if first_space_pos > -1:
        # Return the text from the first full word onwards.
        return context[first_space_pos+1:]
    
    # If no space is found (e.g., one very long word or CJK text), return the truncated context.
    return context

def _extract_translation_from_response(response: str) -> str:
    """Returns the model's response, stripping any leading/trailing whitespace."""
    return response.strip()

class TranslationEngine:
    """
    Orchestrates the entire translation process, segment by segment.
    """
    def __init__(self, gemini_api: GeminiModel, dyn_config_builder: DynamicConfigBuilder):
        self.gemini_api = gemini_api
        self.dyn_config_builder = dyn_config_builder
        self.prompt_builder = PromptBuilder(PromptManager.MAIN_TRANSLATION)

    def translate_job(self, job: TranslationJob):
        """
        Translates all segments in a given TranslationJob.
        """
        # Setup directories for logs
        prompt_log_dir = "debug_prompts"
        context_log_dir = "context_log"
        os.makedirs(prompt_log_dir, exist_ok=True)
        os.makedirs(context_log_dir, exist_ok=True)
        
        prompt_log_path = os.path.join(prompt_log_dir, f"prompts_{job.base_filename}.txt")
        context_log_path = os.path.join(context_log_dir, f"context_{job.base_filename}.txt")

        with open(prompt_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {job.base_filename}\n\n")
        with open(context_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {job.base_filename}\n\n")

        for i, segment_content in enumerate(tqdm(job.segments, desc="Translating Segments")):
            segment_index = i + 1
            print(f"\n\n--- Processing Segment {segment_index}/{len(job.segments)} ---")

            # 1. Build dynamic guides using the orchestrated builder
            updated_glossary, updated_styles = self.dyn_config_builder.build_dynamic_guides(
                segment_content,
                job.glossary,
                job.character_styles
            )
            job.glossary = updated_glossary
            job.character_styles = updated_styles
            
            # 2. Build the final prompt
            immediate_context_en = get_segment_ending(job.get_previous_segment(i), max_chars=1500)
            immediate_context_ko = get_segment_ending(job.get_previous_translation(i), max_chars=500)
            
            prompt = self.prompt_builder.build_translation_prompt(
                glossary=job.glossary,
                character_styles=job.character_styles,
                source_segment=segment_content,
                prev_segment_en=immediate_context_en,
                prev_segment_ko=immediate_context_ko
            )

            # 3. Log the context and prompt for debugging
            self._write_context_log(
                log_path=context_log_path,
                segment_index=segment_index,
                job=job,
                immediate_context_en=immediate_context_en,
                immediate_context_ko=immediate_context_ko
            )
            with open(prompt_log_path, 'a', encoding='utf-8') as f:
                f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n")
                f.write(prompt)
                f.write("\n\n" + "="*50 + "\n\n")

            # 4. Generate translation
            try:
                model_response = self.gemini_api.generate_text(prompt)
                translated_text = _extract_translation_from_response(model_response)
                print(f"Segment {segment_index} translated successfully.")
            except Exception as e:
                print(f"Translation failed for segment {segment_index}. Skipping. Error: {e}")
                translated_text = f"[TRANSLATION_FAILED: {e}]"
            
            # 5. Save the result
            job.append_translated_segment(translated_text)

        print(f"\n--- Translation Complete! ---")
        print(f"Output: {job.output_filename}")
        print(f"Logs: {prompt_log_path}")
        print(f"Context: {context_log_path}")

    def _write_context_log(self, log_path: str, segment_index: int, job: TranslationJob, immediate_context_en: str, immediate_context_ko: str):
        """Writes a human-readable summary of the context to a log file."""
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- CONTEXT FOR SEGMENT {segment_index} ---\n\n")
            
            f.write("### Cumulative Glossary:\n")
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

            f.write("### Immediate English Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_en or 'N/A'}\n\n")

            f.write("### Immediate Korean Context (Previous Segment Ending):\n")
            f.write(f"{immediate_context_ko or 'N/A'}\n\n")

            f.write("="*50 + "\n\n")
