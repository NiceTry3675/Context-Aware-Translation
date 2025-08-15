import json
import uuid
import os
import shutil
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from core.translation.job import TranslationJob
from core.translation.engine import TranslationEngine
from core.config.builder import DynamicConfigBuilder
from core.translation.style_analyzer import (
    extract_sample_text,
    analyze_narrative_style_with_api,
    parse_style_analysis,
    format_style_for_engine,
    analyze_glossary_with_api,
    parse_glossary_analysis
)
from .. import crud, models


class TranslationService:
    """Service layer for translation operations."""
    
    @staticmethod
    def get_model_api(api_key: str, model_name: str, config: dict):
        """Factory function to get the correct model API instance."""
        if api_key.startswith("sk-or-"):
            print(f"--- [API] Using OpenRouter model: {model_name} ---")
            return OpenRouterModel(
                api_key=api_key,
                model_name=model_name,
                enable_soft_retry=config.get('enable_soft_retry', True)
            )
        else:
            print(f"--- [API] Using Gemini model: {model_name} ---")
            return GeminiModel(
                api_key=api_key,
                model_name=model_name,
                safety_settings=config['safety_settings'],
                generation_config=config['generation_config'],
                enable_soft_retry=config.get('enable_soft_retry', True)
            )
    
    @staticmethod
    def validate_api_key(api_key: str, model_name: str) -> bool:
        """Validates the API key based on its prefix."""
        if api_key.startswith("sk-or-"):
            return OpenRouterModel.validate_api_key(api_key, model_name)
        else:
            return GeminiModel.validate_api_key(api_key, model_name)
    
    @staticmethod
    def analyze_style(file_path: str, api_key: str, model_name: str, filename: str) -> Dict[str, Any]:
        """Analyze the narrative style of a document."""
        initial_text = extract_sample_text(file_path, method="first_chars", count=15000)
        
        config = load_config()
        model_api = TranslationService.get_model_api(api_key, model_name, config)
        
        print("\n--- Defining Core Narrative Style via API... ---")
        style_report_text = analyze_narrative_style_with_api(initial_text, model_api, filename)
        print(f"Style defined as: {style_report_text}")
        
        parsed_style = parse_style_analysis(style_report_text)
        
        if len(parsed_style) < 3:
            found_keys = list(parsed_style.keys())
            raise ValueError(
                f"Failed to parse all style attributes from the report. "
                f"Successfully parsed: {found_keys}. "
                f"Received from AI: '{style_report_text}'"
            )
        
        return parsed_style
    
    @staticmethod
    def analyze_glossary(file_path: str, api_key: str, model_name: str, filename: str) -> list:
        """Extract glossary terms from a document."""
        initial_text = extract_sample_text(file_path, method="first_chars", count=15000)
        config = load_config()
        model_api = TranslationService.get_model_api(api_key, model_name, config)
        
        print("\n--- Extracting Glossary via API... ---")
        glossary_report_text = analyze_glossary_with_api(initial_text, model_api, filename)
        print(f"Glossary extracted as: {glossary_report_text}")
        
        parsed_glossary = parse_glossary_analysis(glossary_report_text)
        return parsed_glossary if parsed_glossary else []
    
    @staticmethod
    def save_uploaded_file(file, filename: str) -> tuple[str, str]:
        """Save an uploaded file and return the path and unique filename."""
        temp_dir = "uploads"
        os.makedirs(temp_dir, exist_ok=True)
        unique_id = uuid.uuid4()
        temp_file_path = os.path.join(temp_dir, f"temp_{unique_id}_{filename}")
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file, buffer)
        
        return temp_file_path, str(unique_id)
    
    @staticmethod
    def prepare_translation_job(
        job_id: int,
        job: models.TranslationJob,  # Pass the full job object
        api_key: str,
        model_name: str,
        style_data: Optional[str] = None,
        glossary_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare all the necessary components for a translation job."""
        config = load_config()
        gemini_api = TranslationService.get_model_api(api_key, model_name, config)
        
        translation_job = TranslationJob(
            job.filepath,
            original_filename=job.filename,
            target_segment_size=job.segment_size
        )
        
        # Process style data
        initial_core_style_text = None
        protagonist_name = "protagonist"
        
        if style_data:
            try:
                style_dict = json.loads(style_data)
                print(f"--- Using user-defined core style for Job ID: {job_id}: {style_dict} ---")
                protagonist_name = style_dict.get('protagonist_name', 'protagonist')
                initial_core_style_text = format_style_for_engine(style_dict, protagonist_name)
            except json.JSONDecodeError:
                print(f"--- WARNING: Could not decode style_data JSON for Job ID: {job_id}. Proceeding with auto-analysis. ---")
        else:
            try:
                sample_text = extract_sample_text(file_path, method="first_chars", count=15000)
                config = load_config()
                model_api = TranslationService.get_model_api(api_key, model_name, config)
                
                print(f"--- Performing automatic style analysis for Job ID: {job_id} ---")
                style_report_text = analyze_narrative_style_with_api(sample_text, model_api, filename)
                parsed_style = parse_style_analysis(style_report_text)
                protagonist_name = parsed_style.get('protagonist_name', 'protagonist')
                initial_core_style_text = format_style_for_engine(parsed_style, protagonist_name)
                print(f"--- Automatic style analysis complete for Job ID: {job_id} ---")
            except Exception as e:
                print(f"--- WARNING: Could not perform automatic style analysis for Job ID: {job_id}. Error: {e} ---")
        
        # Process glossary data
        initial_glossary = None
        if glossary_data:
            try:
                initial_glossary = json.loads(glossary_data)
                print(f"--- Using user-defined glossary for Job ID: {job_id} ---")
            except json.JSONDecodeError:
                print(f"--- WARNING: Could not decode glossary_data JSON for Job ID: {job_id}. ---")
        
        return {
            'translation_job': translation_job,
            'gemini_api': gemini_api,
            'protagonist_name': protagonist_name,
            'initial_glossary': initial_glossary,
            'initial_core_style_text': initial_core_style_text
        }
    
    @staticmethod
    def run_translation(
        job_id: int,
        translation_job: TranslationJob,
        gemini_api,
        protagonist_name: str,
        initial_glossary: Optional[dict],
        initial_core_style_text: Optional[str],
        db: Session
    ):
        """Execute the translation process."""
        # Check environment variable for structured output
        use_structured = os.getenv("USE_STRUCTURED_OUTPUT", "true").lower() == "true"
        
        dyn_config_builder = DynamicConfigBuilder(
            gemini_api,
            protagonist_name,
            initial_glossary=initial_glossary,
            use_structured=use_structured
        )
        
        engine = TranslationEngine(
            gemini_api,
            dyn_config_builder,
            db=db,
            job_id=job_id,
            initial_core_style=initial_core_style_text
        )
        
        engine.translate_job(translation_job)
    
    @staticmethod
    def get_translated_file_path(job: models.TranslationJob) -> tuple[str, str]:
        """Get the translated file path and media type for a job."""
        unique_base = os.path.splitext(os.path.basename(job.filepath))[0]
        original_filename_base, original_ext = os.path.splitext(job.filename)
        
        if original_ext.lower() == '.epub':
            output_ext = '.epub'
            media_type = 'application/epub+zip'
        else:
            output_ext = '.txt'
            media_type = 'text/plain'
        
        translated_unique_filename = f"{unique_base}_translated{output_ext}"
        file_path = os.path.join("translated_novel", translated_unique_filename)
        user_translated_filename = f"{original_filename_base}_translated{output_ext}"
        
        return file_path, user_translated_filename, media_type

    @staticmethod
    def delete_job_files(job: models.TranslationJob):
        """Delete all files associated with a translation job."""
        # 1. Source file
        if job.filepath and os.path.exists(job.filepath):
            os.remove(job.filepath)

        # 2. Translated file
        translated_path, _, _ = TranslationService.get_translated_file_path(job)
        if os.path.exists(translated_path):
            os.remove(translated_path)

        # 3. Log files
        base, _ = os.path.splitext(job.filename)
        for log_type in ["prompts", "context"]:
            log_dir = "logs/debug_prompts" if log_type == "prompts" else "logs/context_log"
            log_filename = f"{log_type}_job_{job.id}_{base}.txt"
            log_path = os.path.join(log_dir, log_filename)
            if os.path.exists(log_path):
                os.remove(log_path)

        # 4. Validation report
        if job.validation_report_path and os.path.exists(job.validation_report_path):
            os.remove(job.validation_report_path)

        # 5. Post-edit log
        if job.post_edit_log_path and os.path.exists(job.post_edit_log_path):
            os.remove(job.post_edit_log_path)