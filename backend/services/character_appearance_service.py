"""
Character Appearance Service

Analyzes early parts of the novel to infer the protagonist's physical appearance
and produces candidate image-generation prompts focusing on appearance only.
"""

from typing import Dict, Any, List, Optional
from .base.base_service import BaseAnalysisService


APPEARANCE_EXTRA_INSTRUCTIONS = (
    "Do not include any background. Plain light background. Neutral pose. "
    "No text or watermark. Do not write the character's name in the image."
)


class CharacterAppearanceService(BaseAnalysisService):
    """Service for extracting protagonist appearance prompt candidates."""

    def analyze_appearance(
        self,
        filepath: str,
        api_key: str,
        model_name: str,
        protagonist_name: Optional[str] = None,
        candidates: int = 3,
    ) -> Dict[str, Any]:
        """
        Produce a small set of appearance-only prompt candidates derived from early text.

        Returns a dict: { 'prompts': [str], 'protagonist_name': str, 'sample_size': int }
        """
        self.validate_analysis_input(filepath, api_key, model_name)

        # Prepare sample
        context = self.analyze_document_sample(filepath, api_key, model_name, sample_size=15000)
        model_api = context['model_api']
        segments = context['segments']
        filename = context['filename']

        sample_text = "\n".join(segments[:3]) if segments else ""

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
            response_text = model_api.generate_text(f"{system}\n\n{user}")
        except Exception:
            # Fallback: provide three neutral prompts
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

