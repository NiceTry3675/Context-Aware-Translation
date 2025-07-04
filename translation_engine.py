import re
import os
from tqdm import tqdm
from gemini_model import GeminiModel
from prompt_builder import PromptBuilder
from dynamic_config_builder import DynamicConfigBuilder
from translation_job import TranslationJob

def get_segment_ending(segment_text: str, max_chars: int = 500) -> str:
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
    """
    Extracts the Korean translation from the structured response.
    """
    match = re.search(r"\[Korean Translation\]:\s*(.*)", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        # Fallback if the model doesn't follow the format perfectly
        return response.strip()

class TranslationEngine:
    """
    Orchestrates the entire translation process, segment by segment.
    """
    def __init__(self, gemini_api: GeminiModel, prompt_builder: PromptBuilder, dyn_config_builder: DynamicConfigBuilder):
        self.gemini_api = gemini_api
        self.prompt_builder = prompt_builder
        self.dyn_config_builder = dyn_config_builder

    def _prepare_static_rules(self, config: dict) -> str:
        """Prepares a simple text block of static rules."""
        # This is the simplified version where character styles are off.
        rules = []
        global_style = config.get('style_guide', {}).get('global', {})
        if global_style:
            rules.append(f"Global Style: {global_style.get('directive_en', 'Not specified.')}")
        return "\n".join(rules) if rules else "No static rules provided."

    def _write_context_log(self, log_file, segment_index, context_data):
        """Writes a human-readable summary of the context to a log file."""
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"--- CONTEXT FOR SEGMENT {segment_index} ---\n\n")
            f.write("### Static Rules Used:\n")
            f.write(f"{context_data['static_rules']}\n\n")
            f.write("### AI-Generated Guidelines Used:\n")
            f.write(f"{context_data['dynamic_guidelines']}\n\n")
            f.write("### Immediate Context Used (English):\n")
            f.write(f"{context_data['immediate_context_en']}\n\n")
            f.write("### Immediate Context Used (Korean):\n")
            f.write(f"{context_data['immediate_context_ko']}\n\n")
            f.write("="*50 + "\n\n")

    def translate_job(self, job: TranslationJob, config: dict):
        """
        Translates all segments in a given TranslationJob.
        """
        style_guide = config.get('style_guide', {})
        core_narrative_voice = style_guide.get("core_narrative_voice", "해라체 (haerache)") # Fallback
        
        # Create directories for logs if they don't exist
        os.makedirs('context_log', exist_ok=True)
        os.makedirs('debug_prompts', exist_ok=True)

        prompt_log_filename = os.path.join('debug_prompts', f"debug_prompts_{job.base_filename}.txt")
        context_log_filename = os.path.join('context_log', f"context_log_{job.base_filename}.txt")
        
        with open(prompt_log_filename, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {job.base_filename}\n\n")
        with open(context_log_filename, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {job.base_filename}\n\n")

        for i, segment_content in enumerate(tqdm(job.segments, desc="Translating Segments")):
            segment_index = i + 1
            print(f"\n\n--- Starting processing for Segment {segment_index}/{len(job.segments)} ---")
            print(f"Segment starts with: '{segment_content[:70].strip()}...'")

            updated_glossary, prompt_guidelines = self.dyn_config_builder.generate_guidelines(
                self.gemini_api,
                segment_content,
                core_narrative_voice,
                job.glossary
            )
            job.glossary = updated_glossary
            
            immediate_context_en = get_segment_ending(job.get_previous_segment(i), max_chars=1500)
            immediate_context_ko = get_segment_ending(job.get_previous_translation(i), max_chars=500)

            # Build the final prompt using the hierarchical guide system
            prompt = self.prompt_builder.build_translation_prompt(
                style_guide=style_guide,
                core_narrative_voice=core_narrative_voice,
                glossary_terms=prompt_guidelines['glossary_terms'],
                style_analysis=prompt_guidelines['style_analysis'],
                source_segment=segment_content,
                prev_segment_en=immediate_context_en
            )

            # Log the context used for debugging and review
            dynamic_guidelines_log = (
                f"""Key Term Translations:
{prompt_guidelines['glossary_terms']}

Style and Tone Analysis:
{prompt_guidelines['style_analysis']}"""
            )
            self._write_context_log(context_log_filename, segment_index, {
                "static_rules": self._prepare_static_rules(config),
                "dynamic_guidelines": dynamic_guidelines_log,
                "immediate_context_en": immediate_context_en,
                "immediate_context_ko": immediate_context_ko
            })

            with open(prompt_log_filename, 'a', encoding='utf-8') as f:
                f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n")
                f.write(prompt)
                f.write("\n\n" + "="*50 + "\n\n")

            try:
                model_response = self.gemini_api.generate_text(prompt)
                translated_text = _extract_translation_from_response(model_response)
                print(f"Segment {segment_index} translated successfully.")
            except Exception as e:
                print(f"Translation failed for segment {segment_index} after all retries. Skipping.")
                translated_text = f"[TRANSLATION_FAILED FOR SEGMENT {segment_index}: {e}]"
            
            job.append_translated_segment(translated_text)

        print(f"\n--- Translation Complete! Output saved to {job.output_filename} ---")
        print(f"--- Full prompts were saved to {prompt_log_filename} for debugging. ---")
        print(f"--- Context summary was saved to {context_log_filename} for review. ---")