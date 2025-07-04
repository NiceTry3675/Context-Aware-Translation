import os
import json
import re
from gemini_model import GeminiModel
from prompt_manager import PromptManager

class StyleGuideManager:
    """
    Manages the creation, loading, and retrieval of novel-specific style guides,
    now with a primary focus on defining a consistent core narrative voice.
    """
    def __init__(self, gemini_model: GeminiModel):
        self.model = gemini_model
        self.styles_dir = "config/styles"
        os.makedirs(self.styles_dir, exist_ok=True)

    def get_style_guide(self, novel_filepath: str) -> dict:
        """
        Gets the style guide for a given novel.
        If it doesn't exist, it generates and saves one automatically.
        """
        novel_name = os.path.splitext(os.path.basename(novel_filepath))[0]
        guide_path = os.path.join(self.styles_dir, f"{novel_name}.json")

        if os.path.exists(guide_path):
            print(f"Found existing style guide: {guide_path}")
            with open(guide_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"No style guide found for {novel_name}. Generating a new one...")
            return self._generate_and_save_guide(novel_filepath, guide_path)

    def _generate_and_save_guide(self, novel_filepath: str, guide_path: str) -> dict:
        """
        Generates a style guide using a robust, multi-step process.
        """
        try:
            # Ensure UTF-8 is used for reading the novel
            with open(novel_filepath, 'r', encoding='utf-8') as f:
                sample_text = f.read(8000)

            # Step 1: Determine the narrative voice
            print("Step 1: Determining narrative voice...")
            voice_prompt = PromptManager.DETERMINE_NARRATIVE_VOICE.format(sample_text=sample_text)
            narrative_voice = self.model.generate_text(voice_prompt).strip()
            if "1st-person" not in narrative_voice and "3rd-person" not in narrative_voice:
                raise ValueError(f"Failed to get a valid narrative voice. Got: {narrative_voice}")
            print(f"Determined voice: {narrative_voice}")

            # Step 2: Determine the speech level
            print("Step 2: Determining speech level...")
            speech_prompt = PromptManager.DETERMINE_SPEECH_LEVEL.format(
                narrative_voice=narrative_voice,
                sample_text=sample_text
            )
            # The response from the model is already a string, no need to decode
            speech_level = self.model.generate_text(speech_prompt).strip()
            
            # Validate the response more strictly
            valid_levels = ['해라체', '해요체', '하십시오체']
            # Extract the Korean part only
            match = re.search(r'([가-힣]+체)', speech_level)
            if not match or match.group(1) not in valid_levels:
                 raise ValueError(f"Failed to get a valid speech level. Got: {speech_level}")
            
            clean_speech_level = match.group(1)
            print(f"Determined speech level: {clean_speech_level}")

            # Step 3: Programmatically build the guide
            guide_data = {
                "narrative_voice": narrative_voice,
                "core_narrative_voice": clean_speech_level,
                "reasoning": "Style guide generated programmatically for robustness."
            }

            # Ensure UTF-8 is used for writing the JSON file
            with open(guide_path, 'w', encoding='utf-8') as f:
                json.dump(guide_data, f, ensure_ascii=False, indent=2)
            
            print(f"Successfully generated and saved new style guide: {guide_path}")
            return guide_data

        except Exception as e:
            print(f"Error generating style guide: {e}")
            print("Falling back to a default style guide.")
            return self._get_default_guide()

    def _get_default_guide(self) -> dict:
        """Returns a generic, default style guide."""
        return {
            "narrative_voice": "1st-person",
            "core_narrative_voice": "해라체",
            "reasoning": "Default fallback due to an error during generation."
        }
