from ..translation.models.gemini import GeminiModel
from ..prompts.manager import PromptManager
from ..errors import ProhibitedException
from ..errors import prohibited_content_logger
from typing import Dict, Optional, List
from ..schemas.glossary import (
    ExtractedTerms,
    TranslatedTerms,
    make_extracted_terms_schema,
    make_translated_terms_schema,
    parse_extracted_terms_response,
    parse_translated_terms_response,
)

class GlossaryManager:
    """Manages the glossary for a translation job."""

    def __init__(
        self, 
        model: GeminiModel, 
        job_filename: str = "unknown", 
        initial_glossary: Optional[Dict[str, str]] = None,
        use_structured: bool = True
    ):
        self.model = model
        self.job_filename = job_filename
        self.glossary = initial_glossary or {}
        self.use_structured = use_structured
        if initial_glossary:
            print(f"GlossaryManager initialized with {len(initial_glossary)} pre-defined terms.")
        if use_structured:
            print(f"GlossaryManager using structured output mode.")

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

    def _extract_proper_nouns(self, segment_text: str) -> List[str]:
        """Extracts proper nouns from the text using the LLM."""
        if self.use_structured:
            return self._extract_proper_nouns_structured(segment_text)
        else:
            return self._extract_proper_nouns_text(segment_text)
    
    def _extract_proper_nouns_structured(self, segment_text: str) -> List[str]:
        """Extracts proper nouns using structured output."""
        prompt = PromptManager.GLOSSARY_EXTRACT_NOUNS.format(segment_text=segment_text)
        try:
            schema = make_extracted_terms_schema()
            response = self.model.generate_structured(prompt, schema)
            extracted = parse_extracted_terms_response(response)
            return sorted(list(set(extracted.terms))) if extracted.terms else []
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="glossary_extraction_structured",
                prompt=prompt,
                source_text=segment_text,
                error_message=str(e),
                job_filename=self.job_filename
            )
            print(f"Warning: Structured glossary extraction blocked by safety settings. Log saved to: {log_path}")
            return []
        except Exception as e:
            print(f"Warning: Could not extract proper nouns (structured). {e}")
            return []
    
    def _extract_proper_nouns_text(self, segment_text: str) -> List[str]:
        """Extracts proper nouns using text generation (legacy)."""
        prompt = PromptManager.GLOSSARY_EXTRACT_NOUNS.format(segment_text=segment_text)
        try:
            response = self.model.generate_text(prompt)
            if response and "N/A" not in response:
                return sorted(list(set([term.strip() for term in response.split(',') if term.strip()])))
            return []
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

    def _translate_terms(self, terms: List[str], segment_text: str) -> Dict[str, str]:
        """Translates a list of terms and returns a dictionary."""
        if self.use_structured:
            return self._translate_terms_structured(terms, segment_text)
        else:
            return self._translate_terms_text(terms, segment_text)
    
    def _translate_terms_structured(self, terms: List[str], segment_text: str) -> Dict[str, str]:
        """Translates terms using structured output."""
        existing_glossary_str = '\n'.join([f"{k}: {v}" for k, v in self.glossary.items()])
        if not existing_glossary_str:
            existing_glossary_str = "N/A"

        prompt = PromptManager.GLOSSARY_TRANSLATE_TERMS.format(
            key_terms=', '.join(terms),
            segment_text=segment_text,
            existing_glossary=existing_glossary_str
        )
        try:
            schema = make_translated_terms_schema(terms)
            response = self.model.generate_structured(prompt, schema)
            translated = parse_translated_terms_response(response)
            return translated.to_dict()
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="glossary_translation_structured",
                prompt=prompt,
                source_text=', '.join(terms),
                error_message=str(e),
                job_filename=self.job_filename
            )
            print(f"Warning: Structured glossary translation blocked by safety settings. Log saved to: {log_path}")
            return {}
        except Exception as e:
            print(f"Warning: Could not translate key terms (structured). {e}")
            return {}
    
    def _translate_terms_text(self, terms: List[str], segment_text: str) -> Dict[str, str]:
        """Translates terms using text generation (legacy)."""
        existing_glossary_str = '\n'.join([f"{k}: {v}" for k, v in self.glossary.items()])
        if not existing_glossary_str:
            existing_glossary_str = "N/A"

        prompt = PromptManager.GLOSSARY_TRANSLATE_TERMS.format(
            key_terms=', '.join(terms),
            segment_text=segment_text,
            existing_glossary=existing_glossary_str
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
