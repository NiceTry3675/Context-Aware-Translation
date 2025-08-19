"""
Text Segmentation Utilities

This module provides centralized text segmentation functionality to eliminate code duplication
across the translation engine. It handles intelligent text splitting that preserves sentence
boundaries and maintains readability for AI translation models.
"""

import re
from typing import List
from ..schemas import SegmentInfo
from .file_parser import parse_document


def create_segments_for_text(filepath: str, target_size: int = 15000) -> List[SegmentInfo]:
    """
    Create segments from a text file.
    
    Args:
        filepath: Path to the text file
        target_size: Target character count for each segment
        
    Returns:
        List of SegmentInfo objects
    """
    print("Creating segments for text file...")
    full_text = parse_document(filepath)
    return create_segments_from_plain_text(full_text, target_size)


def create_segments_for_epub(filepath: str, target_size: int = 15000) -> List[SegmentInfo]:
    """
    Create segments from an EPUB file by flattening to text.
    
    Args:
        filepath: Path to the EPUB file
        target_size: Target character count for each segment
        
    Returns:
        List of SegmentInfo objects
    """
    print("Creating segments for EPUB by flattening to text...")
    # Use the existing text parser to get all text from the EPUB
    full_text = parse_document(filepath)
    
    # Use the same segmentation logic as for plain text files
    return create_segments_from_plain_text(full_text, target_size)


def create_segments_from_plain_text(text: str, target_size: int = 15000) -> List[SegmentInfo]:
    """
    Create segments from plain text with intelligent splitting.
    
    This function:
    - Preserves paragraph boundaries
    - Handles hard-wrapped text
    - Maintains sentence integrity
    - Creates segments close to target size
    
    Args:
        text: The full text to segment
        target_size: Target size for each segment in characters
        
    Returns:
        List of SegmentInfo objects
    """
    # Split by double newlines (paragraph boundaries)
    raw_paragraphs = re.split(r'\n\s*\n', text)
    
    # Process paragraphs to handle hard-wrapped text
    normalized_paragraphs = _normalize_paragraphs(raw_paragraphs)
    
    # Create segments from normalized paragraphs
    segments = _build_segments(normalized_paragraphs, target_size)
    
    print(f"Text divided into {len(segments)} segments.")
    
    # Debug: Show preview of first few segments
    _preview_segments(segments)
    
    return segments


def _normalize_paragraphs(raw_paragraphs: List[str]) -> List[str]:
    """
    Normalize paragraphs by handling hard-wrapped lines.
    
    This function processes each paragraph to combine hard-wrapped lines
    that belong to the same sentence while preserving intentional line breaks.
    
    Args:
        raw_paragraphs: List of raw paragraph strings
        
    Returns:
        List of normalized paragraph strings
    """
    normalized_paragraphs = []
    
    for para in raw_paragraphs:
        if not para.strip():
            continue
        
        # Process lines within paragraph
        lines = para.strip().split('\n')
        processed_lines = []
        current_sentence = ""
        
        for line in lines:
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
    
    return normalized_paragraphs


def _build_segments(paragraphs: List[str], target_size: int) -> List[SegmentInfo]:
    """
    Build segments from normalized paragraphs.
    
    Args:
        paragraphs: List of normalized paragraphs
        target_size: Target size for each segment
        
    Returns:
        List of SegmentInfo objects
    """
    segments = []
    current_segment_text = ""
    
    for para in paragraphs:
        # If adding this paragraph would exceed target size
        if len(current_segment_text) + len(para) > target_size and current_segment_text:
            # Save current segment and start new one
            segments.append(SegmentInfo(text=current_segment_text.strip()))
            current_segment_text = ""
        
        # If paragraph itself is larger than target size, split by sentences
        if len(para) > target_size:
            _split_large_paragraph(para, target_size, segments, current_segment_text)
            current_segment_text = ""
        else:
            # Add the whole paragraph
            current_segment_text += para + "\n\n"
    
    # Add any remaining text as final segment
    if current_segment_text.strip():
        segments.append(SegmentInfo(text=current_segment_text.strip()))
    
    return segments


def _split_large_paragraph(para: str, target_size: int, 
                          segments: List[SegmentInfo], current_segment_text: str):
    """
    Split a large paragraph by sentences.
    
    Args:
        para: The paragraph to split
        target_size: Target size for each segment
        segments: List to append segments to
        current_segment_text: Current accumulated text
    """
    # The paragraph already has sentence boundaries preserved as newlines
    sentences = para.split('\n')
    local_segment_text = current_segment_text
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if len(local_segment_text) + len(sentence) > target_size and local_segment_text:
            segments.append(SegmentInfo(text=local_segment_text.strip()))
            local_segment_text = ""
        
        local_segment_text += sentence + "\n"
    
    # Add remaining text with paragraph break
    if local_segment_text.strip():
        segments.append(SegmentInfo(text=local_segment_text.strip()))


def _preview_segments(segments: List[SegmentInfo], count: int = 3):
    """
    Show preview of first few segments for debugging.
    
    Args:
        segments: List of segments to preview
        count: Number of segments to show
    """
    for i, seg in enumerate(segments[:count]):
        preview = seg.text[:100].replace('\n', ' ')
        if len(seg.text) > 100:
            preview += "..."
        print(f"  Segment {i+1}: {preview}")


def get_segment_statistics(segments: List[SegmentInfo]) -> dict:
    """
    Get statistics about the segments.
    
    Args:
        segments: List of segments to analyze
        
    Returns:
        Dictionary with segment statistics
    """
    if not segments:
        return {"count": 0, "avg_length": 0, "min_length": 0, "max_length": 0}
    
    lengths = [len(seg.text) for seg in segments]
    
    return {
        "count": len(segments),
        "avg_length": sum(lengths) // len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "total_chars": sum(lengths)
    }