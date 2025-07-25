import re
from typing import Dict, Any, List
from ..prompts.manager import PromptManager
from ..translation.models.gemini import GeminiModel
from ..translation.models.openrouter import OpenRouterModel
from ..errors import ProhibitedException
from ..errors.error_logger import prohibited_content_logger
from .job import SegmentInfo


def _create_segments_from_plain_text(text: str, target_size: int) -> List[SegmentInfo]:
    """Helper function to segment a block of text with sentence-aware splitting.
    This is a copy of the same function from job.py to avoid circular dependencies."""
    # Split by double newlines (actual paragraph boundaries)
    raw_paragraphs = re.split(r'\n\s*\n', text)
    
    # Process paragraphs to handle hard-wrapped text properly
    normalized_paragraphs = []
    for para in raw_paragraphs:
        if not para.strip():
            continue
        
        # Process lines within paragraph
        lines = para.strip().split('\n')
        processed_lines = []
        current_sentence = ""
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            if current_sentence:
                # Check if previous accumulated text ends with sentence terminator
                if re.search(r'[.!?]["\']*$', current_sentence):
                    # Previous sentence is complete
                    processed_lines.append(current_sentence)
                    current_sentence = line
                else:
                    # Continue accumulating (hard-wrapped line)
                    current_sentence += " " + line
            else:
                current_sentence = line
        
        # Add final sentence
        if current_sentence:
            processed_lines.append(current_sentence)
        
        # Join sentences with newlines to preserve sentence boundaries
        normalized_para = "\n".join(processed_lines)
        normalized_paragraphs.append(normalized_para)
    
    segments = []
    current_segment_text = ""
    
    for para in normalized_paragraphs:
        # If adding this paragraph would exceed target size
        if len(current_segment_text) + len(para) > target_size and current_segment_text:
            # Save current segment and start new one
            segments.append(SegmentInfo(current_segment_text.strip()))
            current_segment_text = ""
        
        # If the paragraph itself is larger than target size, split by sentences
        if len(para) > target_size:
            # The paragraph already has sentence boundaries preserved as newlines
            sentences = para.split('\n')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(current_segment_text) + len(sentence) > target_size and current_segment_text:
                    segments.append(SegmentInfo(current_segment_text.strip()))
                    current_segment_text = ""
                current_segment_text += sentence + "\n"
            current_segment_text = current_segment_text.strip() + "\n\n"
        else:
            # Add the whole paragraph
            current_segment_text += para + "\n\n"
    
    if current_segment_text.strip():
        segments.append(SegmentInfo(current_segment_text.strip()))
        
    return segments


def extract_sample_text(text: str, method: str = "first_segment", count: int = 15000) -> str:
    """
    Extracts a sample text for style analysis based on the specified method.
    
    Args:
        text: The full text to sample from
        method: Sampling method - "first_segment" to use the actual segmentation logic
        count: Target segment size (default 15000 characters)
        
    Returns:
        Sample text for analysis (first segment according to segmentation logic)
    """
    if method == "first_segment":
        # Use the actual segmentation logic to get the first segment
        segments = _create_segments_from_plain_text(text, count)
        return segments[0].text if segments else text[:count]
    else:
        # Fallback to simple character-based extraction
        return text[:count]


def analyze_narrative_style_with_api(
    sample_text: str,
    model_api: GeminiModel | OpenRouterModel,
    job_filename: str = "unknown"
) -> str:
    """
    Analyzes the narrative style using the AI model.
    
    Args:
        sample_text: Text sample to analyze
        model_api: The AI model API instance
        job_filename: Name of the file being processed (for logging)
        
    Returns:
        Style analysis text from the AI
    """
    prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=sample_text)
    
    try:
        style = model_api.generate_text(prompt)
        return style
    except ProhibitedException as e:
        log_path = prohibited_content_logger.log_simple_prohibited_content(
            api_call_type="core_style_definition",
            prompt=prompt,
            source_text=sample_text,
            error_message=str(e),
            job_filename=job_filename
        )
        print(f"Warning: Core style definition blocked. Log: {log_path}. Falling back to default.")
        return "A standard, neutral literary style ('평서체')."
    except Exception as e:
        print(f"Warning: Could not define narrative style. Falling back to default. Error: {e}")
        raise Exception(f"Failed to define core style: {e}") from e


def parse_style_analysis(style_text: str) -> Dict[str, str]:
    """
    Parses the style analysis text into structured data.
    
    Args:
        style_text: The raw style analysis text from AI
        
    Returns:
        Dictionary with structured style data
    """
    parsed_style = {}
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
            
    return parsed_style


def format_style_for_engine(style_data: Dict[str, str], protagonist_name: str = "protagonist") -> str:
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