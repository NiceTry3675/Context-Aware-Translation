import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from core.translation.document import TranslationDocument
from core.translation.translation_pipeline import TranslationPipeline
from core.config.builder import DynamicConfigBuilder
from .base.base_service import BaseService
from .style_analysis_service import StyleAnalysisService
from .glossary_analysis_service import GlossaryAnalysisService
from .. import models


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
        glossary_data: Optional[str] = None,
        translation_model_name: Optional[str] = None,
        style_model_name: Optional[str] = None,
        glossary_model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare all the necessary components for a translation job."""
        # Fallbacks: if specific per-task models are not provided, use the top-level model_name
        translation_model_name = translation_model_name or model_name
        style_model_name = style_model_name or model_name
        glossary_model_name = glossary_model_name or model_name

        # Create per-task model APIs
        model_api = self.create_model_api(api_key, translation_model_name)
        style_model_api = self.create_model_api(api_key, style_model_name) if style_model_name else model_api
        glossary_model_api = self.create_model_api(api_key, glossary_model_name) if glossary_model_name else model_api
        
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
                model_name=style_model_name,
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
                model_name=glossary_model_name,
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
            'style_model_api': style_model_api,
            'glossary_model_api': glossary_model_api,
            'protagonist_name': protagonist_name,
            'initial_glossary': initial_glossary,
            'initial_core_style_text': initial_core_style_text
        }
    
    @staticmethod
    def run_translation(
        job_id: int,
        translation_document: TranslationDocument,
        model_api,
        style_model_api,
        glossary_model_api,
        protagonist_name: str,
        initial_glossary: Optional[dict],
        initial_core_style_text: Optional[str],
        db: Session
    ):
        """Execute the translation process."""
        # Always use structured output for configuration extraction
        # Prefer the glossary/analysis model for dynamic guides if it supports structured output
        dyn_model_for_guides = glossary_model_api if hasattr(glossary_model_api, 'generate_structured') else model_api
        if dyn_model_for_guides is model_api and glossary_model_api is not None and glossary_model_api is not model_api:
            print("Warning: Selected glossary/analysis model does not support structured output. Falling back to main model for dynamic guides.")

        dyn_config_builder = DynamicConfigBuilder(
            dyn_model_for_guides,
            protagonist_name,
            initial_glossary=initial_glossary
        )
        
        pipeline = TranslationPipeline(
            model_api,
            dyn_config_builder,
            db=db,
            job_id=job_id,
            initial_core_style=initial_core_style_text,
            style_model_api=style_model_api,
        )
        
        pipeline.translate_document(translation_document)
    
