import os
from typing import Dict, Optional
from ..translation.models.gemini import GeminiModel
from ..prompts.manager import PromptManager
from shared.errors import ProhibitedException
from shared.errors import prohibited_content_logger
from ..schemas.character_style import (
    DialogueAnalysisResult,
    make_dialogue_analysis_schema,
    parse_dialogue_analysis_response,
)

class CharacterStyleManager:
    """Manages the protagonist's dialogue style towards other characters."""

    def __init__(
        self, 
        model: GeminiModel, 
        protagonist_name: str = "protagonist"
    ):
        self.model = model
        # In a more advanced system, the protagonist's name could be identified dynamically.
        self.protagonist_name = protagonist_name
        print(f"CharacterStyleManager using structured output mode.")

    def update_styles(self, segment_text: str, current_styles: Dict[str, str], job_base_filename: str, segment_index: int) -> Dict[str, str]:
        """
        Analyzes the segment to determine who the protagonist speaks to
        and what speech level is used, then returns the updated styles.
        """
        return self._update_styles_structured(segment_text, current_styles, job_base_filename, segment_index)
    
    def _update_styles_structured(self, segment_text: str, current_styles: Dict[str, str], job_base_filename: str, segment_index: int) -> Dict[str, str]:
        """Update styles using structured output."""
        prompt = PromptManager.CHARACTER_ANALYZE_DIALOGUE.format(
            protagonist_name=self.protagonist_name,
            segment_text=segment_text
        )
        try:
            schema = make_dialogue_analysis_schema(self.protagonist_name)
            response = self.model.generate_structured(prompt, schema)
            result = parse_dialogue_analysis_response(response)
            
            if not result.has_dialogue or not result.interactions:
                return current_styles
            
            return result.merge_with_existing(current_styles)

        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="character_style_analysis_structured",
                prompt=prompt,
                source_text=segment_text,
                error_message=str(e),
                job_filename=job_base_filename,
                segment_index=segment_index,
                context={"protagonist_name": self.protagonist_name}
            )
            print(f"Warning: Structured character style analysis blocked by safety settings. Log saved to: {log_path}")
            return current_styles
            
        except Exception as e:
            print(f"Warning: Could not analyze character styles (structured). {e}")
            return current_styles
