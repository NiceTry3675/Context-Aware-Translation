import argparse
import traceback
import os
from config_loader import load_config
from gemini_model import GeminiModel
from prompt_builder import PromptBuilder
from dynamic_config_builder import DynamicConfigBuilder
from translation_job import TranslationJob
from translation_engine import TranslationEngine
from style_guide_manager import StyleGuideManager

def main():
    """
    Main function to initialize and run the translation process.
    Can accept multiple file paths.
    """
    parser = argparse.ArgumentParser(description="Context-Aware Novel Translation System")
    parser.add_argument("filepaths", nargs='+', type=str, help="One or more absolute paths to the novel's text files.")
    args = parser.parse_args()

    try:
        # 1. Load all base configurations
        config = load_config()

        # 2. Initialize the shared GeminiModel
        gemini_api = GeminiModel(
            api_key=config['gemini_api_key'],
            model_name=config['gemini_model_name'],
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config']
        )
        
        # 3. Process each file individually
        for filepath in args.filepaths:
            if not os.path.exists(filepath):
                print(f"\n[ERROR] File not found: {filepath}. Skipping.")
                continue
            
            print(f"\n\n--- Starting translation for: {os.path.basename(filepath)} ---")
    
            # 1. Get or generate the style guide for the novel
            style_manager = StyleGuideManager(gemini_api)
            style_guide = style_manager.get_style_guide(filepath)
            # Create a job-specific config to hold the style guide
            job_config = config.copy()
            job_config['style_guide'] = style_guide

            # 2. Create NEW instances for each job to ensure state isolation
            prompt_builder = PromptBuilder()
            novel_name = os.path.splitext(os.path.basename(filepath))[0]
            dyn_config_builder = DynamicConfigBuilder(gemini_api, novel_name)
            engine = TranslationEngine(gemini_api, prompt_builder, dyn_config_builder)

            # 3. Create a new translation job from the input file
            translation_job = TranslationJob(filepath)

            # 4. Start the translation engine with the job
            engine.translate_job(translation_job, job_config)
            print(f"--- Finished translation for: {os.path.basename(filepath)} ---")


    except Exception as e:
        print(f"\n--- An unexpected error occurred in the main execution block ---")
        traceback.print_exc()

if __name__ == '__main__':
    main()

