"""
Document I/O Utilities

This module provides centralized file I/O operations to eliminate code duplication
across the translation engine. It handles document parsing, output generation,
and file management operations.
"""

import os
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Optional, Union
from pathlib import Path

from .file_parser import parse_document
from ..schemas import SegmentInfo, TranslationDocumentData


class DocumentOutputManager:
    """
    Centralized manager for document output operations.
    
    This class handles all file output operations including:
    - Text file generation
    - EPUB file generation  
    - Output path management
    - Directory creation
    """
    
    @staticmethod
    def setup_output_path(input_filepath: str, original_filename: Optional[str] = None, 
                         output_dir: str = "translated_novel") -> str:
        """
        Setup output file path based on input file format.
        
        Args:
            input_filepath: Path to input file
            original_filename: Original filename for user-facing display
            output_dir: Output directory for translated files
            
        Returns:
            Full path to output file
        """
        # Determine the unique base filename for saving files
        unique_base_filename = os.path.splitext(os.path.basename(input_filepath))[0]
        
        # Determine format from original filename if provided, else from input filepath
        filename_for_format = original_filename if original_filename else os.path.basename(input_filepath)
        input_format = os.path.splitext(filename_for_format.lower())[1]
        
        if input_format == '.epub':
            output_filename = os.path.join(output_dir, f"{unique_base_filename}_translated.epub")
        else:
            output_filename = os.path.join(output_dir, f"{unique_base_filename}_translated.txt")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
        return output_filename
    
    @staticmethod
    def save_text_output(segments: List[str], output_path: str):
        """
        Save translated segments as a text file.
        
        Args:
            segments: List of translated text segments
            output_path: Path to save the output file
        """
        print(f"Saving text output to {output_path}...")
        
        # Join all translated segments
        full_text = "\n\n".join(segments)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        print(f"✓ Text saved to {output_path}")
    
    @staticmethod
    def save_epub_output(original_filepath: str, segments: List[str], 
                        output_path: str, style_map: Optional[dict] = None):
        """
        Save translated segments as an EPUB file.
        
        Args:
            original_filepath: Path to original EPUB file
            segments: List of translated text segments
            output_path: Path to save the output file
            style_map: Optional style mapping for formatting
        """
        print(f"Saving EPUB output to {output_path}...")
        
        try:
            # Read the original book to preserve structure
            original_book = epub.read_epub(original_filepath)
            translated_book = epub.EpubBook()
            
            # Copy basic metadata
            translated_book.set_identifier(original_book.get_metadata('DC', 'identifier')[0][0] if original_book.get_metadata('DC', 'identifier') else 'translated_book')
            translated_book.set_title(f"[TRANSLATED] {original_book.get_metadata('DC', 'title')[0][0] if original_book.get_metadata('DC', 'title') else 'Untitled'}")
            translated_book.set_language('ko')  # Korean translation
            
            # Add author information
            if original_book.get_metadata('DC', 'creator'):
                original_author = original_book.get_metadata('DC', 'creator')[0][0]
                translated_book.add_author(f"{original_author} (Translated)")
            
            # Join all segments for the content
            full_translated_text = "\n\n".join(segments)
            
            # Create a single chapter with all translated content
            chapter = epub.EpubHtml(title='Translated Content',
                                  file_name='translated_content.xhtml',
                                  lang='ko')
            
            # Convert plain text to HTML with proper paragraph formatting
            html_content = _convert_text_to_html(full_translated_text)
            chapter.content = html_content
            
            # Add chapter to book
            translated_book.add_item(chapter)
            
            # Copy navigation structure or create simple one
            translated_book.toc = (epub.Link("translated_content.xhtml", "Translated Content", "content"),)
            translated_book.add_item(epub.EpubNcx())
            translated_book.add_item(epub.EpubNav())
            
            # Define spine
            translated_book.spine = ['nav', chapter]
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write the EPUB file
            epub.write_epub(output_path, translated_book, {})
            print(f"✓ EPUB saved to {output_path}")
            
        except Exception as e:
            print(f"Error saving EPUB: {e}")
            # Fallback to text output if EPUB fails
            fallback_path = output_path.replace('.epub', '_fallback.txt')
            DocumentOutputManager.save_text_output(segments, fallback_path)
            raise
    
    @staticmethod
    def save_translation_output(segments: List[str], output_path: str, 
                              original_filepath: Optional[str] = None,
                              style_map: Optional[dict] = None):
        """
        Save translation output in the appropriate format.
        
        Args:
            segments: List of translated text segments
            output_path: Path to save the output file
            original_filepath: Path to original file (for EPUB processing)
            style_map: Optional style mapping for formatting
        """
        file_extension = os.path.splitext(output_path.lower())[1]
        
        if file_extension == '.epub':
            if not original_filepath:
                raise ValueError("Original filepath required for EPUB output")
            DocumentOutputManager.save_epub_output(original_filepath, segments, output_path, style_map)
        else:
            DocumentOutputManager.save_text_output(segments, output_path)


class DebugLogger:
    """
    Centralized debug logging utilities for translation operations.
    """
    
    @staticmethod
    def setup_debug_directories():
        """Create debug logging directories if they don't exist."""
        debug_dirs = [
            'logs/debug_prompts',
            'logs/context_log',
            'logs/validation_logs',
            'logs/postedit_logs',
            'logs/prohibited_content_logs'
        ]
        
        for dir_path in debug_dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    @staticmethod
    def log_prompts_and_context(filename: str, core_narrative_style: str,
                               prompts: List[tuple], contexts: List[dict]):
        """
        Log prompts and context information for debugging.
        
        Args:
            filename: Name of the file being processed
            core_narrative_style: Core narrative style definition
            prompts: List of (segment_index, prompt) tuples
            contexts: List of context dictionaries
        """
        DebugLogger.setup_debug_directories()
        
        prompt_log_path = f"logs/debug_prompts/{filename}_prompts.txt"
        context_log_path = f"logs/context_log/{filename}_context.txt"
        
        # Write prompt log
        with open(prompt_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# PROMPT LOG FOR: {filename}\n\n")
            
            for segment_index, prompt in prompts:
                f.write(f"--- PROMPT FOR SEGMENT {segment_index} ---\n\n")
                f.write(prompt)
                f.write("\n\n" + "="*50 + "\n\n")
        
        # Write context log
        with open(context_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# CONTEXT LOG FOR: {filename}\n\n")
            f.write(f"--- Core Narrative Style Defined ---\n")
            f.write(f"{core_narrative_style}\n")
            f.write("="*50 + "\n\n")
            
            for context in contexts:
                segment_index = context.get('segment_index', 'unknown')
                f.write(f"--- CONTEXT FOR SEGMENT {segment_index} ---\n\n")
                
                # Style deviation
                style_deviation = context.get('style_deviation', 'N/A')
                f.write(f"### Narrative Style Deviation:\n{style_deviation}\n\n")
                
                # Contextual glossary
                contextual_glossary = context.get('contextual_glossary', {})
                f.write("### Contextual Glossary (For This Segment):\n")
                if contextual_glossary:
                    for key, value in contextual_glossary.items():
                        f.write(f"- {key}: {value}\n")
                else:
                    f.write("- None relevant to this segment.\n")
                f.write("\n")
                
                # Full glossary
                full_glossary = context.get('full_glossary', {})
                f.write("### Cumulative Glossary (Full):\n")
                if full_glossary:
                    for key, value in full_glossary.items():
                        f.write(f"- {key}: {value}\n")
                else:
                    f.write("- Empty\n")
                f.write("\n")
                
                # Character styles
                character_styles = context.get('character_styles', {})
                f.write("### Cumulative Character Styles:\n")
                if character_styles:
                    for key, value in character_styles.items():
                        f.write(f"- {key}: {value}\n")
                else:
                    f.write("- Empty\n")
                f.write("\n")
                
                # Immediate context
                immediate_context_source = context.get('immediate_context_source')
                immediate_context_ko = context.get('immediate_context_ko')
                f.write("### Immediate language Context (Previous Segment Ending):\n")
                f.write(f"{immediate_context_source or 'N/A'}\n\n")
                f.write("### Immediate Korean Context (Previous Segment Ending):\n")
                f.write(f"{immediate_context_ko or 'N/A'}\n\n")
                f.write("="*50 + "\n\n")


def _convert_text_to_html(text: str) -> str:
    """
    Convert plain text to HTML with proper paragraph formatting.
    
    Args:
        text: Plain text to convert
        
    Returns:
        HTML formatted text
    """
    # Split by double newlines to get paragraphs
    paragraphs = text.split('\n\n')
    
    html_parts = ['<html xmlns="http://www.w3.org/1999/xhtml">',
                  '<head><title>Translated Content</title></head>',
                  '<body>']
    
    for para in paragraphs:
        if para.strip():
            # Replace single newlines with <br/> tags within paragraphs
            para_html = para.replace('\n', '<br/>')
            html_parts.append(f'<p>{para_html}</p>')
    
    html_parts.extend(['</body>', '</html>'])
    
    return '\n'.join(html_parts)