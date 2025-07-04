import json
from prompt_manager import PromptManager

class PromptBuilder:
    """
    Builds the final translation prompt using a centralized template.
    """
    def __init__(self):
        self.template = PromptManager.MAIN_TRANSLATION
        print("PromptBuilder initialized with template from PromptManager.")

    def build_translation_prompt(self, style_guide: dict, glossary_terms: str, style_analysis: str, source_segment: str, prev_segment_en: str, prev_segment_ko: str) -> str:
        """
        Builds the final prompt by filling the template with hierarchical context data.
        """
        # Simplified style guide text generation
        style_guide_text = json.dumps(style_guide, indent=2, ensure_ascii=False)

        # Combine the style analysis and other dynamic elements
        dynamic_guidelines = f"Style and Tone Analysis:\n{style_analysis}"

        context_data = {
            "glossary_terms": glossary_terms,
            "dynamic_guidelines": dynamic_guidelines,
            "style_guide": style_guide_text,
            "prev_segment_en": prev_segment_en or "N/A",
            "prev_segment_ko": prev_segment_ko or "N/A",
            "source_segment": source_segment,
        }

        try:
            return self.template.format(**context_data)
        except KeyError as e:
            raise KeyError(f"The placeholder {e} in the template was not found in the provided context data.")
