import json
from prompt_manager import PromptManager

class PromptBuilder:
    """
    Builds the final translation prompt using a centralized template.
    """
    def __init__(self):
        self.template = PromptManager.MAIN_TRANSLATION
        print("PromptBuilder initialized with template from PromptManager.")

    def build_translation_prompt(self, style_guide: dict, core_narrative_voice: str, full_glossary: dict, style_analysis: str, source_segment: str, prev_segment_en: str) -> str:
        """
        Builds the final prompt by filling the template with hierarchical context data.
        """
        # The main style guide is now just for reference, the core voice is the key.
        style_guide_reference = json.dumps(style_guide, indent=2, ensure_ascii=False)

        # Format the full glossary into a string for the prompt
        if full_glossary:
            glossary_string = "\n".join([f"- {term}: {translation}" for term, translation in full_glossary.items()])
        else:
            glossary_string = "No glossary terms have been defined yet."

        context_data = {
            "core_narrative_voice": core_narrative_voice,
            "glossary_terms": glossary_string,
            "dynamic_guidelines": style_analysis or "No specific style deviations for this segment.",
            "style_guide": style_guide_reference,
            "prev_segment_en": prev_segment_en or "N/A",
            "source_segment": source_segment,
        }

        try:
            return self.template.format(**context_data)
        except KeyError as e:
            raise KeyError(f"The placeholder {e} in the template was not found in the provided context data.")
