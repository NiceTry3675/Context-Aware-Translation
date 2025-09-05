"""
Character Analysis Module

Analyzes early parts of the novel to infer the protagonist's physical appearance
and produces candidate image-generation prompts focusing on appearance only.

Refactored from backend/services/character_appearance_service.py
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from core.config.loader import load_config
from core.utils.text_segmentation import create_segments_for_text


APPEARANCE_EXTRA_INSTRUCTIONS = (
    "Do not include any background. Plain light background. Neutral pose. "
    "No text or watermark. Do not write the character's name in the image."
)


class CharacterAnalysis:
    """Utility class for extracting protagonist appearance prompt candidates."""
    
    def __init__(self, model_api=None):
        """
        Initialize character analysis.
        
        Args:
            model_api: Optional pre-configured model API instance
        """
        self.config = load_config()
        self._model_api = model_api
    
    def set_model_api(self, model_api):
        """Set or update the model API instance."""
        self._model_api = model_api
    
    def analyze_appearance(
        self,
        filepath: str,
        protagonist_name: Optional[str] = None,
        candidates: int = 3,
        sample_size: int = 15000
    ) -> Dict[str, Any]:
        """
        Produce a small set of appearance-only prompt candidates derived from early text.
        
        Args:
            filepath: Path to the source file
            protagonist_name: Optional protagonist name if known
            candidates: Number of prompt candidates to generate
            sample_size: Size of text sample to analyze
            
        Returns:
            Dictionary containing:
                - prompts: List of appearance prompt strings
                - protagonist_name: The protagonist's name
                - sample_size: Size of analyzed sample
        """
        # Validate inputs
        if not filepath:
            raise ValueError("File path is required")
        
        if not Path(filepath).exists():
            raise ValueError(f"File not found: {filepath}")
        
        if self._model_api is None:
            raise ValueError("Model API not configured. Call set_model_api() first.")
        
        # Prepare sample
        segments = self._prepare_document_segments(
            filepath, method="first_chars", count=sample_size
        )
        sample_text = "\n".join(segments[:3]) if segments else ""
        filename = Path(filepath).stem
        
        # Build a concise instruction for appearance extraction with multiple variants
        name_line = f"The protagonist's name is '{protagonist_name}'." if protagonist_name else (
            "Identify the protagonist by context."
        )
        
        system = (
            "You are an assistant extracting a fictional character's physical appearance from the given novel excerpt. "
            "Focus on visual traits useful for image generation. Avoid personality or backstory unless it affects visual cues."
        )
        
        user = (
            f"{name_line}\n\n"
            f"Excerpt (from '{filename}'):\n" + sample_text[:5000] + "\n\n"
            "Task: Draft {n} alternative concise appearance-only prompts for an image generation model. "
            "Each prompt should only describe the character's visual appearance (face, hair, body build, outfit cues) without naming them, "
            "and append: '" + APPEARANCE_EXTRA_INSTRUCTIONS + "'. "
            "Vary style subtly among prompts (e.g., line art vs painterly, casual vs travel outfit) but keep identity consistent. "
            "Do not include background or scene instructions.\n\n"
            "Output strictly as a numbered list, each item on its own line without extra commentary."
        ).replace("{n}", str(candidates))
        
        try:
            response_text = self._model_api.generate_text(f"{system}\n\n{user}")
        except Exception:
            # Fallback: provide neutral prompts
            base = "Young adult with medium build, natural skin tone, tidy hairstyle, simple casual outfit. " + APPEARANCE_EXTRA_INSTRUCTIONS
            return {
                'prompts': [base, base + " Clean line art.", base + " Soft painterly shading."],
                'protagonist_name': protagonist_name or 'Protagonist',
                'sample_size': len(sample_text)
            }
        
        # Parse numbered lines
        lines = [l.strip("- ") for l in response_text.splitlines() if l.strip()]
        candidates_list: List[str] = []
        
        for line in lines:
            # Remove leading numbers like '1. ', '2) '
            cleaned = line
            if len(cleaned) > 2 and (cleaned[1] in ['.', ')'] or cleaned[:2].isdigit()):
                # generic trim
                cleaned = cleaned.lstrip('0123456789. )')
                cleaned = cleaned.strip()
            candidates_list.append(cleaned)
        
        # Ensure we have N prompts
        if len(candidates_list) < candidates:
            while len(candidates_list) < candidates:
                candidates_list.append(candidates_list[-1] if candidates_list else (
                    "Neutral appearance, simple outfit. " + APPEARANCE_EXTRA_INSTRUCTIONS
                ))
        else:
            candidates_list = candidates_list[:candidates]
        
        return {
            'prompts': candidates_list,
            'protagonist_name': protagonist_name or 'Protagonist',
            'sample_size': len(sample_text)
        }
    
    def _prepare_document_segments(
        self,
        filepath: str,
        method: str = "sentence",
        **kwargs
    ) -> list:
        """
        Prepare document segments for processing.
        
        Args:
            filepath: Path to the document
            method: Segmentation method to use
            **kwargs: Additional arguments for segmentation
            
        Returns:
            List of segments
        """
        try:
            if method == "first_chars":
                # Get the desired character count
                count = kwargs.get("count", 15000)
                # Create segments with target size
                segments = create_segments_for_text(filepath, target_size=count)
                # Return just the text content from the first segment(s) up to count chars
                result = []
                total_chars = 0
                for segment in segments:
                    if total_chars + len(segment.text) <= count:
                        result.append(segment.text)
                        total_chars += len(segment.text)
                    else:
                        # Add partial segment to reach count
                        remaining = count - total_chars
                        if remaining > 0:
                            result.append(segment.text[:remaining])
                        break
                return result
            else:
                # For sentence method, return all segment contents
                segments = create_segments_for_text(filepath)
                return [segment.text for segment in segments]
        except Exception as e:
            raise Exception(f"Failed to prepare document segments: {str(e)}")
    
    def extract_character_traits(
        self,
        filepath: str,
        protagonist_name: Optional[str] = None,
        sample_size: int = 10000
    ) -> Dict[str, Any]:
        """
        Extract character traits and personality characteristics.
        
        Args:
            filepath: Path to the source file
            protagonist_name: Optional protagonist name if known
            sample_size: Size of text sample to analyze
            
        Returns:
            Dictionary of character traits
        """
        if self._model_api is None:
            raise ValueError("Model API not configured. Call set_model_api() first.")
        
        # Prepare sample
        segments = self._prepare_document_segments(
            filepath, method="first_chars", count=sample_size
        )
        sample_text = "\n".join(segments) if segments else ""
        
        name_line = f"The protagonist is '{protagonist_name}'." if protagonist_name else (
            "Identify the main protagonist."
        )
        
        prompt = (
            f"{name_line}\n\n"
            f"Text excerpt:\n{sample_text[:5000]}\n\n"
            "Extract the protagonist's key traits:\n"
            "1. Personality traits (3-5 key traits)\n"
            "2. Speaking style (formal/casual, verbose/terse, etc.)\n"
            "3. Behavioral patterns (habits, mannerisms)\n"
            "4. Relationships (key relationships mentioned)\n\n"
            "Format as a bullet list."
        )
        
        try:
            response = self._model_api.generate_text(prompt)
            return {
                'protagonist_name': protagonist_name or 'Protagonist',
                'traits': response,
                'sample_size': len(sample_text)
            }
        except Exception as e:
            print(f"Warning: Could not extract character traits: {e}")
            return {
                'protagonist_name': protagonist_name or 'Protagonist',
                'traits': "Unable to extract traits",
                'sample_size': len(sample_text)
            }