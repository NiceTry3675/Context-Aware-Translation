import re
from tqdm import tqdm
from gemini_model import GeminiModel
from prompt_builder import PromptBuilder
from dynamic_config_builder import DynamicConfigBuilder
from translation_job import TranslationJob

def get_segment_ending(segment_text: str, num_paragraphs: int = 2) -> str:
    """Extracts the last few paragraphs from a segment."""
    if not segment_text:
        return ""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', segment_text) if p.strip()]
    return "\n\n".join(paragraphs[-num_paragraphs:])

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
        static_rules_text = self._prepare_static_rules(config)
        
        prompt_log_filename = f"debug_prompts_{job.base_filename}.txt"
        context_log_filename = f"context_log_{job.base_filename}.txt"
        with open(prompt_log_filename, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {job.base_filename}\n\n")
        with open(context_log_filename, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {job.base_filename}\n\n")

        for i, segment_content in enumerate(tqdm(job.segments, desc="Translating Segments")):
            segment_index = i + 1
            print(f"\n\n--- Starting processing for Segment {segment_index}/{len(job.segments)} ---")
            print(f"Segment starts with: '{segment_content[:70].strip()}...'\n")

            # The call to generate_guidelines_text is simplified back to its stable version
            dynamic_guidelines_text = self.dyn_config_builder.generate_guidelines_text(segment_content)
            
            immediate_context_en_text = get_segment_ending(job.get_previous_segment(i))
            immediate_context_ko_text = get_segment_ending(job.get_previous_translation(i))
            past_events_text = "Episodic memory feature is disabled."

            context_data = {
                "static_rules": static_rules_text,
                "dynamic_guidelines": dynamic_guidelines_text,
                "immediate_context_en": immediate_context_en_text or "N/A",
                "immediate_context_ko": immediate_context_ko_text or "N/A",
                "past_events": past_events_text,
                "current_segment": segment_content
            }
            
            self._write_context_log(context_log_filename, segment_index, context_data)
            prompt = self.prompt_builder.create_prompt(context_data)

            with open(prompt_log_filename, 'a', encoding='utf-8') as f:
                f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n")
                f.write(prompt)
                f.write("\n\n" + "="*50 + "\n\n")

            try:
                translated_text = self.gemini_api.generate_text(prompt)
                print(f"Segment {segment_index} translated successfully.")
            except Exception as e:
                print(f"Translation failed for segment {segment_index} after all retries. Skipping.")
                translated_text = f"[TRANSLATION_FAILED FOR SEGMENT {segment_index}: {e}]"
            
            job.append_translated_segment(translated_text)

        print(f"\n--- Translation Complete! Output saved to {job.output_filename} ---")
        print(f"--- Full prompts were saved to {prompt_log_filename} for debugging. ---")
        print(f"--- Context summary was saved to {context_log_filename} for review. ---")