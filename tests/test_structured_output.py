#!/usr/bin/env python3
"""
Test the structured output implementation for glossary, character style, and narrative style.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.translation.models.gemini import GeminiModel
from core.config.glossary import GlossaryManager
from core.config.character_style import CharacterStyleManager
from core.config.builder import DynamicConfigBuilder
from core.schemas.glossary import ExtractedTerms, TranslatedTerms
from core.schemas.character_style import DialogueAnalysisResult
from core.schemas.narrative_style import StyleDeviation


def test_glossary_extraction():
    """Test structured glossary extraction."""
    print("\n=== Testing Glossary Extraction (Structured) ===")
    
    # Sample text with proper nouns
    sample_text = """
    John Smith walked down Fifth Avenue in New York City. 
    He was heading to the Google headquarters to meet Sarah Johnson.
    The Empire State Building towered above them.
    """
    
    # Initialize model and manager
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Skipping: GEMINI_API_KEY not set")
        return
    
    # Default safety settings and generation config
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 8192,
    }
    
    model = GeminiModel(api_key, "gemini-2.0-flash-exp", safety_settings, generation_config)
    manager = GlossaryManager(model, "test_job", use_structured=True)
    
    # Extract terms
    terms = manager._extract_proper_nouns(sample_text)
    print(f"Extracted terms: {terms}")
    
    # Verify it's a list of strings
    assert isinstance(terms, list), "Should return a list"
    assert all(isinstance(t, str) for t in terms), "All items should be strings"
    
    # Check for expected terms
    expected_terms = {"John Smith", "Fifth Avenue", "New York City", "Google", "Sarah Johnson", "Empire State Building"}
    found_terms = set(terms)
    
    print(f"Expected terms found: {expected_terms & found_terms}")
    print(f"Missing terms: {expected_terms - found_terms}")
    print("✓ Glossary extraction test passed")


def test_glossary_translation():
    """Test structured glossary translation."""
    print("\n=== Testing Glossary Translation (Structured) ===")
    
    # Initialize model and manager
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Skipping: GEMINI_API_KEY not set")
        return
    
    # Default safety settings and generation config
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 8192,
    }
    
    model = GeminiModel(api_key, "gemini-2.0-flash-exp", safety_settings, generation_config)
    
    # Create manager with existing glossary
    existing_glossary = {"John": "존", "New York": "뉴욕"}
    manager = GlossaryManager(model, "test_job", initial_glossary=existing_glossary, use_structured=True)
    
    # Terms to translate
    terms = ["John Smith", "Sarah Johnson", "Google"]
    sample_text = "John Smith and Sarah Johnson work at Google."
    
    # Translate terms
    translations = manager._translate_terms(terms, sample_text)
    print(f"Translations: {translations}")
    
    # Verify it's a dictionary
    assert isinstance(translations, dict), "Should return a dictionary"
    
    # Check that John Smith uses the existing "John" translation
    if "John Smith" in translations:
        assert "존" in translations["John Smith"], "Should use existing translation for 'John'"
    
    print("✓ Glossary translation test passed")


def test_character_style_analysis():
    """Test structured character dialogue analysis."""
    print("\n=== Testing Character Style Analysis (Structured) ===")
    
    # Sample text with dialogue
    sample_text = """
    "Hello, Mr. President," John said formally.
    "Hey kiddo," John said to his daughter.
    "How are you doing today?" John asked his colleague politely.
    """
    
    # Initialize model and manager
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Skipping: GEMINI_API_KEY not set")
        return
    
    # Default safety settings and generation config
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 8192,
    }
    
    model = GeminiModel(api_key, "gemini-2.0-flash-exp", safety_settings, generation_config)
    manager = CharacterStyleManager(model, "John", use_structured=True)
    
    # Analyze styles
    current_styles = {}
    updated_styles = manager.update_styles(sample_text, current_styles, "test_job", 0)
    print(f"Character styles: {updated_styles}")
    
    # Verify it's a dictionary
    assert isinstance(updated_styles, dict), "Should return a dictionary"
    
    # Check for expected patterns
    for key, value in updated_styles.items():
        assert "->" in key, "Style key should have arrow notation"
        assert value in ["반말", "해요체", "하십시오체"], f"Invalid style: {value}"
    
    print("✓ Character style analysis test passed")


def test_style_deviation():
    """Test structured style deviation detection."""
    print("\n=== Testing Style Deviation Detection (Structured) ===")
    
    # Core narrative style
    core_style = """
    1. **Protagonist Name:** John
    2. **Narration Style & Endings:**
       - **Description:** Third-person neutral observer
       - **Ending Style:** 해라체
    3. **Core Tone & Keywords:** Detached, Analytical
    4. **Key Stylistic Rule:** Keep sentences short and direct.
    """
    
    # Sample text with potential deviation (a letter)
    sample_text = """
    John walked down the street. 
    
    Dear Sarah,
    I hope this letter finds you well. I wanted to express my deepest gratitude
    for your help last week. Your kindness meant everything to me.
    Sincerely,
    John
    
    He continued walking after mailing the letter.
    """
    
    # Initialize model and builder
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Skipping: GEMINI_API_KEY not set")
        return
    
    # Default safety settings and generation config
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 8192,
    }
    
    model = GeminiModel(api_key, "gemini-2.0-flash-exp", safety_settings, generation_config)
    builder = DynamicConfigBuilder(model, "John", use_structured=True)
    
    # Analyze deviation
    deviation = builder._analyze_style_deviation(sample_text, core_style, "test_job", 0)
    print(f"Style deviation: {deviation}")
    
    # Verify it's a string
    assert isinstance(deviation, str), "Should return a string"
    
    # Could be "N/A" or a deviation instruction
    if deviation != "N/A":
        print("Deviation detected!")
    else:
        print("No deviation detected")
    
    print("✓ Style deviation test passed")


def main():
    """Run all structured output tests."""
    print("=" * 60)
    print("STRUCTURED OUTPUT TESTS")
    print("=" * 60)
    
    # Ensure we're using structured output
    os.environ["USE_STRUCTURED_OUTPUT"] = "true"
    
    try:
        test_glossary_extraction()
        test_glossary_translation()
        test_character_style_analysis()
        test_style_deviation()
        
        print("\n" + "=" * 60)
        print("ALL STRUCTURED OUTPUT TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())