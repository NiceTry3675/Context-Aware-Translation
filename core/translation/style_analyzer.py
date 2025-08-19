"""
Style Analyzer Module

This module provides comprehensive style analysis functionality for the translation engine,
including narrative style detection, glossary extraction, and style formatting.
"""

import re
from typing import Dict, Any, List, Union, Optional
from ..prompts.manager import PromptManager
from ..translation.models.gemini import GeminiModel
from ..translation.models.openrouter import OpenRouterModel
from ..errors import ProhibitedException, TranslationError
from ..errors.error_logger import prohibited_content_logger
from ..utils.file_parser import parse_document
from ..utils.text_segmentation import create_segments_from_plain_text




class StyleAnalyzer:
    """
    Analyzes and extracts style information from source documents.
    
    This class encapsulates all style-related analysis functionality,
    including narrative style detection, glossary extraction, and formatting.
    """
    
    def __init__(self, model_api: Union[GeminiModel, OpenRouterModel]):
        """
        Initialize the StyleAnalyzer.
        
        Args:
            model_api: The AI model API instance for analysis
        """
        self.model_api = model_api
    
    def extract_sample_text(self, filepath: str, method: str = "first_segment", count: int = 15000) -> str:
        """
        Extracts a sample text for analysis based on the specified method.

        Args:
            filepath: Path to the file to parse and sample from
            method: Sampling method
                - "first_segment": Use segmentation logic to build the first segment up to count chars
                - "first_chars":   Simply take the first `count` characters from the parsed document
            count: Target size (default 15000 characters)

        Returns:
            Sample text for analysis
        """
        # Parse document using centralized file parser
        text = parse_document(filepath)
        
        if method == "first_chars":
            return text[:count]
        
        if method == "first_segment":
            segments = create_segments_from_plain_text(text, count)
            return segments[0].text if segments else text[:count]
        
        # Fallback to simple character-based extraction
        return text[:count]




    def analyze_narrative_style(self, sample_text: str, job_filename: str = "unknown") -> str:
        """
        Analyzes the narrative style using the AI model.
        
        Args:
            sample_text: Text sample to analyze
            job_filename: Name of the file being processed (for logging)
            
        Returns:
            Style analysis text from the AI
        """
        prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=sample_text)
        
        try:
            style = self.model_api.generate_text(prompt)
            return style
        except ProhibitedException as e:
            log_path = prohibited_content_logger.log_simple_prohibited_content(
                api_call_type="core_style_definition",
                prompt=prompt,
                source_text=sample_text,
                error_message=str(e),
                job_filename=job_filename
            )
            print(f"Warning: Core style definition blocked. Log: {log_path}. Falling back to default.")
            return "A standard, neutral literary style ('평서체')."
        except Exception as e:
            print(f"Warning: Could not define narrative style. Error: {e}")
            # Re-raise with the specific error message from the underlying API call
            raise Exception(f"Failed to define core style: {e}") from e


    def parse_style_analysis(self, style_text: str) -> Dict[str, str]:
        """
        Parses the style analysis text into structured data.
        
        Args:
            style_text: The raw style analysis text from AI
            
        Returns:
            Dictionary with structured style data
        """
        parsed_style = {}
        key_mapping = {
            "Protagonist Name": "protagonist_name",
            "Protagonist Name (주인공 이름)": "protagonist_name",
            "Narration Style & Endings (서술 문체 및 어미)": "narration_style_endings",
            "Narration Style & Endings": "narration_style_endings",
            "Core Tone & Keywords (전체 분위기)": "tone_keywords",
            "Core Tone & Keywords": "tone_keywords",
            "Key Stylistic Rule (The \"Golden Rule\")": "stylistic_rule",
            "Key Stylistic Rule": "stylistic_rule",
        }

        for key_pattern, json_key in key_mapping.items():
            pattern = re.escape(key_pattern) + r":\s*(.*?)(?=\s*\d\.\s*|$)"
            match = re.search(pattern, style_text, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip().replace('**', '')
                parsed_style[json_key] = value
                
        return parsed_style


    def format_style_for_engine(self, style_data: Dict[str, str], protagonist_name: str = "protagonist") -> str:
        """
        Formats structured style data into the text format expected by the translation engine.
        
        Args:
            style_data: Dictionary with style information
            protagonist_name: Name of the protagonist
            
        Returns:
            Formatted style text for the translation engine
        """
        protagonist_name = style_data.get('protagonist_name', protagonist_name)
        style_parts = [
            f"1. **Protagonist Name:** {protagonist_name}",
            f"2. **Narration Style & Endings (서술 문체 및 어미):** {style_data.get('narration_style_endings', 'Not specified')}",
            f"3. **Core Tone & Keywords (전체 분위기):** {style_data.get('tone_keywords', 'Not specified')}",
            f"4. **Key Stylistic Rule (The \"Golden Rule\"):** {style_data.get('stylistic_rule', 'Not specified')}"
        ]
        return "\n".join(style_parts)

    def analyze_glossary(self, sample_text: str, job_filename: str = "unknown") -> str:
        """
        Analyzes the sample text to extract and translate glossary terms in two steps.
        
        Args:
            sample_text: Text sample to analyze.
            job_filename: Name of the file being processed (for logging).
            
        Returns:
            A string containing term-translation pairs, one per line.
        """
        # Step 1: Extract nouns
        noun_prompt = PromptManager.GLOSSARY_EXTRACT_NOUNS.format(segment_text=sample_text)
        try:
            print("--- Extracting nouns for glossary... ---")
            nouns_text = self.model_api.generate_text(noun_prompt)
            if "N/A" in nouns_text or not nouns_text.strip():
                print("No nouns found for glossary.")
                return ""
            print(f"Extracted nouns: {nouns_text}")
        except Exception as e:
            print(f"Warning: Could not extract nouns for glossary. Error: {e}")
            raise TranslationError(f"Failed to extract nouns: {e}") from e

        # Step 2: Translate the extracted nouns
        translate_prompt = PromptManager.GLOSSARY_TRANSLATE_TERMS.format(
            segment_text=sample_text, 
            key_terms=nouns_text,
            existing_glossary="N/A"  # No existing glossary during initial analysis
        )
        try:
            print("--- Translating extracted nouns... ---")
            translated_text = self.model_api.generate_text(translate_prompt)
            print(f"Translated terms: {translated_text}")
            return translated_text
        except Exception as e:
            print(f"Warning: Could not translate terms for glossary. Error: {e}")
            raise TranslationError(f"Failed to translate terms: {e}") from e

    def parse_glossary_analysis(self, glossary_text: str) -> List[Dict[str, str]]:
        """
        Parses the term-translation text into a list of structured dictionaries.
        
        Args:
            glossary_text: The raw text from the AI (e.g., "Term1: 번역1\nTerm2: 번역2").
            
        Returns:
            A list of dictionaries, e.g., [{"source": "Term1", "korean": "번역1"}].
        """
        parsed_glossary = []
        if not glossary_text.strip():
            return parsed_glossary

        lines = glossary_text.strip().split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                term = parts[0].strip()
                translation = parts[1].strip()
                if term and translation:
                    # Changed from "term"/"translation" to "source"/"korean" to match TranslatedTerm schema
                    parsed_glossary.append({"source": term, "korean": translation})
        
        return parsed_glossary
    
    def define_core_style(self, file_path: str, job_base_filename: str = "unknown") -> str:
        """
        Analyzes the first segment to define the core narrative style for the novel.
        
        Args:
            file_path: Path to the source file
            job_base_filename: Base filename for logging
            
        Returns:
            Core style description text
        """
        print("\n--- Defining Core Narrative Style... ---")
        # Extract sample text using simplified method
        sample_text = self.extract_sample_text(file_path, method="first_chars", count=15000)
        try:
            style = self.analyze_narrative_style(sample_text, job_base_filename)
            print(f"Style defined as: {style}")
            return style
        except Exception as e:
            print(f"Warning: Could not define narrative style. Falling back to default. Error: {e}")
            raise TranslationError(f"Failed to define core style: {e}") from e


# Keep standalone functions for backward compatibility
def extract_sample_text(filepath: str, method: str = "first_segment", count: int = 15000) -> str:
    """Backward compatibility wrapper."""
    text = parse_document(filepath)
    
    if method == "first_chars":
        return text[:count]
    
    if method == "first_segment":
        segments = create_segments_from_plain_text(text, count)
        return segments[0].text if segments else text[:count]
    
    return text[:count]

def analyze_narrative_style_with_api(
    sample_text: str,
    model_api: GeminiModel | OpenRouterModel,
    job_filename: str = "unknown"
) -> str:
    """Backward compatibility wrapper."""
    analyzer = StyleAnalyzer(model_api)
    return analyzer.analyze_narrative_style(sample_text, job_filename)

def parse_style_analysis(style_text: str) -> Dict[str, str]:
    """Backward compatibility wrapper."""
    analyzer = StyleAnalyzer(None)  # Parser doesn't need model API
    return analyzer.parse_style_analysis(style_text)

def format_style_for_engine(style_data: Dict[str, str], protagonist_name: str = "protagonist") -> str:
    """Backward compatibility wrapper."""
    analyzer = StyleAnalyzer(None)  # Formatter doesn't need model API
    return analyzer.format_style_for_engine(style_data, protagonist_name)

def analyze_glossary_with_api(sample_text: str, model_api: Union[GeminiModel, OpenRouterModel], job_filename: str = "unknown") -> str:
    """Backward compatibility wrapper."""
    analyzer = StyleAnalyzer(model_api)
    return analyzer.analyze_glossary(sample_text, job_filename)

def parse_glossary_analysis(glossary_text: str) -> List[Dict[str, str]]:
    """Backward compatibility wrapper."""
    analyzer = StyleAnalyzer(None)  # Parser doesn't need model API
    return analyzer.parse_glossary_analysis(glossary_text)

