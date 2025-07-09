import re
import os
from tqdm import tqdm
from .gemini_model import GeminiModel
from .prompt_builder import PromptBuilder
from .dynamic_config_builder import DynamicConfigBuilder
from .translation_job import TranslationJob
from .prompt_manager import PromptManager

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

        # Define the core narrative style using the first segment
        if not job.segments:
            print("No segments to translate. Exiting.")
            return
        core_narrative_style = self._define_core_style(job.segments[0].text)
        
        # Log the defined style
        with open(context_log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- Core Narrative Style Defined ---\n")
            f.write(f"{core_narrative_style}\n")
            f.write("="*50 + "\n\n")

        for i, segment_info in enumerate(tqdm(job.segments, desc="Translating Segments")):
            segment_index = i + 1
            segment_content = segment_info.text
            # print(f"\n\n--- Processing Segment {segment_index}/{len(job.segments)} ---")

            # 1. Build dynamic guides using the orchestrated builder
            updated_glossary, updated_styles, style_deviation = self.dyn_config_builder.build_dynamic_guides(
                segment_text=segment_content,
                core_narrative_style=core_narrative_style,
                current_glossary=job.glossary,
                current_character_styles=job.character_styles,
                job_base_filename=job.base_filename,
                segment_index=segment_index
            )
            job.glossary = updated_glossary
            job.character_styles = updated_styles

            # 2. Filter glossary for the current segment
            contextual_glossary = {
                key: value for key, value in job.glossary.items() 
                if re.search(r'\b' + re.escape(key) + r'\b', segment_content, re.IGNORECASE)
            }
            
            # 3. Build the final prompt
            immediate_context_en = get_segment_ending(job.get_previous_segment(i), max_chars=1500)
            immediate_context_ko = get_segment_ending(job.get_previous_translation(i), max_chars=500)
            
            prompt = self.prompt_builder.build_translation_prompt(
                core_narrative_style=core_narrative_style,
                style_deviation_info=style_deviation,
                glossary=contextual_glossary, # Use the filtered glossary
                character_styles=job.character_styles,
                source_segment=segment_content,
                prev_segment_en=immediate_context_en,
                prev_segment_ko=immediate_context_ko
            )

            # 4. Log the context and prompt for debugging
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

            # 5. Generate translation
            try:
                model_response = self.gemini_api.generate_text(prompt)
                translated_text = _extract_translation_from_response(model_response)
                # print(f"Segment {segment_index} translated successfully.")
            except Exception as e:
                error_message = str(e)
                print(f"Translation failed for segment {segment_index}. Error: {error_message}")
                translated_text = f"[TRANSLATION_FAILED: {error_message}]"
                
                # Log the problematic prompt and content
                if "PROHIBITED_CONTENT" in error_message.upper():
                    error_log_path = os.path.join(prompt_log_dir, f"error_prompt_{job.base_filename}_{segment_index}.txt")
                    with open(error_log_path, 'w', encoding='utf-8') as f:
                        f.write(f"# PROHIBITED CONTENT ERROR LOG FOR SEGMENT {segment_index}\n\n")
                        f.write(f"--- SOURCE SEGMENT ---\n{segment_content}\n\n")
                        f.write(f"--- FULL PROMPT ---\n{prompt}")
                    print(f"Problematic prompt for segment {segment_index} saved to: {error_log_path}")
            
            # 6. Save the result
            job.append_translated_segment(translated_text, segment_info)

        job.save_final_output()

        print(f"\n--- Translation Complete! ---")
        print(f"Output: {job.output_filename}")

    def _define_core_style(self, sample_text: str) -> str:
        """Analyzes the first segment to define the core narrative style for the novel."""
        print("\n--- Defining Core Narrative Style... ---")
        try:
            prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=sample_text)
            style = self.gemini_api.generate_text(prompt)
            print(f"Style defined as: {style}")
            return style
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
