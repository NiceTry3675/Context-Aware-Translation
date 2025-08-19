import json
import uuid
import os
import shutil
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from core.translation.translation_document import TranslationDocument
from core.translation.translation_pipeline import TranslationPipeline
from core.config.builder import DynamicConfigBuilder
from .style_analysis_service import StyleAnalysisService
from .glossary_analysis_service import GlossaryAnalysisService
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
        
        translation_document = TranslationDocument(
            job.filepath,
            original_filename=job.filename,
            target_segment_size=job.segment_size
        )
        
        # Process style data using StyleAnalysisService
        initial_core_style_text = None
        protagonist_name = "protagonist"
        
        try:
            print(f"--- Analyzing style for Job ID: {job_id} ---")
            style_result = StyleAnalysisService.analyze_style(
                filepath=job.filepath,
                api_key=api_key,
                model_name=model_name,
                user_style_data=style_data
            )
            
            protagonist_name = style_result['protagonist_name']
            initial_core_style_text = style_result['style_text']
            
            if style_result['source'] == 'user_provided':
                print(f"--- Using user-defined style for Job ID: {job_id} ---")
            else:
                print(f"--- Automatic style analysis complete for Job ID: {job_id} ---")
                
        except Exception as e:
            print(f"--- WARNING: Style analysis failed for Job ID: {job_id}. Error: {e} ---")
            # Use fallback values
            protagonist_name = "protagonist"
            initial_core_style_text = None
        
        # Process glossary data using GlossaryAnalysisService
        initial_glossary = None
        try:
            if glossary_data:
                print(f"--- Processing user-defined glossary for Job ID: {job_id} ---")
            else:
                print(f"--- Extracting automatic glossary for Job ID: {job_id} ---")
            
            initial_glossary = GlossaryAnalysisService.analyze_glossary(
                filepath=job.filepath,
                api_key=api_key,
                model_name=model_name,
                user_glossary_data=glossary_data
            )
            
            if initial_glossary:
                print(f"--- Glossary prepared with {len(initial_glossary)} terms for Job ID: {job_id} ---")
                
        except Exception as e:
            print(f"--- WARNING: Glossary analysis failed for Job ID: {job_id}. Error: {e} ---")
            initial_glossary = None
        
        return {
            'translation_document': translation_document,
            'gemini_api': gemini_api,
            'protagonist_name': protagonist_name,
            'initial_glossary': initial_glossary,
            'initial_core_style_text': initial_core_style_text
        }
    
    @staticmethod
    def run_translation(
        job_id: int,
        translation_document: TranslationDocument,
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
        
        pipeline = TranslationPipeline(
            gemini_api,
            dyn_config_builder,
            db=db,
            job_id=job_id,
            initial_core_style=initial_core_style_text
        )
        
        pipeline.translate_document(translation_document)
    
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