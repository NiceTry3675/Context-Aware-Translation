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
    def setup_job_output_path(job_id: int, original_filename: Optional[str], 
                             input_format: str) -> str:
        """
        Setup job-specific output file path in logs/jobs/{job_id}/output/.
        
        Args:
            job_id: Job ID for the translation
            original_filename: Original filename
            input_format: Input file format
            
        Returns:
            Full path to job-specific output file
        """
        # Determine base filename
        if original_filename:
            base_name = os.path.splitext(original_filename)[0]
        else:
            base_name = f"job_{job_id}"
        
        # Setup output directory
        output_dir = os.path.join("logs", "jobs", str(job_id), "output")
        
        # Determine output filename based on format
        if input_format == '.epub':
            output_filename = os.path.join(output_dir, f"{base_name}_translated.epub")
        else:
            output_filename = os.path.join(output_dir, f"{base_name}_translated.txt")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
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
    def save_to_storage_sync(segments: List[str], job_id: int, original_filename: str,
                            storage_handler=None):
        """
        Save translation using storage abstraction (synchronous wrapper).
        
        Args:
            segments: List of translated text segments
            job_id: Job ID
            original_filename: Original filename
            storage_handler: Optional storage handler injected from backend
            
        Returns:
            List of saved paths, or None if backend not available
        """
        # If no handler provided, just return None (core-only mode)
        if storage_handler is None:
            return None
            
        try:
            # Use the injected storage handler
            content = '\n\n'.join(segments)
            saved_paths = storage_handler(
                job_id=job_id,
                content=content,
                original_filename=original_filename
            )
            print(f"✓ Saved to storage: {saved_paths}")
            return saved_paths
        except Exception as e:
            print(f"Warning: Failed to save to storage: {e}")
            return None
    
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