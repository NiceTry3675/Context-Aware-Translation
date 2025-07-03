from gemini_model import GeminiModel
import re

class DynamicConfigBuilder:
    """
    Analyzes a text segment to generate comprehensive, multi-part dynamic guidelines
    in a structured, 3-step process.
    """
    def __init__(self, gemini_model: GeminiModel):
        self.model = gemini_model

    def _extract_key_terms(self, segment_text: str) -> list[str]:
        """Step 1: Extract key term candidates from the text."""
        print("\nStep 1: Extracting key terms from segment...")
        prompt = f"""
Your task is to act as a data extractor. Read the following text segment and extract all proper nouns (names of people, places, unique objects) and important recurring terms. Do not translate or explain them. Output ONLY a comma-separated list of these terms.

**Text Segment to Analyze:**
---
{segment_text[:4000]}
---

**Comma-separated list of key terms:**
"""
        try:
            response = self.model.generate_text(prompt)
            terms = [term.strip() for term in response.split(',') if term.strip()]
            print(f"Found {len(terms)} potential key terms.")
            return terms
        except Exception as e:
            print(f"Warning: Could not extract key terms. {e}")
            return []

    def _translate_terms(self, terms: list[str]) -> str:
        """Step 2: Get translations for the extracted key terms in a strict format."""
        if not terms:
            return "- No key terms were identified for this segment."

        print("Step 2: Translating key terms...")
        prompt = f"""
You are a terminology expert. For the following comma-separated list of key terms, provide a suitable Korean translation for each.
Output EACH term on a new line.
The format MUST be exactly: `Key Term: Korean Translation`

**Key Terms to Translate:**
{', '.join(terms)}

**Output:**
"""
        try:
            return self.model.generate_text(prompt)
        except Exception as e:
            print(f"Warning: Could not translate key terms. {e}")
            return "- Failed to generate key term translations."

    def _analyze_style_and_tone(self, segment_text: str) -> str:
        """Step 3: Analyze the style and tone of the segment."""
        print("Step 3: Analyzing style and tone...")
        prompt = f"""
You are a literary analyst. Read the following text segment and briefly describe:
1. The overall atmosphere and tone (e.g., tense, melancholic, humorous).
2. The speaking style of any major characters who have dialogue.

**Text Segment to Analyze:**
---
{segment_text[:4000]}
---

**Analysis (in a short, bulleted list):**
"""
        try:
            return self.model.generate_text(prompt)
        except Exception as e:
            print(f"Warning: Could not analyze style and tone. {e}")
            return "- Failed to generate style and tone analysis."

    def generate_guidelines_text(self, segment_text: str) -> str:
        """
        Performs the full 3-step process to generate comprehensive dynamic guidelines.
        """
        extracted_terms = self._extract_key_terms(segment_text)
        term_translations = self._translate_terms(extracted_terms)
        style_analysis = self._analyze_style_and_tone(segment_text)
        
        combined_guidelines = (
            "Key Term Translations:\n"
            f"{term_translations}\n\n"
            "Style and Tone Analysis:\n"
            f"{style_analysis}"
        )
        print("Dynamic guidelines generated successfully.")
        return combined_guidelines