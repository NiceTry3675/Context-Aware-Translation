"""
Translation Document Module

This module handles document I/O, segmentation, and translation storage.
It manages the source document parsing, segment creation, and output generation.
"""

import os
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Optional
from ..utils.file_parser import parse_document


class SegmentInfo:
    """Container for segment data and its context."""
    def __init__(self, text: str, chapter_title: Optional[str] = None, 
                 chapter_filename: Optional[str] = None):
        self.text = text
        self.chapter_title = chapter_title
        self.chapter_filename = chapter_filename


class TranslationDocument:
    """
    Manages a document through the translation process.
    
    This class handles:
    - Document parsing and segmentation
    - Translation storage and retrieval
    - Output file generation in various formats
    - Glossary and style management
    """
    
    def __init__(self, filepath: str, original_filename: Optional[str] = None, 
                 target_segment_size: int = 15000):
        """
        Initialize a translation document.
        
        Args:
            filepath: Path to the source document
            original_filename: Original filename for user-facing display
            target_segment_size: Target size for each segment in characters
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file '{filepath}' does not exist.")
        
        self.filepath = filepath  # Unique path, e.g., "uploads/123_MyBook.txt"
        
        # Determine filenames
        self._setup_filenames(original_filename)
        
        # Determine input format
        self.input_format = os.path.splitext(self.user_base_filename.lower())[1] \
                           if original_filename else os.path.splitext(filepath.lower())[1]
        
        # Initialize data structures
        self.segments: List[SegmentInfo] = []
        self.translated_segments: List[str] = []
        self.glossary: dict = {}
        self.character_styles: dict = {}
        self.style_map: dict = {}  # For EPUB styles
        
        # Setup output path and create segments
        self._setup_output_path()
        self._create_segments(target_segment_size)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.output_filename), exist_ok=True)
    
    def _setup_filenames(self, original_filename: Optional[str]):
        """Setup user-facing and unique filenames."""
        # User-facing filename (e.g., "MyBook")
        user_facing_filename = original_filename if original_filename else os.path.basename(self.filepath)
        self.user_base_filename = os.path.splitext(user_facing_filename)[0]
        
        # Unique base filename for saving (e.g., "123_MyBook")
        self.unique_base_filename = os.path.splitext(os.path.basename(self.filepath))[0]
    
    def _setup_output_path(self):
        """Setup the output file path based on format."""
        if self.input_format == '.epub':
            self.original_book = epub.read_epub(self.filepath)
            self.output_filename = os.path.join('translated_novel', 
                                               f"{self.unique_base_filename}_translated.epub")
        else:
            self.output_filename = os.path.join('translated_novel', 
                                               f"{self.unique_base_filename}_translated.txt")
    
    def _create_segments(self, target_size: int):
        """Create segments from the document."""
        if self.input_format == '.epub':
            self.segments = self._create_segments_for_epub(target_size)
        else:
            self.segments = self._create_segments_for_text(target_size)
    
    def _create_segments_for_epub(self, target_size: int) -> List[SegmentInfo]:
        """
        Creates size-aware segments from EPUB content.
        
        Args:
            target_size: Target size for each segment
            
        Returns:
            List of SegmentInfo objects
        """
        print("Creating segments for EPUB by flattening to text...")
        # Use the existing text parser to get all text from the EPUB
        full_text = parse_document(self.filepath)
        
        # Use the same segmentation logic as for plain text files
        return self._create_segments_from_plain_text(full_text, target_size)
    
    def _create_segments_for_text(self, target_size: int) -> List[SegmentInfo]:
        """
        Creates size-aware segments from a text file.
        
        Args:
            target_size: Target size for each segment
            
        Returns:
            List of SegmentInfo objects
        """
        print("Creating segments for text file...")
        full_text = parse_document(self.filepath)
        return self._create_segments_from_plain_text(full_text, target_size)
    
    def _create_segments_from_plain_text(self, text: str, target_size: int) -> List[SegmentInfo]:
        """
        Helper function to segment text with sentence-aware splitting.
        
        This method:
        - Preserves paragraph boundaries
        - Handles hard-wrapped text
        - Maintains sentence integrity
        - Creates segments close to target size
        
        Args:
            text: The full text to segment
            target_size: Target size for each segment
            
        Returns:
            List of SegmentInfo objects
        """
        # Split by double newlines (paragraph boundaries)
        raw_paragraphs = re.split(r'\n\s*\n', text)
        
        # Process paragraphs to handle hard-wrapped text
        normalized_paragraphs = self._normalize_paragraphs(raw_paragraphs)
        
        # Create segments from normalized paragraphs
        segments = self._build_segments(normalized_paragraphs, target_size)
        
        print(f"Text divided into {len(segments)} segments.")
        
        # Debug: Show preview of first few segments
        self._preview_segments(segments)
        
        return segments
    
    def _normalize_paragraphs(self, raw_paragraphs: List[str]) -> List[str]:
        """
        Normalize paragraphs by handling hard-wrapped lines.
        
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
                    # Check if previous text ends with sentence terminator
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
            
            # Join sentences with newlines to preserve boundaries
            normalized_para = "\n".join(processed_lines)
            normalized_paragraphs.append(normalized_para)
        
        return normalized_paragraphs
    
    def _build_segments(self, paragraphs: List[str], target_size: int) -> List[SegmentInfo]:
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
                segments.append(SegmentInfo(current_segment_text.strip()))
                current_segment_text = ""
            
            # If paragraph itself is larger than target size, split by sentences
            if len(para) > target_size:
                self._split_large_paragraph(para, target_size, segments, current_segment_text)
                current_segment_text = ""
            else:
                # Add the whole paragraph
                current_segment_text += para + "\n\n"
        
        # Add any remaining text as final segment
        if current_segment_text.strip():
            segments.append(SegmentInfo(current_segment_text.strip()))
        
        return segments
    
    def _split_large_paragraph(self, para: str, target_size: int, 
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
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_segment_text) + len(sentence) > target_size and current_segment_text:
                segments.append(SegmentInfo(current_segment_text.strip()))
                current_segment_text = ""
            
            current_segment_text += sentence + "\n"
        
        # Add remaining text with paragraph break
        if current_segment_text:
            segments.append(SegmentInfo(current_segment_text.strip()))
    
    def _preview_segments(self, segments: List[SegmentInfo], count: int = 3):
        """Show preview of first few segments for debugging."""
        for i, seg in enumerate(segments[:count]):
            preview = seg.text[:100].replace('\n', ' ')
            if len(seg.text) > 100:
                preview += "..."
            print(f"  Segment {i+1}: {preview}")
    
    def append_translated_segment(self, translated_text: str, original_segment: SegmentInfo):
        """
        Append a translated segment.
        
        Args:
            translated_text: The translated text
            original_segment: The original segment info (unused but kept for compatibility)
        """
        self.translated_segments.append(translated_text)
    
    def get_previous_segment(self, current_index: int) -> str:
        """
        Get the text of the previous segment.
        
        Args:
            current_index: Current segment index
            
        Returns:
            Previous segment text or empty string
        """
        return self.segments[current_index - 1].text if current_index > 0 else ""
    
    def get_previous_translation(self, current_index: int) -> str:
        """
        Get the translation of the previous segment.
        
        Args:
            current_index: Current segment index
            
        Returns:
            Previous translation or empty string
        """
        return self.translated_segments[current_index - 1] if current_index > 0 else ""
    
    def save_partial_output(self):
        """Save the currently translated segments to the output file."""
        if self.input_format == '.epub':
            self._save_as_epub()
        else:
            self._save_as_text()
    
    def save_final_output(self):
        """Save the final output based on the input file format."""
        print(f"\nSaving final output to {self.output_filename}...")
        if self.input_format == '.epub':
            self._save_as_epub()
        else:
            self._save_as_text()
        print("Save complete.")
    
    def save_translation(self, output_path: Optional[str] = None):
        """
        Save the translation to a specified path or default output filename.
        
        Args:
            output_path: Optional custom output path
        """
        if output_path:
            # Temporarily change the output filename for saving
            original_output = self.output_filename
            self.output_filename = output_path
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save based on format
            if self.input_format == '.epub' and output_path.endswith('.epub'):
                self._save_as_epub()
            else:
                # Default to text format for post-edited versions
                self._save_as_text()
            
            # Restore original output filename
            self.output_filename = original_output
        else:
            self.save_final_output()
    
    def _save_as_text(self):
        """Save the translated segments as a single text file."""
        with open(self.output_filename, 'w', encoding='utf-8') as f:
            full_text = "\n".join(self.translated_segments)
            f.write(full_text)
    
    def _save_as_epub(self):
        """Save the translated content as a simple EPUB file."""
        translated_book = epub.EpubBook()
        
        # Set metadata
        self._set_epub_metadata(translated_book)
        
        # Add cover if available
        self._add_epub_cover(translated_book)
        
        # Create content
        main_chapter = self._create_epub_chapter()
        translated_book.add_item(main_chapter)
        
        # Setup TOC and spine
        translated_book.toc = [main_chapter]
        translated_book.spine = ['nav', main_chapter]
        translated_book.add_item(epub.EpubNcx())
        translated_book.add_item(epub.EpubNav())
        
        # Write the EPUB file
        epub.write_epub(self.output_filename, translated_book, {})
    
    def _set_epub_metadata(self, book: epub.EpubBook):
        """Set metadata for the EPUB book."""
        try:
            title = self.original_book.get_metadata('DC', 'title')[0][0]
            book.set_title(f"[KOR] {title}")
        except (IndexError, KeyError, AttributeError):
            book.set_title(f"[KOR] {self.user_base_filename}")
        
        book.set_language('ko')
        
        # Add authors if available
        if hasattr(self, 'original_book'):
            for author in self.original_book.get_metadata('DC', 'creator'):
                book.add_author(author[0])
    
    def _add_epub_cover(self, book: epub.EpubBook):
        """Add cover image to EPUB if available."""
        if not hasattr(self, 'original_book'):
            return
        
        cover_image_item = None
        for item in self.original_book.get_items_of_type(ebooklib.ITEM_IMAGE):
            if 'cover' in item.get_name().lower():
                cover_image_item = item
                break
        
        if cover_image_item:
            book.set_cover(cover_image_item.file_name, cover_image_item.content)
    
    def _create_epub_chapter(self) -> epub.EpubHtml:
        """Create the main chapter with translated content."""
        # Combine all translated text
        full_translated_text = "".join(self.translated_segments)
        
        # Create chapter
        main_chapter = epub.EpubHtml(
            title='Translated Content',
            file_name='chap_1.xhtml',
            lang='ko'
        )
        
        # Build HTML body
        html_body = ""
        for para in full_translated_text.split('\n'):
            if para.strip():
                html_body += f"<p>{para.strip()}</p>"
        
        main_chapter.content = (
            f'<html><head><title>Translation</title></head>'
            f'<body>{html_body}</body></html>'
        )
        
        return main_chapter