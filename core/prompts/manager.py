import yaml
import os


class PromptManager:
    """
    Manages all prompts used in the translation system.
    This centralized approach makes it easy to view, edit, and manage prompts.
    """
    
    # Load prompts at class level
    _prompts_path = os.path.join(os.path.dirname(__file__), "prompts.yaml")
    with open(_prompts_path, "r", encoding="utf-8") as f:
        _prompts = yaml.safe_load(f)
    
    # --- Glossary Manager Prompts ---
    GLOSSARY_EXTRACT_NOUNS = _prompts["glossary"]["extract_nouns"]
    GLOSSARY_TRANSLATE_TERMS = _prompts["glossary"]["translate_terms"]
    
    # --- Character Style Manager Prompts ---
    CHARACTER_ANALYZE_DIALOGUE = _prompts["character_style"]["analyze_dialogue"]
    
    # --- Dynamic Style Analysis Prompts ---
    ANALYZE_NARRATIVE_DEVIATION = _prompts["style_analysis"]["narrative_deviation"]
    DEFINE_NARRATIVE_STYLE = _prompts["style_analysis"]["define_narrative_style"]
    
    # --- Translation Engine Prompts ---
    MAIN_TRANSLATION = _prompts["translation"]["main"]
    TURBO_TRANSLATION = _prompts["translation"].get("turbo", _prompts["translation"]["main"])  # fallback to main if missing
    SOFT_RETRY_TRANSLATION = _prompts["translation"]["soft_retry"]
    
    # --- Validation Prompts (Structured Only) ---
    VALIDATION_STRUCTURED_COMPREHENSIVE = _prompts["validation"]["structured_comprehensive"]
    VALIDATION_STRUCTURED_QUICK = _prompts["validation"]["structured_quick"]
    
    # --- Post-Edit Prompts ---
    POST_EDIT_CORRECTION = _prompts["post_edit"]["correction"]
