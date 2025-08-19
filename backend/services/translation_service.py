import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from core.translation.document import TranslationDocument
from core.translation.translation_pipeline import TranslationPipeline
from core.config.builder import DynamicConfigBuilder
from .base.base_service import BaseService
from .style_analysis_service import StyleAnalysisService
from .glossary_analysis_service import GlossaryAnalysisService
from .. import crud, models


class TranslationService(BaseService):
    """Service layer for translation operations."""
    
    def __init__(self):
        """Initialize translation service."""
        super().__init__()
    
    
    
    
    def prepare_translation_job(
        self,
        job_id: int,
        job: models.TranslationJob,  # Pass the full job object
        api_key: str,
        model_name: str,
        style_data: Optional[str] = None,
        glossary_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare all the necessary components for a translation job."""
        model_api = self.create_model_api(api_key, model_name)
        
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
            style_service = StyleAnalysisService()
            style_result = style_service.analyze_style(
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
            
            glossary_service = GlossaryAnalysisService()
            initial_glossary = glossary_service.analyze_glossary(
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
            'model_api': model_api,
            'protagonist_name': protagonist_name,
            'initial_glossary': initial_glossary,
            'initial_core_style_text': initial_core_style_text
        }
    
    @staticmethod
    def run_translation(
        job_id: int,
        translation_document: TranslationDocument,
        model_api,
        protagonist_name: str,
        initial_glossary: Optional[dict],
        initial_core_style_text: Optional[str],
        db: Session
    ):
        """Execute the translation process."""
        # Always use structured output for configuration extraction
        
        dyn_config_builder = DynamicConfigBuilder(
            model_api,
            protagonist_name,
            initial_glossary=initial_glossary
        )
        
        pipeline = TranslationPipeline(
            model_api,
            dyn_config_builder,
            db=db,
            job_id=job_id,
            initial_core_style=initial_core_style_text
        )
        
        pipeline.translate_document(translation_document)
    

