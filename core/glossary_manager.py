from gemini_model import GeminiModel
from prompt_manager import PromptManager

class GlossaryManager:
    """Manages the glossary for a translation job."""

    def __init__(self, model: GeminiModel):
        self.model = model

    def update_glossary(self, segment_text: str, current_glossary: dict) -> dict:
        """
        Extracts proper nouns from the segment, translates new ones,
        and returns the updated glossary.
        """
        # print("\nUpdating Glossary...")
        extracted_terms = self._extract_proper_nouns(segment_text)
        if not extracted_terms:
            # print("No new proper nouns found in this segment.")
            return current_glossary

        new_terms = [term for term in extracted_terms if term not in current_glossary]
        if not new_terms:
            # print("All extracted nouns are already in the glossary.")
            return current_glossary
            
        # encoded_new_terms = [term.encode('cp949', 'replace').decode('cp949') for term in new_terms]
        # print(f"Found {len(new_terms)} new proper nouns to translate: {', '.join(encoded_new_terms)}")
        translated_terms = self._translate_terms(new_terms)

        updated_glossary = current_glossary.copy()
        updated_glossary.update(translated_terms)
        
        # print("Glossary updated.")
        return updated_glossary

    def _extract_proper_nouns(self, segment_text: str) -> list[str]:
        """Extracts proper nouns from the text using the LLM."""
        prompt = PromptManager.GLOSSARY_EXTRACT_NOUNS.format(segment_text=segment_text)
        try:
            response = self.model.generate_text(prompt)
            # Return a sorted list of unique, non-empty terms
            return sorted(list(set([term.strip() for term in response.split(',') if term.strip()])))
        except Exception as e:
            print(f"Warning: Could not extract proper nouns. {e}")
            return []

    def _translate_terms(self, terms: list[str]) -> dict:
        """Translates a list of terms and returns a dictionary."""
        prompt = PromptManager.GLOSSARY_TRANSLATE_TERMS.format(key_terms=', '.join(terms))
        try:
            response = self.model.generate_text(prompt)
            translated_dict = {}
            for line in response.strip().split('\n'):
                if ':' in line:
                    key, value = [x.strip() for x in line.split(':', 1)]
                    if key in terms:
                        translated_dict[key] = value
            return translated_dict
        except Exception as e:
            print(f"Warning: Could not translate key terms. {e}")
            return {}