from ..translation.models.gemini import GeminiModel
from ..prompts.manager import PromptManager
from .glossary import GlossaryManager
from .character_style import CharacterStyleManager
from ..errors import ProhibitedException
from ..errors import prohibited_content_logger
from typing import List, Dict, Optional

class DynamicConfigBuilder:
    """
    Orchestrates the dynamic generation of configuration for each translation segment.
    It uses specialized managers to handle different aspects of the analysis.
    """

    def __init__(self, model: GeminiModel, protagonist_name: str, initial_glossary: Optional[List[Dict[str, str]]] = None):
        """
        Initializes the builder with the shared Gemini model and managers.
        
        Args:
            model: The shared GeminiModel instance.
            protagonist_name: The name of the protagonist.
            initial_glossary: An optional list of dictionaries to pre-populate the glossary.
        """
        self.model = model
        self.character_style_manager = CharacterStyleManager(model, protagonist_name)
        
        self.initial_glossary_dict = {}
        if initial_glossary:
            for item in initial_glossary:
                if isinstance(item, dict) and 'term' in item and 'translation' in item:
                    self.initial_glossary_dict[item['term']] = item['translation']
        
        print(f"DynamicConfigBuilder initialized with protagonist '{protagonist_name}'.")
        if self.initial_glossary_dict:
            print(f"Pre-populating glossary with {len(self.initial_glossary_dict)} user-defined terms.")

    

    def build_dynamic_guides(self, segment_text: str, core_narrative_style: str, current_glossary: dict, current_character_styles: dict, job_base_filename: str, segment_index: int, language: str = "english") -> tuple[dict, dict, str]:
        """
        Analyzes a text segment to build dynamic guidelines for translation.

        This method orchestrates the process:
        1. Updates the glossary with new proper nouns.
        2. Updates the character style guide based on dialogue.
        3. Analyzes the segment for any narrative style deviations.

        Args:
            segment_text: The text content of the current segment.
            core_narrative_style: The core narrative style defined for the novel.
            current_glossary: The glossary dictionary from the TranslationJob.
            current_character_styles: The character styles dictionary from the TranslationJob.

        Returns:
            A tuple containing the updated glossary, updated character styles,
            and any style deviation information.
        """
        # 1. Initialize GlossaryManager with the user-defined glossary
        # The current_glossary from the job state is merged with the initial one.
        combined_glossary = {**self.initial_glossary_dict, **current_glossary}
        glossary_manager = GlossaryManager(self.model, job_base_filename, initial_glossary=combined_glossary)
        
        # Update glossary based on the current segment
        updated_glossary = glossary_manager.update_glossary(segment_text, language=language)

        # 2. Update character styles
        updated_character_styles = self.character_style_manager.update_styles(
            segment_text,
            current_character_styles,
            job_base_filename,
            segment_index
        )

        # 3. Analyze for style deviations
        style_deviation_info = self._analyze_style_deviation(
            segment_text,
            core_narrative_style,
            job_base_filename,
            segment_index
        )

        return updated_glossary, updated_character_styles, style_deviation_info

    def _analyze_style_deviation(self, segment_text: str, core_narrative_style: str, job_base_filename: str = "unknown", segment_index: int = None) -> str:
        """Analyzes the segment for deviations from the core narrative style."""
        prompt = PromptManager.ANALYZE_NARRATIVE_DEVIATION.format(
            core_narrative_style=core_narrative_style,
            segment_text=segment_text
        )
        try:
            response = self.model.generate_text(prompt)
            if "N/A" in response:
                return "N/A"
            else:
                return response
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="style_deviation_analysis",
                prompt=prompt,
                source_text=segment_text,
                error_message=str(e),
                job_filename=job_base_filename,
                segment_index=segment_index,
                context={"core_narrative_style": core_narrative_style}
            )
            print(f"Warning: Style deviation analysis blocked by safety settings. Log saved to: {log_path}")
            return "N/A"
        except Exception as e:
            print(f"Warning: Could not analyze style deviation. {e}")
            return "N/A"
