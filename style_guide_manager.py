import os
import json
import re
from gemini_model import GeminiModel

class StyleGuideManager:
    """
    Manages the creation, loading, and retrieval of novel-specific style guides.
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
        Generates a style guide by analyzing the beginning of a novel,
        saves it as a JSON file, and returns the guide.
        """
        try:
            with open(novel_filepath, 'r', encoding='utf-8') as f:
                # Analyze a substantial chunk of the beginning for accurate style detection
                novel_intro_text = f.read(20000)

            master_prompt = self._build_master_prompt(novel_intro_text)
            
            print("Generating style guide with AI. This may take a moment...")
            response_text = self.model.generate_text(master_prompt)
            
            # Extract the JSON part from the response
            json_match = re.search(r"""```json
({.*?})
```""", response_text, re.DOTALL)
            if not json_match:
                raise ValueError("AI response did not contain a valid JSON block.")

            guide_data = json.loads(json_match.group(1))

            with open(guide_path, 'w', encoding='utf-8') as f:
                json.dump(guide_data, f, ensure_ascii=False, indent=2)
            
            print(f"Successfully generated and saved new style guide: {guide_path}")
            return guide_data

        except Exception as e:
            print(f"Error generating style guide: {e}")
            print("Falling back to a default style guide.")
            return self._get_default_guide()

    def _build_master_prompt(self, novel_text: str) -> str:
        """Builds the master prompt for the AI to generate the style guide."""
        return f"""
You are a distinguished literary critic and translation strategist. Your task is to analyze the provided introduction of a novel and generate a comprehensive 'Style Guide' in JSON format for its Korean translation.

This guide will establish the foundational rules for the translation project.

**Novel Introduction to Analyze:**
---
{novel_text}
---

**Your Task:**
Based on the text, generate a JSON object with the following structure.

```json
{{
  "base_style": {{
    "narration_voice": "Describe the narrator's perspective (e.g., '1st-person protagonist', '3rd-person omniscient').",
    "overall_tone": "Describe the overall tone and style in a few keywords (e.g., 'Cynical, colloquial, stream-of-consciousness').",
    "default_speech_level": "Specify the default Korean speech level for narration (e.g., '해체 (banmal)', '문어체 (formal, literary)')."
  }},
  "character_profiles": {{
    "[Character Name]": {{
      "description": "A brief description of the character's role and personality.",
      "default_speech_style": "Recommend a default Korean speech style (e.g., '해요체 (polite, informal)', '하게체 (authoritative but familiar)')."
    }},
    "[Another Character Name]": {{
      "description": "...",
      "default_speech_style": "..."
    }}
  }}
}}
```

**Instructions:**
1.  Identify the main narrator and key characters from the text.
2.  Analyze their personalities, relationships, and speaking styles.
3.  Fill in the JSON structure with your expert analysis.
4.  **Crucially, output ONLY the JSON object enclosed in ```json ... ```.** Do not include any other text or explanation.
"""

    def _get_default_guide(self) -> dict:
        """Returns a generic, default style guide."""
        default_guide = {
            "base_style": {
                "narration_voice": "3rd-person",
                "overall_tone": "Neutral, standard literary",
                "default_speech_level": "문어체 (formal, literary)"
            },
            "character_profiles": {}
        }
        # Save a default file to prevent re-generation on every run for this novel
        # The filename will be based on the novel that failed.
        # This part is tricky as we don't have the novel name here.
        # For simplicity, we'll just return the dict. A more robust solution
        # might save a 'failed_guides.log' or similar.
        return default_guide
