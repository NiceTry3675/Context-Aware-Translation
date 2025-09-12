"""
Style Analyzer Module

This module provides style analysis functionality for the translation engine,
including narrative style detection and style formatting.
"""

import re
from typing import Dict, Any, List, Union, Optional
from ..prompts.manager import PromptManager
from ..translation.models.gemini import GeminiModel
from ..translation.models.openrouter import OpenRouterModel
from shared.errors import ProhibitedException, TranslationError
from shared.errors.error_logger import ProhibitedContentLogger
from ..utils.file_parser import parse_document
from ..utils.text_segmentation import create_segments_from_plain_text
from shared.utils.logging import TranslationLogger




class StyleAnalyzer:
    """
    Analyzes and extracts style information from source documents.
    
    This class encapsulates all style-related analysis functionality,
    including narrative style detection, glossary extraction, and formatting.
    """
    
    def __init__(self, model_api: Union[GeminiModel, OpenRouterModel], job_id: Optional[int] = None):
        """
        Initialize the StyleAnalyzer.
        
        Args:
            model_api: The AI model API instance for analysis
            job_id: Optional job ID for logging
        """
        self.model_api = model_api
        self.job_id = job_id
        self.logger = None
    
    def extract_sample_text(self, filepath: str, method: str = "first_segment", count: int = 15000) -> str:
        """
        Extracts a sample text for analysis based on the specified method.

        Args:
            filepath: Path to the file to parse and sample from
            method: Sampling method
                - "first_segment": Use segmentation logic to build the first segment up to count chars
                - "first_chars":   Simply take the first `count` characters from the parsed document
            count: Target size (default 15000 characters)

        Returns:
            Sample text for analysis
        """
        # Parse document using centralized file parser
        text = parse_document(filepath)
        
        if method == "first_chars":
            return text[:count]
        
        if method == "first_segment":
            segments = create_segments_from_plain_text(text, count)
            return segments[0].text if segments else text[:count]
        
        # Fallback to simple character-based extraction
        return text[:count]




    def analyze_narrative_style(self, sample_text: str, job_filename: str = "unknown") -> str:
        """
        Analyzes the narrative style using the AI model.
        
        Args:
            sample_text: Text sample to analyze
            job_filename: Name of the file being processed (for logging)
            
        Returns:
            Style analysis text from the AI
        """
        # Initialize logger if not already done
        if not self.logger:
            self.logger = TranslationLogger(self.job_id, job_filename, task_type="style_analysis")
            self.logger.initialize_session()
        
        # Initialize prohibited content logger for this job
        prohibited_logger = ProhibitedContentLogger(job_id=self.job_id)
        
        prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=sample_text)
        
        # Log the style analysis prompt
        if self.logger:
            self.logger.log_translation_prompt(0, f"[STYLE ANALYSIS PROMPT]\n{prompt}")
        
        try:
            style = self.model_api.generate_text(prompt)
            
            # Log successful style analysis
            if self.logger and self.logger.context_log_path:
                with open(self.logger.context_log_path, 'a', encoding='utf-8') as f:
                    f.write(f"--- NARRATIVE STYLE ANALYSIS ---\n")
                    f.write(f"Sample text length: {len(sample_text)} chars\n")
                    f.write(f"Style analysis result:\n{style}\n\n")
            
            return style
        except ProhibitedException as e:
            log_path = prohibited_logger.log_simple_prohibited_content(
                api_call_type="core_style_definition",
                prompt=prompt,
                source_text=sample_text,
                error_message=str(e),
                job_filename=job_filename
            )
            print(f"Warning: Core style definition blocked. Log: {log_path}. Falling back to default.")
            return "A standard, neutral literary style ('평서체')."
        except Exception as e:
            print(f"Warning: Could not define narrative style. Error: {e}")
            
            # Log error
            if self.logger:
                self.logger.log_error(e, context="analyze_narrative_style")
            
            # Re-raise with the specific error message from the underlying API call
            raise Exception(f"Failed to define core style: {e}") from e


    def parse_style_analysis(self, style_text: str) -> Dict[str, str]:
        """
        Parses the style analysis text into structured data.
        
        Args:
            style_text: The raw style analysis text from AI
            
        Returns:
            Dictionary with structured style data
        """
        parsed_style = {}
        
        # Log parsing attempt
        if self.logger and self.logger.context_log_path:
            with open(self.logger.context_log_path, 'a', encoding='utf-8') as f:
                f.write(f"--- PARSING STYLE ANALYSIS ---\n")
                f.write(f"Input text length: {len(style_text)} chars\n")
        
        key_mapping = {
            "Protagonist Name": "protagonist_name",
            "Protagonist Name (주인공 이름)": "protagonist_name",
            "Narration Style & Endings (서술 문체 및 어미)": "narration_style_endings",
            "Narration Style & Endings": "narration_style_endings",
            "Core Tone & Keywords (전체 분위기)": "tone_keywords",
            "Core Tone & Keywords": "tone_keywords",
            "Key Stylistic Rule (The \"Golden Rule\")": "stylistic_rule",
            "Key Stylistic Rule": "stylistic_rule",
        }

        for key_pattern, json_key in key_mapping.items():
            pattern = re.escape(key_pattern) + r":\s*(.*?)(?=\s*\d\.\s*|$)"
            match = re.search(pattern, style_text, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip().replace('**', '')
                parsed_style[json_key] = value
        
        # Log parsed results
        if self.logger and self.logger.context_log_path:
            with open(self.logger.context_log_path, 'a', encoding='utf-8') as f:
                f.write(f"Parsed style components:\n")
                for key, value in parsed_style.items():
                    f.write(f"  {key}: {value[:100]}...\n" if len(value) > 100 else f"  {key}: {value}\n")
                f.write("\n")
        
        return parsed_style


    def format_style_for_engine(self, style_data: Dict[str, str], protagonist_name: str = "protagonist") -> str:
        """
        Formats structured style data into the text format expected by the translation engine.
        
        Args:
            style_data: Dictionary with style information
            protagonist_name: Name of the protagonist
            
        Returns:
            Formatted style text for the translation engine
        """
        protagonist_name = style_data.get('protagonist_name', protagonist_name)
        style_parts = [
            f"1. **Protagonist Name:** {protagonist_name}",
            f"2. **Narration Style & Endings (서술 문체 및 어미):** {style_data.get('narration_style_endings', 'Not specified')}",
            f"3. **Core Tone & Keywords (전체 분위기):** {style_data.get('tone_keywords', 'Not specified')}",
            f"4. **Key Stylistic Rule (The \"Golden Rule\"):** {style_data.get('stylistic_rule', 'Not specified')}"
        ]
        return "\n".join(style_parts)

    
    def define_core_style(self, file_path: str, job_base_filename: str = "unknown") -> str:
        """
        Analyzes the first segment to define the core narrative style for the novel.
        
        Args:
            file_path: Path to the source file
            job_base_filename: Base filename for logging
            
        Returns:
            Core style description text
        """
        print("\n--- Defining Core Narrative Style... ---")
        
        # Initialize logger if not already done
        if not self.logger:
            self.logger = TranslationLogger(self.job_id, job_base_filename, task_type="style_analysis")
            self.logger.initialize_session()
        
        # Log core style definition start
        if self.logger and self.logger.context_log_path:
            with open(self.logger.context_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"CORE STYLE DEFINITION SESSION\n")
                f.write(f"File: {file_path}\n")
                f.write(f"Base filename: {job_base_filename}\n")
                f.write(f"{'='*60}\n\n")
        
        # Extract sample text using simplified method
        sample_text = self.extract_sample_text(file_path, method="first_chars", count=15000)
        try:
            style = self.analyze_narrative_style(sample_text, job_base_filename)
            print(f"Style defined as: {style}")
            
            # Log successful style definition
            if self.logger:
                self.logger.log_core_narrative_style(style)
            
            return style
        except Exception as e:
            print(f"Warning: Could not define narrative style. Falling back to default. Error: {e}")
            
            # Log error
            if self.logger:
                self.logger.log_error(e, context="define_core_style")
            
            raise TranslationError(f"Failed to define core style: {e}") from e


