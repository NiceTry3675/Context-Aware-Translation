from ..translation.models.gemini import GeminiModel
from ..translation.models.openrouter import OpenRouterModel
from ..prompts.manager import PromptManager
from .glossary import GlossaryManager
from .character_style import CharacterStyleManager
from shared.errors import ProhibitedException
from shared.errors import prohibited_content_logger
from typing import List, Dict, Optional, Union
from pydantic import ValidationError
from ..schemas.narrative_style import (
    StyleDeviation,
    WorldAtmosphereAnalysis,
    make_style_deviation_schema,
    parse_style_deviation_response,
    make_world_atmosphere_schema,
    parse_world_atmosphere_response,
)

class DynamicConfigBuilder:
    """
    Orchestrates the dynamic generation of configuration for each translation segment.
    It uses specialized managers to handle different aspects of the analysis.
    """

    def __init__(
        self, 
        model: GeminiModel | OpenRouterModel, 
        protagonist_name: str, 
        initial_glossary: Optional[Union[List[Dict[str, str]], Dict[str, str]]] = None,
        character_style_model: Optional[GeminiModel | OpenRouterModel] = None
    ):
        """
        Initializes the builder with the shared Gemini model and managers.
        
        Args:
            model: The shared GeminiModel instance.
            protagonist_name: The name of the protagonist.
            initial_glossary: An optional dictionary or list of dictionaries to pre-populate the glossary.
        """
        self.model = model

        # Prefer a dedicated model for character style analysis if it supports structured output
        character_style_backend = character_style_model if (
            character_style_model and hasattr(character_style_model, 'generate_structured')
        ) else model
        if character_style_model and not hasattr(character_style_model, 'generate_structured'):
            print("Warning: Selected style model does not support structured output for character styles. Falling back to dynamic guide model.")

        self.character_style_manager = CharacterStyleManager(character_style_backend, protagonist_name)
        
        self.initial_glossary_dict = {}
        if initial_glossary:
            # Accept either a dict { term: translation } or a list of { term, translation }
            if isinstance(initial_glossary, dict):
                self.initial_glossary_dict = {
                    str(k): str(v) for k, v in initial_glossary.items()
                }
            elif isinstance(initial_glossary, list):
                for item in initial_glossary:
                    if isinstance(item, dict) and 'term' in item and 'translation' in item:
                        self.initial_glossary_dict[str(item['term'])] = str(item['translation'])
        
        print(f"DynamicConfigBuilder initialized with protagonist '{protagonist_name}'.")
        if self.initial_glossary_dict:
            print(f"Pre-populating glossary with {len(self.initial_glossary_dict)} user-defined terms.")
        print(f"DynamicConfigBuilder using structured output mode.")

    

    def build_dynamic_guides(self, segment_text: str, core_narrative_style: str, current_glossary: dict, current_character_styles: dict, job_base_filename: str, segment_index: int, previous_context: Optional[str] = None) -> tuple[dict, dict, str, Optional[WorldAtmosphereAnalysis]]:
        """
        Analyzes a text segment to build dynamic guidelines for translation.

        This method orchestrates the process:
        1. Updates the glossary with new proper nouns.
        2. Updates the character style guide based on dialogue.
        3. Analyzes the segment for any narrative style deviations.
        4. Analyzes world and atmosphere for context and illustration.

        Args:
            segment_text: The text content of the current segment.
            core_narrative_style: The core narrative style defined for the novel.
            current_glossary: The glossary dictionary from the TranslationJob.
            current_character_styles: The character styles dictionary from the TranslationJob.
            job_base_filename: Base filename for logging.
            segment_index: Index of the current segment.
            previous_context: Optional previous segment text for context.

        Returns:
            A tuple containing the updated glossary, updated character styles,
            style deviation information, and world/atmosphere analysis.
        """
        # 1. Initialize GlossaryManager with the user-defined glossary
        # The current_glossary from the job state is merged with the initial one.
        combined_glossary = {**self.initial_glossary_dict, **current_glossary}
        glossary_manager = GlossaryManager(
            self.model, 
            job_base_filename, 
            initial_glossary=combined_glossary
        )
        
        # Update glossary based on the current segment
        updated_glossary = glossary_manager.update_glossary(segment_text)

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

        # 4. Analyze world and atmosphere
        world_atmosphere = self._analyze_world_atmosphere(
            segment_text,
            previous_context,
            updated_glossary,
            job_base_filename,
            segment_index
        )

        return updated_glossary, updated_character_styles, style_deviation_info, world_atmosphere

    def _analyze_style_deviation(self, segment_text: str, core_narrative_style: str, job_base_filename: str = "unknown", segment_index: Optional[int] = None) -> str:
        """Analyzes the segment for deviations from the core narrative style using structured output."""
        return self._analyze_style_deviation_structured(segment_text, core_narrative_style, job_base_filename, segment_index)
    
    def _analyze_style_deviation_structured(self, segment_text: str, core_narrative_style: str, job_base_filename: str = "unknown", segment_index: Optional[int] = None) -> str:
        """Analyzes style deviation using structured output."""
        prompt = PromptManager.ANALYZE_NARRATIVE_DEVIATION.format(
            core_narrative_style=core_narrative_style,
            segment_text=segment_text
        )
        try:
            schema = make_style_deviation_schema()
            response = self.model.generate_structured(prompt, schema)
            deviation = parse_style_deviation_response(response)
            return deviation.to_prompt_format()
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="style_deviation_analysis_structured",
                prompt=prompt,
                source_text=segment_text,
                error_message=str(e),
                job_filename=job_base_filename,
                segment_index=segment_index,
                context={"core_narrative_style": core_narrative_style}
            )
            print(f"Warning: Structured style deviation analysis blocked by safety settings. Log saved to: {log_path}")
            return "N/A"
        except Exception as e:
            print(f"Warning: Could not analyze style deviation (structured). {e}")
            return "N/A"
    
    def _analyze_world_atmosphere(self, segment_text: str, previous_context: Optional[str], glossary: dict, job_base_filename: str = "unknown", segment_index: Optional[int] = None) -> Optional[WorldAtmosphereAnalysis]:
        """Analyzes world and atmosphere using structured output."""
        prompt_manager = PromptManager()

        # Format glossary for prompt
        glossary_str = "\n".join([f"{term}: {translation}" for term, translation in glossary.items()]) if glossary else "N/A"

        # Get the prompt template
        try:
            prompt_template = prompt_manager._prompts["world_atmosphere"]["analyze"]
        except (KeyError, TypeError):
            print("Warning: world_atmosphere.analyze prompt not found")
            return None

        prompt = prompt_template.format(
            segment_text=segment_text,
            previous_context=previous_context or "N/A",
            glossary=glossary_str
        )

        try:
            # Check if the model supports structured output
            if hasattr(self.model, 'generate_structured'):
                schema = make_world_atmosphere_schema()
                response = self.model.generate_structured(prompt, schema)
                if not response:
                    print("Warning: World atmosphere analysis returned empty payload; skipping.")
                    return None

                try:
                    world_atmosphere = parse_world_atmosphere_response(response)
                except ValidationError as validation_error:
                    print(
                        "Warning: World atmosphere analysis produced invalid payload; "
                        f"skipping. Details: {validation_error}"
                    )
                    return None

                # Validate that we got a proper summary, not raw text
                if world_atmosphere.segment_summary:
                    # Check if summary looks like actual source text (too long and matches source)
                    if (len(world_atmosphere.segment_summary) > 400 and
                        world_atmosphere.segment_summary[:100] in segment_text):
                        raise ValueError(f"World atmosphere analysis failed: segment_summary contains raw text instead of a summary. Length: {len(world_atmosphere.segment_summary)}")

                return world_atmosphere
            else:
                # Model doesn't support structured output (e.g., OpenRouter)
                print(f"Warning: Model {type(self.model).__name__} doesn't support structured output. Skipping world atmosphere analysis.")
                return None
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="world_atmosphere_analysis",
                prompt=prompt,
                source_text=segment_text,
                error_message=str(e),
                job_filename=job_base_filename,
                segment_index=segment_index,
                context={"previous_context": previous_context, "glossary": glossary_str}
            )
            print(f"Warning: World atmosphere analysis blocked by safety settings. Log saved to: {log_path}")
            return None
        except Exception as e:
            print(f"ERROR: World atmosphere analysis failed: {e}")
            raise  # Re-raise the exception to make it fail properly
