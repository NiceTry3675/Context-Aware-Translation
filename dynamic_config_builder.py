import json
from gemini_model import GeminiModel
import re
from prompt_manager import PromptManager

class DynamicConfigBuilder:
    def __init__(self, gemini_api, novel_name):
        self.gemini_api = gemini_api
        self.novel_name = novel_name

    @staticmethod
    def _extract_key_terms(model: GeminiModel, segment_text: str) -> list[str]:
        """Step 1: Extract key term candidates from the text."""
        print("\nStep 1: Extracting key terms from segment...")
        prompt = PromptManager.EXTRACT_KEY_TERMS.format(segment_text=segment_text[:4000])
        try:
            response = model.generate_text(prompt)
            terms = sorted(list(set([term.strip() for term in response.split(',') if term.strip()])))
            print(f"Found {len(terms)} potential key terms.")
            return terms
        except Exception as e:
            print(f"Warning: Could not extract key terms. {e}")
            return []

    @staticmethod
    def _update_glossary(model: GeminiModel, terms: list[str], current_glossary: dict) -> tuple[dict, str]:
        """
        Step 2: Get translations for new terms and return the updated glossary
        and a formatted string for the prompt.
        """
        if not terms:
            return current_glossary, "- No key terms were identified for this segment."

        print("Step 2: Translating key terms and updating glossary...")
        
        new_terms = [term for term in terms if term not in current_glossary]
        updated_glossary = current_glossary.copy()

        if new_terms:
            print(f"Found {len(new_terms)} new terms to translate: {', '.join(new_terms)}")
            prompt = PromptManager.TRANSLATE_KEY_TERMS.format(key_terms=', '.join(new_terms))
            try:
                translation_response = model.generate_text(prompt)
                for line in translation_response.strip().split('\n'):
                    if ':' in line:
                        key, value = [x.strip() for x in line.split(':', 1)]
                        if key in new_terms:
                            updated_glossary[key] = value
            except Exception as e:
                print(f"Warning: Could not translate new key terms. {e}")
        else:
            print("No new key terms to translate. Using existing glossary.")

        translation_lines = [f"{term}: {updated_glossary.get(term, 'Translation not found')}" for term in terms]
        formatted_terms = "\n".join(translation_lines)
        
        return updated_glossary, formatted_terms

    @staticmethod
    def _analyze_style_and_tone(model: GeminiModel, segment_text: str, core_narrative_voice: str) -> str:
        """Step 3: Analyze for style deviations from the core narrative voice."""
        print("Step 3: Analyzing for style deviations...")
        prompt = PromptManager.ANALYZE_STYLE_AND_TONE.format(
            core_narrative_voice=core_narrative_voice,
            segment_text=segment_text[:4000]
        )
        try:
            return model.generate_text(prompt)
        except Exception as e:
            print(f"Warning: Could not analyze style and tone. {e}")
            return "- Failed to generate style and tone analysis."

    @staticmethod
    def generate_guidelines(model: GeminiModel, segment_text: str, core_narrative_voice: str, current_glossary: dict) -> tuple[dict, dict]:
        """
        Performs the full 3-step process to generate comprehensive dynamic guidelines.
        Returns the updated glossary and a dictionary of guidelines for the prompt.
        """
        extracted_terms = DynamicConfigBuilder._extract_key_terms(model, segment_text)
        updated_glossary, formatted_terms = DynamicConfigBuilder._update_glossary(model, extracted_terms, current_glossary)
        style_analysis = DynamicConfigBuilder._analyze_style_and_tone(model, segment_text, core_narrative_voice)
        
        print("Dynamic guidelines generated successfully.")
        
        prompt_guidelines = {
            "glossary_terms": formatted_terms,
            "style_analysis": style_analysis
        }
        
        return updated_glossary, prompt_guidelines

