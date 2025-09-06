"""
PDF Generator Service

This module provides functionality to generate PDF documents from translation jobs,
including translated text, source text (optional), and illustrations (if available).
"""

import os
import re
import fitz  # PyMuPDF
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json
from PIL import Image
from io import BytesIO
import logging

from backend.domains.translation.models import TranslationJob
from sqlalchemy.orm import Session


class PDFGenerator:
    """
    Handles PDF generation for translation jobs with optional illustrations.
    
    This class provides methods to:
    - Generate professional PDF documents from translation segments
    - Embed illustrations where available
    - Include source text alongside translations (optional)
    - Apply consistent formatting and styling
    """
    
    # PDF Configuration
    PAGE_WIDTH = 595  # A4 width in points
    PAGE_HEIGHT = 842  # A4 height in points
    MARGIN_TOP = 60
    MARGIN_BOTTOM = 60
    MARGIN_LEFT = 60
    MARGIN_RIGHT = 60
    
    # Font configuration
    NANUM_FONT_PATH = os.path.join(os.path.dirname(__file__), '..', 'NanumGothic-Regular.ttf')
    
    # Font sizes
    TITLE_FONT_SIZE = 24
    HEADING_FONT_SIZE = 18
    BODY_FONT_SIZE = 12  # Increased for better Korean text readability
    SOURCE_FONT_SIZE = 9
    CAPTION_FONT_SIZE = 8
    
    # Colors
    COLOR_BLACK = (0, 0, 0)
    COLOR_GRAY = (0.4, 0.4, 0.4)
    COLOR_LIGHT_GRAY = (0.7, 0.7, 0.7)
    COLOR_BLUE = (0, 0.2, 0.6)
    
    def __init__(self, job: TranslationJob, db: Session):
        """
        Initialize the PDF generator.
        
        Args:
            job: TranslationJob model instance
            db: Database session
        """
        self.job = job
        self.db = db
        self.doc = fitz.open()  # Create new PDF document
        self.current_page = None
        self.current_y = self.MARGIN_TOP
        self.page_number = 0
        
        # Load custom Korean font
        self.korean_font = None
        if os.path.exists(self.NANUM_FONT_PATH):
            try:
                # Load NanumGothic font from file
                with open(self.NANUM_FONT_PATH, 'rb') as f:
                    font_data = f.read()
                self.korean_font = fitz.Font(fontbuffer=font_data)
                logging.info(f"Successfully loaded NanumGothic font from {self.NANUM_FONT_PATH}")
            except Exception as e:
                logging.warning(f"Failed to load NanumGothic font: {e}. Using fallback CJK font.")
                self.korean_font = fitz.Font("CJK")  # Fallback to CJK
        else:
            logging.warning(f"NanumGothic font not found at {self.NANUM_FONT_PATH}. Using fallback CJK font.")
            self.korean_font = fitz.Font("CJK")  # Fallback to CJK
        
    def generate(self, 
                 include_source: bool = True,
                 include_illustrations: bool = True,
                 page_size: str = "A4") -> bytes:
        """
        Generate the complete PDF document.
        
        Args:
            include_source: Whether to include source text
            include_illustrations: Whether to include illustrations
            page_size: Page size (A4 or Letter)
            
        Returns:
            PDF document as bytes
        """
        # Set page dimensions based on size
        if page_size == "Letter":
            self.PAGE_WIDTH = 612
            self.PAGE_HEIGHT = 792
        
        # Add title page
        self._add_title_page()
        
        # Add translation content
        self._add_translation_content(include_source, include_illustrations)
        
        # Add metadata
        self._add_metadata()
        
        # Convert to bytes
        pdf_bytes = self.doc.write()
        self.doc.close()
        
        return pdf_bytes
    
    def _add_title_page(self):
        """Add a title page to the PDF."""
        page = self._new_page()
        
        # Center Y position for title
        y_center = self.PAGE_HEIGHT / 2
        
        # Title
        title = self.job.filename or "Translation Document"
        # Remove file extension for cleaner title
        if '.' in title:
            title = title.rsplit('.', 1)[0]
        
        # Sanitize title for PDF rendering
        title = self._sanitize_text_for_pdf(title)
        
        self._draw_text(
            page,
            title,
            self.PAGE_WIDTH / 2,
            y_center - 50,
            self.TITLE_FONT_SIZE,
            font="korean",  # Use Korean font
            align="center",
            color=self.COLOR_BLACK
        )
        
        # Subtitle
        self._draw_text(
            page,
            "Literary Translation",
            self.PAGE_WIDTH / 2,
            y_center,
            self.HEADING_FONT_SIZE,
            font="helv",  # Use standard font for English
            align="center",
            color=self.COLOR_GRAY
        )
        
        # Translation info
        info_y = y_center + 100
        
        # Completion date
        if self.job.completed_at:
            date_str = self.job.completed_at.strftime("%B %d, %Y")
            self._draw_text(
                page,
                f"Translated on: {date_str}",
                self.PAGE_WIDTH / 2,
                info_y,
                self.BODY_FONT_SIZE,
                align="center",
                color=self.COLOR_GRAY
            )
            info_y += 25
        
        # Segment count
        segments = self._get_segments_with_post_edit()
        if segments:
            segment_count = len(segments)
            self._draw_text(
                page,
                f"Total segments: {segment_count}",
                self.PAGE_WIDTH / 2,
                info_y,
                self.BODY_FONT_SIZE,
                align="center",
                color=self.COLOR_GRAY
            )
            info_y += 25
        
        # Post-edit status
        if self.job.post_edit_status == "COMPLETED":
            self._draw_text(
                page,
                "✓ Post-Edited",
                self.PAGE_WIDTH / 2,
                info_y,
                self.BODY_FONT_SIZE,
                align="center",
                color=self.COLOR_BLUE
            )
            info_y += 25
        
        # Illustration count if enabled
        if self.job.illustrations_data:
            illustration_count = sum(1 for ill in self.job.illustrations_data if ill.get('success'))
            if illustration_count > 0:
                self._draw_text(
                    page,
                    f"Illustrations: {illustration_count}",
                    self.PAGE_WIDTH / 2,
                    info_y,
                    self.BODY_FONT_SIZE,
                    align="center",
                    color=self.COLOR_GRAY
                )
        
        # Footer
        self._draw_text(
            page,
            "Generated by Context-Aware Translation System",
            self.PAGE_WIDTH / 2,
            self.PAGE_HEIGHT - 50,
            self.CAPTION_FONT_SIZE,
            align="center",
            color=self.COLOR_LIGHT_GRAY
        )
        
        # Reset current page to force new page for content
        self.current_page = None
        self.current_y = self.PAGE_HEIGHT  # Force new page on next content
    
    def _get_segments_with_post_edit(self):
        """
        Get translation segments, preferring post-edited versions if available.
        
        Returns:
            List of segments with translated_text field
        """
        # Check if post-edit log exists
        if self.job.post_edit_log_path and os.path.exists(self.job.post_edit_log_path):
            try:
                # Load post-edit log
                with open(self.job.post_edit_log_path, 'r', encoding='utf-8') as f:
                    post_edit_data = json.load(f)
                
                # Extract segments from post-edit log
                if 'segments' in post_edit_data:
                    segments = []
                    for seg in post_edit_data['segments']:
                        # Create segment in expected format
                        segment = {
                            'source_text': seg.get('source_text', ''),
                            'translated_text': seg.get('edited_translation', ''),  # Use edited translation
                            'original_translation': seg.get('original_translation', ''),
                            'was_edited': seg.get('was_edited', False)
                        }
                        segments.append(segment)
                    
                    logging.info(f"Using post-edited translations for PDF generation (job_id: {self.job.id})")
                    return segments
            except Exception as e:
                logging.error(f"Error loading post-edit log: {e}")
                # Fall through to use original segments
        
        # Use original translation segments if no post-edit available
        return self.job.translation_segments
    
    def _add_translation_content(self, include_source: bool, include_illustrations: bool):
        """
        Add the main translation content to the PDF.
        
        Args:
            include_source: Whether to include source text
            include_illustrations: Whether to include illustrations
        """
        # Check if post-edit results are available
        segments_to_use = self._get_segments_with_post_edit()
        
        if not segments_to_use:
            # Add a note if no segments available
            page = self._new_page()
            self._draw_text(
                page,
                "No translation segments available.",
                self.MARGIN_LEFT,
                self.current_y,
                self.BODY_FONT_SIZE,
                color=self.COLOR_GRAY
            )
            return
        
        # Get illustration data mapping
        illustration_map = {}
        if include_illustrations and self.job.illustrations_data:
            for ill in self.job.illustrations_data:
                if ill.get('success') and ill.get('illustration_path'):
                    illustration_map[ill.get('segment_index')] = ill.get('illustration_path')
        
        # Start on a new page after title page
        self.current_page = self._new_page()
        self.current_y = self.MARGIN_TOP
        
        # Process each segment
        for idx, segment in enumerate(segments_to_use):
            # Start new page if needed (with some buffer space)
            # Need more space for Korean text which is taller
            if self.current_y > self.PAGE_HEIGHT - self.MARGIN_BOTTOM - 50:
                self.current_page = self._new_page()
                self.current_y = self.MARGIN_TOP
            
            # Skip segment header for cleaner output
            # self._add_segment_header(idx + 1)
            
            # Add illustration BEFORE the text if available
            if include_illustrations and idx in illustration_map:
                self._add_illustration(illustration_map[idx], idx)
                self.current_y += 15  # Space between illustration and text
            
            # Add source text if requested
            if include_source and segment.get('source_text'):
                self._add_source_text(segment['source_text'])
            
            # Add translated text
            if segment.get('translated_text'):
                self._add_translated_text(segment['translated_text'])
            else:
                # Fallback to 'translation' field for backward compatibility
                if segment.get('translation'):
                    self._add_translated_text(segment['translation'])
            
            # Add proper paragraph spacing between segments
            self.current_y += self.BODY_FONT_SIZE * 1.5  # Increased from 10 to ~18 units for clearer separation
    
    def _add_segment_header(self, segment_number: int):
        """Add a segment header."""
        if not self.current_page:
            self.current_page = self._new_page()
        
        # Draw segment number
        header_text = f"Segment {segment_number}"
        self._draw_text(
            self.current_page,
            header_text,
            self.MARGIN_LEFT,
            self.current_y,
            self.CAPTION_FONT_SIZE,
            color=self.COLOR_BLUE
        )
        self.current_y += 15
    
    def _add_source_text(self, text: str):
        """Add source text in gray."""
        if not self.current_page:
            self.current_page = self._new_page()
        
        # Sanitize text for PDF rendering
        text = self._sanitize_text_for_pdf(text)
        
        # Wrap and draw source text
        lines = self._wrap_text(text, self.SOURCE_FONT_SIZE)
        for line in lines:
            # Check with buffer to prevent text cutoff
            if self.current_y + self.BODY_FONT_SIZE > self.PAGE_HEIGHT - self.MARGIN_BOTTOM:
                self.current_page = self._new_page()
                self.current_y = self.MARGIN_TOP
            
            self._draw_text(
                self.current_page,
                line,
                self.MARGIN_LEFT,
                self.current_y,
                self.SOURCE_FONT_SIZE,
                color=self.COLOR_GRAY
            )
            self.current_y += self.SOURCE_FONT_SIZE + 3
        
        self.current_y += 10  # Extra spacing after source text
    
    def _sanitize_text_for_pdf(self, text: str) -> str:
        """
        Sanitize text for PDF rendering to avoid character rendering issues.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        # Preserve paragraph breaks
        paragraphs = text.split('\n')
        sanitized_paragraphs = []
        
        for paragraph in paragraphs:
            # Replace em dash with spaced hyphen for better rendering
            paragraph = paragraph.replace('—', ' - ')
            # Replace other problematic Unicode dashes
            paragraph = paragraph.replace('–', ' - ')  # en dash
            paragraph = paragraph.replace('―', ' - ')  # horizontal bar
            # Only clean up excessive spaces (3+ spaces), preserve double spaces
            paragraph = re.sub(r'   +', '  ', paragraph)  # Replace 3+ spaces with 2
            paragraph = re.sub(r'  +(?=[가-힣])', ' ', paragraph)  # Single space before Korean
            sanitized_paragraphs.append(paragraph)
        
        # Rejoin with original line breaks preserved
        return '\n'.join(sanitized_paragraphs)
    
    def _add_translated_text(self, text: str):
        """Add translated text in black with justification."""
        if not self.current_page:
            self.current_page = self._new_page()
        
        # Sanitize text for PDF rendering
        text = self._sanitize_text_for_pdf(text)
        
        # Split text by paragraph breaks (double newlines first, then single if no double)
        if '\n\n' in text:
            paragraphs = text.split('\n\n')
        elif '\n' in text:
            # If only single newlines, treat them as paragraph breaks
            paragraphs = text.split('\n')
        else:
            paragraphs = [text]
        
        for p_idx, paragraph in enumerate(paragraphs):
            # Skip empty paragraphs
            if not paragraph.strip():
                continue
                
            # Wrap and draw each paragraph
            lines = self._wrap_text(paragraph.strip(), self.BODY_FONT_SIZE)
            num_lines = len(lines)
            
            for i, line in enumerate(lines):
                # Check with buffer to prevent text cutoff
                if self.current_y + self.BODY_FONT_SIZE > self.PAGE_HEIGHT - self.MARGIN_BOTTOM:
                    self.current_page = self._new_page()
                    self.current_y = self.MARGIN_TOP
                
                # Justify all lines except the last one in a paragraph
                is_last_line = (i == num_lines - 1)
                
                if is_last_line or len(line.split()) <= 1:
                    # Don't justify last line or single-word lines
                    self._draw_text(
                        self.current_page,
                        line,
                        self.MARGIN_LEFT,
                        self.current_y,
                        self.BODY_FONT_SIZE,
                        color=self.COLOR_BLACK
                    )
                else:
                    # Draw justified text
                    self._draw_justified_text(
                        self.current_page,
                        line,
                        self.MARGIN_LEFT,
                        self.current_y,
                        self.BODY_FONT_SIZE,
                        self.PAGE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT,
                        color=self.COLOR_BLACK
                    )
                
                self.current_y += self.BODY_FONT_SIZE + 6  # More line spacing for Korean text
            
            # Add paragraph spacing if not the last paragraph
            if p_idx < len(paragraphs) - 1:
                self.current_y += self.BODY_FONT_SIZE  # Extra line break between paragraphs within same segment
    
    def _add_illustration(self, illustration_path: str, segment_index: int):
        """
        Add an illustration to the PDF.
        
        Args:
            illustration_path: Path to the illustration file
            segment_index: Index of the segment for labeling
        """
        if not os.path.exists(illustration_path):
            logging.warning(f"Illustration file not found: {illustration_path}")
            return
        
        # Check if it's an image file
        if not illustration_path.endswith('.png'):
            # It might be a JSON prompt file, skip it or add a note
            if illustration_path.endswith('.json'):
                try:
                    with open(illustration_path, 'r', encoding='utf-8') as f:
                        prompt_data = json.load(f)
                        if prompt_data.get('prompt'):
                            # Add a note about the illustration prompt
                            self._add_illustration_prompt_note(prompt_data.get('prompt', ''))
                except Exception as e:
                    logging.error(f"Error reading prompt file: {e}")
            return
        
        try:
            # Check if we need a new page for the illustration (increased space check for larger images)
            if self.current_y > self.PAGE_HEIGHT - self.MARGIN_BOTTOM - 450:
                self.current_page = self._new_page()
                self.current_y = self.MARGIN_TOP
            
            # Load and insert the image
            img = Image.open(illustration_path)
            
            # Calculate dimensions to fit within page margins
            max_width = self.PAGE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT
            max_height = 450  # Increased maximum height for illustrations (was 300)
            
            # Calculate scaling factor
            width_ratio = max_width / img.width
            height_ratio = max_height / img.height
            scale_factor = min(width_ratio, height_ratio, 1.2)  # Allow slight upscaling up to 120%
            
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            
            # Center the image horizontally
            x_pos = (self.PAGE_WIDTH - new_width) / 2
            
            # Convert PIL image to bytes for PyMuPDF
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Insert the image
            rect = fitz.Rect(x_pos, self.current_y, x_pos + new_width, self.current_y + new_height)
            self.current_page.insert_image(rect, stream=img_bytes.getvalue())
            
            self.current_y += new_height + 5
            
            # Add caption
            caption = f"Illustration for Segment {segment_index + 1}"
            self._draw_text(
                self.current_page,
                caption,
                self.PAGE_WIDTH / 2,
                self.current_y,
                self.CAPTION_FONT_SIZE,
                align="center",
                color=self.COLOR_GRAY
            )
            self.current_y += 15
            
        except Exception as e:
            logging.error(f"Error adding illustration: {e}")
    
    def _add_illustration_prompt_note(self, prompt: str):
        """Add a note about illustration prompt when image is not available."""
        if not self.current_page:
            self.current_page = self._new_page()
        
        # Add a border box for the prompt note
        note_text = "Illustration prompt (image not generated):"
        self._draw_text(
            self.current_page,
            note_text,
            self.MARGIN_LEFT,
            self.current_y,
            self.CAPTION_FONT_SIZE,
            color=self.COLOR_BLUE
        )
        self.current_y += 12
        
        # Add the prompt text (truncated if too long)
        prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
        lines = self._wrap_text(prompt_preview, self.CAPTION_FONT_SIZE)
        for line in lines[:3]:  # Limit to 3 lines
            self._draw_text(
                self.current_page,
                line,
                self.MARGIN_LEFT + 10,
                self.current_y,
                self.CAPTION_FONT_SIZE,
                color=self.COLOR_LIGHT_GRAY
            )
            self.current_y += self.CAPTION_FONT_SIZE + 2
        
        self.current_y += 10
    
    def _add_metadata(self):
        """Add metadata to the PDF document."""
        # Sanitize filename for metadata
        filename = self.job.filename or 'Document'
        filename = self._sanitize_text_for_pdf(filename)
        
        metadata = {
            'title': f"Translation: {filename}",
            'author': 'Context-Aware Translation System',
            'subject': 'Literary Translation',
            'creator': 'PyMuPDF',
            'producer': 'Context-Aware Translation',
            'creationDate': datetime.now().strftime("%Y%m%d%H%M%S"),
            'modDate': datetime.now().strftime("%Y%m%d%H%M%S")
        }
        
        self.doc.set_metadata(metadata)
    
    def _new_page(self) -> fitz.Page:
        """Create a new page and add page number."""
        page = self.doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
        self.page_number += 1
        self.current_y = self.MARGIN_TOP
        
        # Add page number (skip on first page)
        if self.page_number > 1:
            self._draw_text(
                page,
                str(self.page_number),
                self.PAGE_WIDTH / 2,
                self.PAGE_HEIGHT - 30,
                self.CAPTION_FONT_SIZE,
                align="center",
                color=self.COLOR_GRAY
            )
        
        self.current_page = page
        return page
    
    def _draw_text(self, 
                   page: fitz.Page,
                   text: str,
                   x: float,
                   y: float,
                   font_size: float,
                   font: str = "korean",
                   color: Tuple[float, float, float] = COLOR_BLACK,
                   align: str = "left"):
        """
        Draw text on the page.
        
        Args:
            page: Page to draw on
            text: Text to draw
            x: X coordinate
            y: Y coordinate
            font_size: Font size
            font: Font name ("korean" for NanumGothic, "helv" for standard)
            color: RGB color tuple (0-1 range)
            align: Text alignment (left, center, right)
        """
        # Create text writer
        tw = fitz.TextWriter(page.rect)
        
        # Get the font object
        if font == "korean" or font == "CJK":
            font_obj = self.korean_font  # Use loaded NanumGothic font
        else:
            font_obj = fitz.Font(font)  # Use standard font
        
        # Calculate text position based on alignment
        if align == "center":
            # For Korean fonts, use a more accurate width calculation
            if font == "korean" or font == "CJK":
                # Count actual Korean characters vs ASCII characters for better estimation
                korean_count = sum(1 for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7AF)
                cjk_count = sum(1 for c in text if ord(c) > 0x3000 and not (ord(c) >= 0xAC00 and ord(c) <= 0xD7AF))
                ascii_count = len(text) - korean_count - cjk_count
                # NanumGothic has specific width ratios
                text_width = (korean_count * font_size * 0.88) + (cjk_count * font_size * 0.9) + (ascii_count * font_size * 0.48)
            else:
                try:
                    text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
                except:
                    text_width = len(text) * font_size * 0.5
            x = x - text_width / 2
        elif align == "right":
            # For Korean fonts, use a more accurate width calculation
            if font == "korean" or font == "CJK":
                # Count actual Korean characters vs ASCII characters for better estimation
                korean_count = sum(1 for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7AF)
                cjk_count = sum(1 for c in text if ord(c) > 0x3000 and not (ord(c) >= 0xAC00 and ord(c) <= 0xD7AF))
                ascii_count = len(text) - korean_count - cjk_count
                # NanumGothic has specific width ratios
                text_width = (korean_count * font_size * 0.88) + (cjk_count * font_size * 0.9) + (ascii_count * font_size * 0.48)
            else:
                try:
                    text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
                except:
                    text_width = len(text) * font_size * 0.5
            x = x - text_width
        
        # Add text with font object
        tw.append(
            (x, y),
            text,
            font=font_obj,
            fontsize=font_size
        )
        
        # Write text with color
        tw.write_text(page, color=color)
    
    def _draw_justified_text(self,
                            page: fitz.Page,
                            text: str,
                            x: float,
                            y: float,
                            font_size: float,
                            width: float,
                            font: str = "korean",
                            color: Tuple[float, float, float] = COLOR_BLACK):
        """
        Draw justified text on the page with controlled spacing.
        
        Args:
            page: Page to draw on
            text: Text to draw
            x: X coordinate (left margin)
            y: Y coordinate
            font_size: Font size
            width: Available width for the text
            font: Font name
            color: RGB color tuple (0-1 range)
        """
        # For Korean text, be more careful about word splitting
        if font == "korean" or font == "CJK":
            # Split on spaces but keep punctuation attached to words
            words = re.findall(r'\S+', text)
        else:
            words = text.split()
        
        if len(words) <= 1:
            # Can't justify single word
            self._draw_text(page, text, x, y, font_size, font, color)
            return
        
        # Create text writer
        tw = fitz.TextWriter(page.rect)
        
        # Get the font object
        if font == "korean" or font == "CJK":
            font_obj = self.korean_font  # Use loaded NanumGothic font
        else:
            font_obj = fitz.Font(font)
        
        # Calculate total text width without spaces
        total_text_width = 0
        for word in words:
            if font == "korean" or font == "CJK":
                # More accurate width calculation for NanumGothic
                korean_count = sum(1 for c in word if ord(c) >= 0xAC00 and ord(c) <= 0xD7AF)
                ascii_count = len(word) - korean_count
                word_width = (korean_count * font_size * 0.88) + (ascii_count * font_size * 0.48)
            else:
                try:
                    word_width = fitz.get_text_length(word, fontname="helv", fontsize=font_size)
                except:
                    word_width = len(word) * font_size * 0.5
            total_text_width += word_width
        
        # Add natural space width to total
        natural_space_width = font_size * 0.3
        num_spaces = len(words) - 1
        total_text_with_natural_spaces = total_text_width + num_spaces * natural_space_width
        
        # Calculate how much the line fills the width
        fill_ratio = total_text_with_natural_spaces / width
        
        # For lines that are very short (< 50%), don't justify
        if fill_ratio < 0.5:
            self._draw_text(page, text, x, y, font_size, font, color)
            return
        
        # Calculate space width to distribute
        if num_spaces > 0:
            # Calculate required space to fill the width
            required_total_space = width - total_text_width
            space_width = required_total_space / num_spaces
            
            # Set limits based on how full the line is
            # For nearly full lines (>85%), allow larger spaces
            # For less full lines, restrict spacing more
            if fill_ratio > 0.85:
                max_space = font_size * 1.2  # Allow moderate spacing for nearly full lines
            elif fill_ratio > 0.75:
                max_space = font_size * 1.0  # More restricted for medium-full lines
            else:
                max_space = font_size * 0.8  # Most restricted for shorter lines
            
            # Increased minimum space to prevent words sticking together
            min_space = font_size * 0.35  # Minimum space width (was 0.2)
            
            # Apply the limits
            space_width = max(min(space_width, max_space), min_space)
        else:
            space_width = font_size * 0.35  # Default space (was 0.3)
        
        # Draw each word with calculated spacing
        current_x = x
        for i, word in enumerate(words):
            # Add the word
            tw.append(
                (current_x, y),
                word,
                font=font_obj,
                fontsize=font_size
            )
            
            # Calculate word width
            if font == "korean" or font == "CJK":
                # More accurate width calculation for NanumGothic
                korean_count = sum(1 for c in word if ord(c) >= 0xAC00 and ord(c) <= 0xD7AF)
                ascii_count = len(word) - korean_count
                word_width = (korean_count * font_size * 0.88) + (ascii_count * font_size * 0.48)
            else:
                try:
                    word_width = fitz.get_text_length(word, fontname="helv", fontsize=font_size)
                except:
                    word_width = len(word) * font_size * 0.5
            
            # Move to next word position
            current_x += word_width
            if i < len(words) - 1:  # Don't add space after last word
                current_x += space_width
        
        # Write all text with color
        tw.write_text(page, color=color)
    
    def _wrap_text(self, text: str, font_size: float, font: str = "korean") -> List[str]:
        """
        Wrap text to fit within page margins.
        
        Args:
            text: Text to wrap
            font_size: Font size
            font: Font name
            
        Returns:
            List of wrapped lines
        """
        # Calculate actual available width accounting for margins
        max_width = self.PAGE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT
        
        # For Korean text, we need to wrap by characters, not just words
        # Split by spaces first, but also handle long words
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Check if adding this word would exceed the width
            test_line = ' '.join(current_line + [word])
            
            # Use a more conservative estimate for Korean fonts
            if font == "korean" or font == "CJK":
                # More accurate width calculation for NanumGothic
                korean_count = sum(1 for c in test_line if ord(c) >= 0xAC00 and ord(c) <= 0xD7AF)
                ascii_count = len(test_line) - korean_count
                estimated_width = (korean_count * font_size * 0.88) + (ascii_count * font_size * 0.48)
            else:
                try:
                    estimated_width = fitz.get_text_length(test_line, fontname="helv", fontsize=font_size)
                except:
                    estimated_width = len(test_line) * font_size * 0.5
            
            if estimated_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, break it into smaller chunks
                    # Use conservative estimate for NanumGothic characters
                    max_chars = int(max_width / (font_size * 0.88))
                    for i in range(0, len(word), max_chars):
                        lines.append(word[i:i+max_chars])
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else ['']


def generate_translation_pdf(
    job_id: int,
    db: Session,
    include_source: bool = True,
    include_illustrations: bool = True,
    page_size: str = "A4"
) -> bytes:
    """
    Generate a PDF for a translation job.
    
    Args:
        job_id: ID of the translation job
        db: Database session
        include_source: Whether to include source text
        include_illustrations: Whether to include illustrations
        page_size: Page size (A4 or Letter)
        
    Returns:
        PDF document as bytes
        
    Raises:
        ValueError: If job not found or not completed
    """
    # Get the job from database
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    
    if not job:
        raise ValueError(f"Translation job {job_id} not found")
    
    if job.status != "COMPLETED":
        raise ValueError(f"Translation job {job_id} is not completed (status: {job.status})")
    
    # Create PDF generator and generate PDF
    generator = PDFGenerator(job, db)
    pdf_bytes = generator.generate(
        include_source=include_source,
        include_illustrations=include_illustrations,
        page_size=page_size
    )
    
    return pdf_bytes