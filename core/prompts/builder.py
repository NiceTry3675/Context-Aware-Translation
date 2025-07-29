import json

class PromptBuilder:
    """
    Builds the final translation prompt using a centralized template.
    """
    def __init__(self, template: str):
        """
        Initializes the builder with a specific prompt template.
        
        Args:
            template: The prompt template string (e.g., from PromptManager).
        """
        self.template = template
        print("PromptBuilder initialized.")

    def build_translation_prompt(self, core_narrative_style: str, style_deviation_info: str, glossary: dict, character_styles: dict, source_segment: str, prev_segment_source: str, prev_segment_ko: str, protagonist_name: str) -> str:
        """
        Builds the final prompt by filling the template with all necessary data.

        Args:
            core_narrative_style: The defined core style for the novel's narration.
            style_deviation_info: Information about any style deviation in this segment.
            glossary: The full, cumulative glossary.
            character_styles: The full, cumulative character style dictionary.
            source_segment: The source text to be translated.
            prev_segment_source: The ending of the previous source language segment for context.
            prev_segment_ko: The ending of the previous Korean segment for context.

        Returns:
            The fully formatted prompt string ready for the AI model.
        """
        glossary_string = self._format_dict_for_prompt(glossary, "No glossary terms defined.")
        character_styles_string = self._format_dict_for_prompt(character_styles, "No specific dialogue styles defined.")

        context_data = {
            "core_narrative_style": core_narrative_style,
            "style_deviation_info": style_deviation_info,
            "glossary_terms": glossary_string,
            "character_speech_styles": character_styles_string,
            "prev_segment_source": prev_segment_source or "N/A",
            "prev_segment_ko": prev_segment_ko or "N/A",
            "source_segment": source_segment,
            "protagonist_name": protagonist_name,
        }

        try:
            return self.template.format(**context_data)
        except KeyError as e:
            raise KeyError(f"The placeholder '{{{e}}}' in the template was not found in the provided context data.")

    def _format_dict_for_prompt(self, data: dict, default_text: str) -> str:
        """Formats a dictionary into a newline-separated string for the prompt."""
        if not data:
            return f"- {default_text}"
        
        return "\n".join([f"- {key}: {value}" for key, value in data.items()])