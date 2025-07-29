#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.config.builder import DynamicConfigBuilder
from core.translation.job import TranslationJob
from core.translation.engine import TranslationEngine
from core.errors.base import TranslationError
from core.utils.file_parser import parse_document


def translate(source_file: str, target_file: Optional[str] = None, api_key: Optional[str] = None, 
              segment_size: int = 10000, verbose: bool = False) -> None:
    """
    Translate a novel from a source language to Korean using the Context-Aware Translation system.
    
    Args:
        source_file: Path to the source file to translate
        target_file: Path to save the translated file (optional)
        api_key: Google Gemini API key
        segment_size: Size of text segments for translation
        verbose: Enable verbose output
    """
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Validate source file
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        # Load configuration
        config = load_config()
        
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("API key required. Provide via --api-key or GEMINI_API_KEY environment variable")
        
        # Validate API key
        if verbose:
            print("Validating API key...")
        
        # Use the model name from config for validation
        model_name = config.get('gemini_model_name', 'gemini-2.5-flash-lite')
        if not GeminiModel.validate_api_key(api_key, model_name):
            raise ValueError("Invalid API key provided")
        
        # Create Gemini model instance
        gemini_model = GeminiModel(
            api_key=api_key,
            model_name=config['gemini_model_name'],
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config'],
            enable_soft_retry=config.get('enable_soft_retry', True)
        )
        
        # Create translation job
        if verbose:
            print(f"Creating translation job for: {source_file}")
            print(f"Segment size: {segment_size}")
        
        job = TranslationJob(source_file, target_segment_size=segment_size)
        
        if verbose:
            print(f"Created {len(job.segments)} segments from source file")
        
        # Extract book title from filename
        book_title = Path(source_file).stem.replace('_', ' ').title()
        
        # Create dynamic config builder
        if verbose:
            print(f"Initializing dynamic config builder for: {book_title}")
        
        dyn_config_builder = DynamicConfigBuilder(gemini_model, book_title)
        
        # Create translation engine (no database for CLI mode)
        engine = TranslationEngine(gemini_model, dyn_config_builder, db=None, job_id=None)
        
        # Run translation
        if verbose:
            print("Starting translation...")
            print("-" * 50)
        
        # Verbose mode is already handled by the engine's progress display
        
        # Execute translation
        engine.translate_job(job)
        
        # Handle output file
        if target_file:
            # Move the output file to the target location
            os.rename(job.output_filename, target_file)
            output_path = target_file
        else:
            output_path = job.output_filename
        
        # Print summary
        print(f"\nTranslation completed successfully!")
        print(f"Output file: {output_path}")
        print(f"Glossary entries: {len(job.glossary)}")
        print(f"Character styles: {len(job.character_styles)}")
        
        if verbose and job.glossary:
            print("\nGlossary sample:")
            for term, translation in list(job.glossary.items())[:5]:
                print(f"  {term} → {translation}")
    
    except TranslationError as e:
        print(f"Translation error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Context-Aware Literary Translation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate with API key from environment
  %(prog)s novel.txt

  # Translate with explicit output file
  %(prog)s novel.txt translated_novel.txt

  # Translate with API key and custom segment size
  %(prog)s novel.txt -k YOUR_API_KEY -s 15000

  # Enable verbose output
  %(prog)s novel.txt -v
        """
    )
    
    # Positional arguments
    parser.add_argument('source', help='Source file to translate')
    parser.add_argument('target', nargs='?', help='Target output file (optional)')
    
    # Optional arguments
    parser.add_argument('-k', '--api-key', help='Google Gemini API key')
    parser.add_argument('-s', '--segment-size', type=int, default=10000,
                        help='Target segment size for translation (default: 10000)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Run translation
    translate(
        source_file=args.source,
        target_file=args.target,
        api_key=args.api_key,
        segment_size=args.segment_size,
        verbose=args.verbose
    )


if __name__ == '__main__':
    main()