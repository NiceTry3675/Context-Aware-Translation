from ..translation.models.gemini import GeminiModel
from ..prompts.manager import PromptManager
from ..errors import ProhibitedException
from ..errors import prohibited_content_logger
from typing import Dict, Optional

class GlossaryManager:
    """Manages the glossary for a translation job."""

    def __init__(self, model: GeminiModel, job_filename: str = "unknown", initial_glossary: Optional[Dict[str, str]] = None):
        self.model = model
        self.job_filename = job_filename
        self.glossary = initial_glossary or {}
        if initial_glossary:
            print(f"GlossaryManager initialized with {len(initial_glossary)} pre-defined terms.")

    def update_glossary(self, segment_text: str) -> dict:
        """
        Extracts proper nouns from the segment, translates new ones,
        and returns the updated glossary.
        """
        extracted_terms = self._extract_proper_nouns(segment_text)
        if not extracted_terms:
            return self.glossary

        new_terms = [term for term in extracted_terms if term not in self.glossary]
        if not new_terms:
            return self.glossary
            
        translated_terms = self._translate_terms(new_terms, segment_text)

        self.glossary.update(translated_terms)
        return self.glossary

    def _extract_proper_nouns(self, segment_text: str) -> list[str]:
        """Extracts proper nouns from the text using the LLM."""
        prompt = PromptManager.GLOSSARY_EXTRACT_NOUNS.format(segment_text=segment_text)
        try:
            response = self.model.generate_text(prompt)
            return sorted(list(set([term.strip() for term in response.split(',') if term.strip()])))
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="glossary_extraction",
                prompt=prompt,
                source_text=segment_text,
                error_message=str(e),
                job_filename=self.job_filename
            )
            print(f"Warning: Glossary extraction blocked by safety settings. Log saved to: {log_path}")
            return []
        except Exception as e:
            print(f"Warning: Could not extract proper nouns. {e}")
            return []

    def _translate_terms(self, terms: list[str], segment_text: str) -> dict:
        """Translates a list of terms and returns a dictionary."""
        prompt = PromptManager.GLOSSARY_TRANSLATE_TERMS.format(
            key_terms=', '.join(terms),
            segment_text=segment_text
        )
        try:
            response = self.model.generate_text(prompt)
            translated_dict = {}
            for line in response.strip().split('\n'):
                if ':' in line:
                    key, value = [x.strip() for x in line.split(':', 1)]
                    if key in terms:
                        translated_dict[key] = value
            return translated_dict
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="glossary_translation",
                prompt=prompt,
                source_text=', '.join(terms),
                error_message=str(e),
                job_filename=self.job_filename
            )
            print(f"Warning: Glossary translation blocked by safety settings. Log saved to: {log_path}")
            return {}
        except Exception as e:
            print(f"Warning: Could not translate key terms. {e}")
            return {}
