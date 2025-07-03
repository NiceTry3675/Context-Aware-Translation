import os
import json
import voyageai
import google.generativeai as genai
from dotenv import load_dotenv

def load_config():
    """Loads API keys and configuration files."""
    load_dotenv()
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("API key for Gemini must be set in .env file.")

    # Load JSON files
    try:
        with open('config/glossary.json', 'r', encoding='utf-8') as f:
            glossary = json.load(f)
        with open('config/style_guide.json', 'r', encoding='utf-8') as f:
            style_guide = json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Configuration file not found: {e.filename}. Make sure config files exist.")

    # Safety settings to be less restrictive
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    # Generation settings to reduce repetition and enhance stability
    generation_config = {
        "temperature": 0.85,
        "top_p": 0.95,
        "top_k": 40,
    }

    return {
        "gemini_api_key": gemini_api_key,
        "gemini_model_name": 'gemini-2.5-flash-lite-preview-06-17',
        "safety_settings": safety_settings,
        "generation_config": generation_config,
        "glossary": glossary,
        "style_guide": style_guide,
    }

if __name__ == '__main__':
    # Test the loader
    try:
        config = load_config()
        print("Configuration loaded successfully!")
        print("Glossary entries:", len(config['glossary']))
        print("Style guide characters:", len(config['style_guide']['characters']))
        print("Cultural notes entries:", len(config['cultural_notes']))
        print("Gemini Model and Voyage Client initialized.")
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
