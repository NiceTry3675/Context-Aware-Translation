import os
from dotenv import load_dotenv

def load_config():
    """Loads API keys and model configuration."""
    load_dotenv()
    
    # --- 서버 제공 API 키 사용 시 (현재 비활성화) ---
    # .env 파일에서 서버의 기본 API 키를 로드합니다.
    # gemini_api_key = os.getenv("GEMINI_API_KEY")
    # if not gemini_api_key:
    #     raise ValueError("API key for Gemini must be set in .env file.")
    # -----------------------------------------

    # Safety settings to be less restrictive
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    # Generation settings to reduce repetition and enhance stability
    generation_config = {
        "temperature": 0.5,
        "top_p": 0.6,
        "top_k": 20,
        # Target ~15k tokens for model output where supported
        # Gemini/Vertex: max_output_tokens; other providers will map appropriately
        "max_output_tokens": 25000,
    }

    return {
        # "gemini_api_key": gemini_api_key, # 서버 제공 키 사용 시 주석 해제
        "gemini_model_name": 'gemini-flash-lite-latest',
        "safety_settings": safety_settings,
        "generation_config": generation_config,
        "enable_soft_retry": True,  # Enable retry with softer prompts for ProhibitedException
    }

if __name__ == '__main__':
    # Test the loader
    try:
        config = load_config()
        print("Configuration loaded successfully!")
        # print("API Key loaded:", "Yes" if config.get("gemini_api_key") else "No")
        print("Model Name:", config.get("gemini_model_name"))
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
