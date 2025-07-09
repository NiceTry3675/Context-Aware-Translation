import argparse
import traceback
import os
import sys
import io
from config_loader import load_config
from gemini_model import GeminiModel
from dynamic_config_builder import DynamicConfigBuilder
from translation_job import TranslationJob
from translation_engine import TranslationEngine

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    """
    Main function to initialize and run the translation process.
    """
    parser = argparse.ArgumentParser(description="Context-Aware Novel Translation System")
    parser.add_argument("filepath", type=str, help="The absolute path to the novel's text file.")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"[ERROR] File not found: {args.filepath}")
        return

    try:
        # 1. Load base configurations
        config = load_config()

        # 2. Initialize the shared GeminiModel
        gemini_api = GeminiModel(
            api_key=config['gemini_api_key'],
            model_name=config['gemini_model_name'],
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config']
        )
        
        print(f"\n--- Starting translation for: {os.path.basename(args.filepath)} ---")

        # 3. Create a new translation job from the input file
        translation_job = TranslationJob(args.filepath)

        # 4. Initialize the main dynamic config builder and the translation engine
        novel_name = translation_job.base_filename
        dyn_config_builder = DynamicConfigBuilder(gemini_api, novel_name)
        engine = TranslationEngine(gemini_api, dyn_config_builder)

        # 5. Start the translation engine with the job
        engine.translate_job(translation_job)

    except Exception as e:
        print(f"\n--- An unexpected error occurred in the main execution block ---")
        traceback.print_exc()

if __name__ == '__main__':
    main()
