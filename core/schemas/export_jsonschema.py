#!/usr/bin/env python3
"""
Export JSON Schema from Pydantic models for frontend TypeScript generation.

This script exports JSON schemas from domain models that the frontend
needs to render directly (e.g., validation reports, glossary terms).
"""

from pathlib import Path
import json
from typing import Type
from pydantic import BaseModel

# Import all models that need schema export
from .validation import ValidationResponse, ValidationCase
from .glossary import ExtractedTerms, TranslatedTerms, TranslatedTerm
from .character_style import CharacterInteraction, DialogueAnalysisResult
from .narrative_style import NarrativeStyleDefinition, StyleDeviation, NarrationStyle
from .illustration import (
    VisualElements, CharacterVisualInfo, LightingInfo, CameraInfo,
    IllustrationData, IllustrationConfig, IllustrationBatch
)


# Output directory for JSON schemas
OUTPUT_DIR = Path(__file__).parent / "jsonschema"


def export_model_schema(model: Type[BaseModel], name: str) -> None:
    """
    Export a Pydantic model's JSON schema to a file.
    
    Args:
        model: The Pydantic model class
        name: The name to use for the output file
    """
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Generate JSON schema using Pydantic v2 method
    schema = model.model_json_schema()
    
    # Write to file with pretty formatting
    output_file = OUTPUT_DIR / f"{name}.schema.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Exported {name} schema to {output_file}")


def main():
    """Export all required schemas for frontend consumption."""
    
    print("Exporting JSON schemas for frontend TypeScript generation...")
    
    # Models used directly in the frontend UI
    models_to_export = [
        # Validation models (used in validation reports)
        (ValidationResponse, "ValidationResponse"),
        (ValidationCase, "ValidationCase"),
        
        # Glossary models (used in glossary display)
        (ExtractedTerms, "ExtractedTerms"),
        (TranslatedTerms, "TranslatedTerms"),
        (TranslatedTerm, "TranslatedTerm"),
        
        # Character style models (used in character analysis)
        (CharacterInteraction, "CharacterInteraction"),
        (DialogueAnalysisResult, "DialogueAnalysisResult"),
        
        # Narrative style models (used in style analysis)
        (NarrativeStyleDefinition, "NarrativeStyleDefinition"),
        (NarrationStyle, "NarrationStyle"),
        (StyleDeviation, "StyleDeviation"),
        
        # Illustration models (used in illustration generation)
        (VisualElements, "VisualElements"),
        (CharacterVisualInfo, "CharacterVisualInfo"),
        (LightingInfo, "LightingInfo"),
        (CameraInfo, "CameraInfo"),
        (IllustrationData, "IllustrationData"),
        (IllustrationConfig, "IllustrationConfig"),
        (IllustrationBatch, "IllustrationBatch"),
    ]
    
    # Export each model
    for model_class, model_name in models_to_export:
        export_model_schema(model_class, model_name)
    
    print(f"\n✅ Successfully exported {len(models_to_export)} schemas to {OUTPUT_DIR}/")
    print("\nNext steps:")
    print("  1. Run 'npm run codegen:schemas' in the frontend to generate TypeScript types")
    print("  2. Import generated types from 'src/types/schemas/' in your components")


if __name__ == "__main__":
    main()