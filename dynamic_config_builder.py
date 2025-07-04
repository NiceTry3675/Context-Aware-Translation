from gemini_model import GeminiModel
from glossary_manager import GlossaryManager
from character_style_manager import CharacterStyleManager

class DynamicConfigBuilder:
    """
    Orchestrates the dynamic generation of configuration for each translation segment.
    It uses specialized managers to handle different aspects of the analysis.
    """

    def __init__(self, model: GeminiModel, novel_name: str):
        """
        Initializes the builder with the shared Gemini model and managers.
        
        Args:
            model: The shared GeminiModel instance.
            novel_name: The name of the novel, used for context.
        """
        self.model = model
        self.novel_name = novel_name
        # In a future implementation, the protagonist's name could be dynamically identified
        # or passed in from a configuration file. For now, we can assume a default.
        protagonist_name = self._determine_protagonist(novel_name)
        
        self.glossary_manager = GlossaryManager(model)
        self.character_style_manager = CharacterStyleManager(model, protagonist_name)
        print(f"DynamicConfigBuilder initialized for '{novel_name}' with protagonist '{protagonist_name}'.")

    def _determine_protagonist(self, novel_name: str) -> str:
        """

        Determines the protagonist's name based on the novel's title.
        This is a simple heuristic and can be replaced with a more robust method.
        """
        # Simple example: "THE_CATCHER_IN_THE_RYE" -> "Holden"
        if "CATCHER" in novel_name.upper():
            return "Holden"
        if "METAMORPHOSIS" in novel_name.upper():
            return "Gregor"
        # Default fallback
        return "protagonist"

    def build_dynamic_guides(self, segment_text: str, current_glossary: dict, current_character_styles: dict) -> tuple[dict, dict]:
        """
        Analyzes a text segment to build dynamic guidelines for translation.

        This method orchestrates the process:
        1. Updates the glossary with new proper nouns found in the segment.
        2. Updates the character style guide based on dialogue interactions.

        Args:
            segment_text: The text content of the current segment.
            current_glossary: The glossary dictionary from the TranslationJob.
            current_character_styles: The character styles dictionary from the TranslationJob.

        Returns:
            A tuple containing the updated glossary and the updated character styles.
        """
        print("\n--- Building Dynamic Guides for Segment ---")
        
        # 1. Update glossary
        updated_glossary = self.glossary_manager.update_glossary(
            segment_text,
            current_glossary
        )

        # 2. Update character styles
        updated_character_styles = self.character_style_manager.update_styles(
            segment_text,
            current_character_styles
        )

        print("--- Dynamic Guides Built Successfully ---")
        return updated_glossary, updated_character_styles