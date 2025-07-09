import os
from gemini_model import GeminiModel
from prompt_manager import PromptManager

class CharacterStyleManager:
    """Manages the protagonist's dialogue style towards other characters."""

    def __init__(self, model: GeminiModel, protagonist_name: str = "protagonist"):
        self.model = model
        # In a more advanced system, the protagonist's name could be identified dynamically.
        self.protagonist_name = protagonist_name

    def update_styles(self, segment_text: str, current_styles: dict, job_base_filename: str, segment_index: int) -> dict:
        """
        Analyzes the segment to determine who the protagonist speaks to
        and what speech level is used, then returns the updated styles.
        """
        # print("\nUpdating Character Styles...")
        prompt = PromptManager.CHARACTER_ANALYZE_DIALOGUE.format(
            protagonist_name=self.protagonist_name,
            segment_text=segment_text
        )
        try:
            response = self.model.generate_text(prompt)
            if not response or "N/A" in response:
                # print("No new character interactions found in this segment.")
                return current_styles

            updated_styles = current_styles.copy()
            # The response is expected to be in the format:
            # Character1: 존댓말
            # Character2: 반말
            for line in response.strip().split('\n'):
                if ':' in line:
                    character, style = [x.strip() for x in line.split(':', 1)]
                    # Add or update the style for this character interaction
                    style_key = f"{self.protagonist_name}->{character}"
                    if style_key not in updated_styles or updated_styles[style_key] != style:
                        # print(f"New/updated style found: {style_key} uses '{style}'")
                        updated_styles[style_key] = style
            
            # print("Character styles updated.")
            return updated_styles

        except Exception as e:
            error_message = str(e)
            print(f"Warning: Could not analyze character styles. {error_message}")
            
            if "PROHIBITED_CONTENT" in error_message.upper():
                debug_prompts_dir = "debug_prompts"
                os.makedirs(debug_prompts_dir, exist_ok=True)
                error_log_path = os.path.join(debug_prompts_dir, f"error_character_style_{job_base_filename}_{segment_index}.txt")
                with open(error_log_path, 'w', encoding='utf-8') as f:
                    f.write(f"# PROHIBITED CONTENT ERROR LOG FOR CHARACTER STYLE ANALYSIS - SEGMENT {segment_index}\n\n")
                    f.write(f"--- SOURCE SEGMENT ---\n{segment_text}\n\n")
                    f.write(f"--- FULL PROMPT ---\n{prompt}")
                print(f"Problematic character style prompt for segment {segment_index} saved to: {error_log_path}")
            
            return current_styles

