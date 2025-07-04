import json
from gemini_model import GeminiModel
import re
from prompt_manager import PromptManager


class DynamicConfigBuilder:
    """
    Analyzes a text segment to generate comprehensive, multi-part dynamic guidelines
    in a structured, 3-step process. It now integrates with a glossary for consistent term translation.
    """
    def __init__(self, gemini_model: GeminiModel, glossary_path: str):
        self.model = gemini_model
        self.glossary_path = glossary_path
        self.glossary = self._load_glossary()

    def _load_glossary(self) -> dict:
        """Loads the glossary from the specified JSON file."""
        try:
            with open(self.glossary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Warning: Glossary not found or invalid. Starting with an empty glossary.")
            return {}

    def _save_glossary(self):
        """Saves the current glossary to the JSON file."""
        try:
            with open(self.glossary_path, 'w', encoding='utf-8') as f:
                json.dump(self.glossary, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error: Could not save glossary to {self.glossary_path}. {e}")

    def _extract_key_terms(self, segment_text: str) -> list[str]:
        """Step 1: Extract key term candidates from the text with a refined prompt."""
        print("\nStep 1: Extracting key terms from segment...")
        prompt = PromptManager.EXTRACT_KEY_TERMS.format(segment_text=segment_text[:4000])
        try:
            response = self.model.generate_text(prompt)
            terms = sorted(list(set([term.strip() for term in response.split(',') if term.strip()])))
            print(f"Found {len(terms)} potential key terms.")
            return terms
        except Exception as e:
            print(f"Warning: Could not extract key terms. {e}")
            return []

    def _update_and_get_translations(self, terms: list[str]) -> str:
        """
        Step 2: Get translations for terms, using the glossary for consistency.
        New translations are requested from the model and saved to the glossary.
        """
        if not terms:
            return "- No key terms were identified for this segment."

        print("Step 2: Translating key terms and updating glossary...")
        
        new_terms = [term for term in terms if term not in self.glossary]
        updated = False

        if new_terms:
            print(f"Found {len(new_terms)} new terms to translate: {', '.join(new_terms)}")
            prompt = PromptManager.TRANSLATE_KEY_TERMS.format(key_terms=', '.join(new_terms))
            try:
                translation_response = self.model.generate_text(prompt)
                # Parse the response and update the glossary
                for line in translation_response.strip().split('\n'):
                    if ':' in line:
                        key, value = [x.strip() for x in line.split(':', 1)]
                        if key in new_terms:
                            self.glossary[key] = value
                            updated = True
            except Exception as e:
                print(f"Warning: Could not translate new key terms. {e}")
        else:
            print("No new key terms to translate. Using existing glossary.")

        if updated:
            self._save_glossary()

        # Format the output using all terms (old and new) from the current segment
        translation_lines = [f"{term}: {self.glossary.get(term, 'Translation not found')}" for term in terms]
        return "\n".join(translation_lines)


    def _analyze_style_and_tone(self, segment_text: str) -> str:
        """Step 3: Analyze the style and tone to create practical translation guidelines."""
        print("Step 3: Analyzing style and tone for practical guidelines...")
        prompt = PromptManager.ANALYZE_STYLE_AND_TONE.format(segment_text=segment_text[:4000])
        try:
            return self.model.generate_text(prompt)
        except Exception as e:
            print(f"Warning: Could not analyze style and tone. {e}")
            return "- Failed to generate style and tone analysis."

    def generate_guidelines(self, segment_text: str) -> dict:
        """
        Performs the full 3-step process to generate comprehensive dynamic guidelines.
        Returns a dictionary with 'glossary_terms' and 'style_analysis'.
        """
        extracted_terms = self._extract_key_terms(segment_text)
        term_translations = self._update_and_get_translations(extracted_terms)
        style_analysis = self._analyze_style_and_tone(segment_text)
        
        print("Dynamic guidelines generated successfully.")
        return {
            "glossary_terms": term_translations,
            "style_analysis": style_analysis
        }

    def update_and_log_context(self, segment_text: str, static_rules: str, context_log_path: str, segment_num: int):
        """
        Generates dynamic guidelines, combines them with static rules,
        and logs them to the context file.
        """
        print(f"\n--- Building dynamic context for segment {segment_num} ---")
        guidelines = self.generate_guidelines(segment_text)
        dynamic_guidelines = (
            "Key Term Translations:\n"
            f"{guidelines['glossary_terms']}\n\n"
            "Style and Tone Analysis:\n"
            f"{guidelines['style_analysis']}"
        )

        # Read existing log content
        try:
            with open(context_log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
        except FileNotFoundError:
            log_content = f"# CONTEXT LOG FOR: {context_log_path.split('_')[-1].replace('.txt', '')}\n"

        # Prepare new entry
        new_log_entry = (
            f"\n--- CONTEXT FOR SEGMENT {segment_num} ---\n\n"
            "### Static Rules Used:\n"
            f"{static_rules}\n\n"
            "### AI-Generated Guidelines Used:\n"
            f"{dynamic_guidelines}\n\n"
            "### Immediate Context Used (English):\n"
            "N/A\n\n"
            "### Immediate Context Used (Korean):\n"
            "N/A\n"
            "\n==================================================\n"
        )

        # Append and write back
        with open(context_log_path, 'w', encoding='utf-8') as f:
            f.write(log_content + new_log_entry)
        
        print(f"Context for segment {segment_num} logged to {context_log_path}")