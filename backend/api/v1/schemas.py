"""Schemas API router for exposing core JSON schemas."""

from fastapi import APIRouter
from typing import Dict, Any

from core.schemas import (
    ExtractedTerms,
    TranslatedTerms,
    CharacterInteraction,
    DialogueAnalysisResult,
    NarrativeStyleDefinition,
    StyleDeviation,
    ValidationResponse,
    ValidationCase
)

router = APIRouter(prefix="/api/v1/schemas", tags=["schemas"])


@router.get("/core", response_model=Dict[str, Any])
def get_core_schemas() -> Dict[str, Any]:
    """
    Get all core JSON schemas used in structured output.
    
    Returns a dictionary mapping schema names to their JSON schema definitions.
    These schemas are used by Gemini's structured output feature.
    """
    models = [
        ExtractedTerms,
        TranslatedTerms,
        CharacterInteraction,
        DialogueAnalysisResult,
        NarrativeStyleDefinition,
        StyleDeviation,
        ValidationResponse,
        ValidationCase
    ]
    
    return {
        model.__name__: model.model_json_schema() 
        for model in models
    }


@router.get("/core/{schema_name}", response_model=Dict[str, Any])
def get_core_schema(schema_name: str) -> Dict[str, Any]:
    """
    Get a specific core JSON schema by name.
    
    Args:
        schema_name: Name of the schema to retrieve
        
    Returns:
        The JSON schema definition for the specified schema
        
    Raises:
        404 if schema not found
    """
    schema_map = {
        "ExtractedTerms": ExtractedTerms,
        "TranslatedTerms": TranslatedTerms,
        "CharacterInteraction": CharacterInteraction,
        "DialogueAnalysisResult": DialogueAnalysisResult,
        "NarrativeStyleDefinition": NarrativeStyleDefinition,
        "StyleDeviation": StyleDeviation,
        "ValidationResponse": ValidationResponse,
        "ValidationCase": ValidationCase
    }
    
    if schema_name not in schema_map:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{schema_name}' not found. Available schemas: {list(schema_map.keys())}"
        )
    
    return schema_map[schema_name].model_json_schema()


@router.get("/backend", response_model=Dict[str, Any])
def get_backend_schemas() -> Dict[str, Any]:
    """
    Get all backend API schemas (DTOs).
    
    Returns schemas used in FastAPI endpoints for request/response models.
    """
    from backend.domains.translation.schemas import (
        TranslationJob,
        TranslationJobCreate,
        StyleAnalysisResponse,
        GlossaryAnalysisResponse,
        ValidationRequest,
        PostEditRequest
    )
    from backend.domains.community.schemas import (
        Post,
        PostCreate,
        Comment,
        CommentCreate,
        PostCategory
    )
    from backend.domains.user.schemas import (
        User,
        Announcement,
        AnnouncementCreate
    )
    
    backend_models = [
        TranslationJob,
        TranslationJobCreate,
        Post,
        PostCreate,
        Comment,
        CommentCreate,
        PostCategory,
        Announcement,
        AnnouncementCreate,
        StyleAnalysisResponse,
        GlossaryAnalysisResponse,
        ValidationRequest,
        PostEditRequest,
        User
    ]
    
    return {
        model.__name__: model.model_json_schema()
        for model in backend_models
    }