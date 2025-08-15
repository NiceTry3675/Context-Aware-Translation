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
from core.translation.style_analyzer import extract_sample_text, analyze_narrative_style_with_api, parse_style_analysis
from core.validation.validator import TranslationValidator
from core.translation.post_editor import PostEditEngine


def translate(source_file: str, target_file: Optional[str] = None, api_key: Optional[str] = None, 
              segment_size: int = 10000, verbose: bool = False, with_validation: bool = False,
              validation_sample_rate: float = 1.0, quick_validation: bool = False, post_edit: bool = False) -> None:
    """
    Translate a novel from a source language to Korean using the Context-Aware Translation system.
    
    Args:
        source_file: Path to the source file to translate
        target_file: Path to save the translated file (optional)
        api_key: Google Gemini API key
        segment_size: Size of text segments for translation
        verbose: Enable verbose output
        with_validation: Run validation after translation
        validation_sample_rate: Percentage of segments to validate (0.0 to 1.0)
        quick_validation: Use quick validation mode instead of comprehensive
        post_edit: Apply post-editing to fix validation issues
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
        
        # Analyze protagonist name from the text
        if verbose:
            print("\n--- Analyzing Protagonist Name... ---")
        
        try:
            sample_text = extract_sample_text(source_file)
            # Use the filename for logging purposes in the analyzer
            job_filename = Path(source_file).stem
            style_analysis_text = analyze_narrative_style_with_api(sample_text, gemini_model, job_filename=job_filename)
            parsed_style = parse_style_analysis(style_analysis_text)
            protagonist_name = parsed_style.get('protagonist_name')

            if not protagonist_name:
                print("Warning: Could not determine protagonist name from analysis. Falling back to filename.")
                protagonist_name = Path(source_file).stem.replace('_', ' ').title()
            else:
                 if verbose:
                    print(f"Protagonist identified as: {protagonist_name}")

        except Exception as e:
            print(f"Warning: Failed to analyze protagonist name due to an error: {e}. Falling back to filename.")
            protagonist_name = Path(source_file).stem.replace('_', ' ').title()

        # Create dynamic config builder
        if verbose:
            print(f"\nInitializing dynamic config builder for protagonist: {protagonist_name}")
        
        # Check environment variable for structured output
        use_structured = os.getenv("USE_STRUCTURED_OUTPUT", "true").lower() == "true"
        if verbose and use_structured:
            print("Using structured output for configuration extraction")
        
        dyn_config_builder = DynamicConfigBuilder(
            gemini_model, 
            protagonist_name,
            use_structured=use_structured
        )
        
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
        
        # Run validation if requested
        if with_validation:
            print("\n" + "="*60)
            print("Running Translation Validation")
            print("="*60)
            
            validator = TranslationValidator(gemini_model, verbose=verbose)
            validation_results, validation_summary = validator.validate_job(
                translation_job=job,
                sample_rate=validation_sample_rate,
                quick_mode=quick_validation
            )
            
            # Show additional details based on validation results
            if validation_summary['pass_rate'] < 70:
                print("\n⚠️  WARNING: Translation validation found significant issues!")
                print("\nIssue Summary:")
                if validation_summary['total_critical_issues'] > 0:
                    print(f"  🔴 {validation_summary['total_critical_issues']} critical issues found")
                if validation_summary['total_missing_content'] > 0:
                    print(f"  ⚠️  {validation_summary['total_missing_content']} pieces of missing content")
                if validation_summary['total_added_content'] > 0:
                    print(f"  ➕ {validation_summary['total_added_content']} pieces of added content")
                if validation_summary['total_name_inconsistencies'] > 0:
                    print(f"  👤 {validation_summary['total_name_inconsistencies']} name inconsistencies")
                
                print(f"\nPlease review the validation report for full details.")
                print(f"Report location: logs/validation_logs/{job.user_base_filename}_validation_report.json")
            elif validation_summary['pass_rate'] >= 95:
                print("\n✅ Excellent! Translation passed validation with high quality.")
            elif validation_summary['pass_rate'] >= 85:
                print("\n✅ Good! Translation passed validation with minor issues.")
            
            # Run post-edit if requested and validation was performed
            if post_edit:
                print("\n" + "="*60)
                print("Running Post-Edit Process")
                print("="*60)
                
                # Check if validation report exists
                validation_report_path = f"logs/validation_logs/{job.user_base_filename}_validation_report.json"
                if not os.path.exists(validation_report_path):
                    print("Error: Validation report not found. Post-edit requires validation to be run first.")
                    print("Please run with --with-validation flag.")
                else:
                    post_editor = PostEditEngine(gemini_model, verbose=verbose)
                    edited_segments, edit_summary = post_editor.post_edit_job(job, validation_report_path)
                    
                    # Save the post-edited translation
                    if edit_summary['segments_edited'] > 0:
                        # Generate post-edited output filename
                        base_name = os.path.splitext(output_path)[0]
                        post_edit_output = f"{base_name}_postedited.txt"
                        
                        # Write post-edited translation
                        job.save_translation(post_edit_output)
                        print(f"\nPost-edited translation saved to: {post_edit_output}")
                        
                        # Optionally run validation again on post-edited version
                        if verbose:
                            print("\nConsider running validation again on the post-edited version to verify improvements.")
        elif post_edit and not with_validation:
            print("\n⚠️  Warning: Post-edit requires validation to be run first.")
            print("Please use --with-validation along with --post-edit")
    
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
  
  # Translate with full validation
  %(prog)s novel.txt --with-validation
  
  # Translate with quick validation on 30% of segments
  %(prog)s novel.txt --with-validation --quick-validation --validation-sample-rate 0.3
  
  # Translate with validation and post-edit to fix issues
  %(prog)s novel.txt --with-validation --post-edit
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
    parser.add_argument('--with-validation', action='store_true',
                        help='Run validation after translation to check quality')
    parser.add_argument('--validation-sample-rate', type=float, default=1.0,
                        help='Percentage of segments to validate (0.0-1.0, default: 1.0 for all segments)')
    parser.add_argument('--quick-validation', action='store_true',
                        help='Use quick validation mode (faster but less thorough)')
    parser.add_argument('--post-edit', action='store_true',
                        help='Apply AI-powered post-editing to fix validation issues (requires --with-validation)')
    
    args = parser.parse_args()
    
    # Validate sample rate
    if args.validation_sample_rate < 0.0 or args.validation_sample_rate > 1.0:
        parser.error("--validation-sample-rate must be between 0.0 and 1.0")
    
    # Run translation
    translate(
        source_file=args.source,
        target_file=args.target,
        api_key=args.api_key,
        segment_size=args.segment_size,
        verbose=args.verbose,
        with_validation=args.with_validation,
        validation_sample_rate=args.validation_sample_rate,
        quick_validation=args.quick_validation,
        post_edit=args.post_edit
    )


if __name__ == '__main__':
    main()