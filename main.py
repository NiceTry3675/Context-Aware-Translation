import argparse
import traceback
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
    """
    parser = argparse.ArgumentParser(description="Context-Aware Novel Translation System")
    parser.add_argument("filepath", type=str, help="The absolute path to the novel's text file.")
    args = parser.parse_args()

    try:
        # 1. Load all configurations
        config = load_config()

        # 2. Initialize all necessary objects (Dependency Injection)
        gemini_api = GeminiModel(
            api_key=config['gemini_api_key'],
            model_name=config['gemini_model_name'],
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config']
        )
        
        # 2a. Automatically get or generate the style guide for the novel
        style_manager = StyleGuideManager(gemini_api)
        style_guide = style_manager.get_style_guide(args.filepath)
        config['style_guide'] = style_guide # Add to config for easy access

        prompt_builder = PromptBuilder()
        dyn_config_builder = DynamicConfigBuilder(gemini_api, config['glossary_path'])
        engine = TranslationEngine(gemini_api, prompt_builder, dyn_config_builder)

        # 3. Create a new translation job from the input file
        translation_job = TranslationJob(args.filepath)

        # 4. Start the translation engine with the job
        engine.translate_job(translation_job, config)

    except FileNotFoundError as e:
        print(f"\n[ERROR] A required file was not found: {e}")
    except Exception as e:
        print(f"\n--- An unexpected error occurred in the main execution block ---")
        traceback.print_exc()

if __name__ == '__main__':
    main()

