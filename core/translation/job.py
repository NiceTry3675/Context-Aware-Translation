import os
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from ..utils.file_parser import parse_document

class SegmentInfo:
    """A simple class to hold segment data and its context."""
    def __init__(self, text, chapter_title=None, chapter_filename=None):
        self.text = text
        self.chapter_title = chapter_title
        self.chapter_filename = chapter_filename

class TranslationJob:
    """
    Represents a single translation job, handling different file formats
    and orchestrating the segmentation and saving process.
    """
    def __init__(self, filepath: str, target_segment_size: int = 15000):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file '{filepath}' does not exist.")
        
        self.filepath = filepath
        self.base_filename = os.path.splitext(os.path.basename(filepath))[0]
        self.input_format = os.path.splitext(filepath.lower())[1]
        
        self.segments = []
        self.translated_segments = []
        self.glossary = {}
        self.character_styles = {}
        self.style_map = {} # For EPUB styles

        if self.input_format == '.epub':
            self.original_book = epub.read_epub(self.filepath)
            self.output_filename = os.path.join('translated_novel', f"{self.base_filename}_translated.epub")
            self.segments = self._create_segments_for_epub(target_segment_size)
        else:
            self.output_filename = os.path.join('translated_novel', f"{self.base_filename}_translated.txt")
            self.segments = self._create_segments_for_text(target_segment_size)
        
        os.makedirs(os.path.dirname(self.output_filename), exist_ok=True)

    def _create_segments_for_epub(self, target_size: int) -> list[SegmentInfo]:
        """
        Creates size-aware segments from the entire EPUB's text content,
        treating it as a single text block.
        """
        print("Creating segments for EPUB by flattening to text...")
        # Use the existing text parser to get all text from the EPUB
        full_text = parse_document(self.filepath)
        
        # Use the same segmentation logic as for plain text files
        return self._create_segments_from_plain_text(full_text, target_size)

    def _create_segments_for_text(self, target_size: int) -> list[SegmentInfo]:
        """Creates size-aware segments from a plain text source."""
        print("Creating segments for text file...")
        full_text = parse_document(self.filepath)
        return self._create_segments_from_plain_text(full_text, target_size)

    def _create_segments_from_plain_text(self, text: str, target_size: int) -> list[SegmentInfo]:
        """Helper function to segment a block of text with sentence-aware splitting."""
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
            
        print(f"Text divided into {len(segments)} segments.")
        
        # Debug: Show first few characters of each segment
        for i, seg in enumerate(segments[:3]):  # Show first 3 segments
            preview = seg.text[:100].replace('\n', ' ')
            if len(seg.text) > 100:
                preview += "..."
            print(f"  Segment {i+1}: {preview}")
        
        return segments

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences while preserving line breaks that indicate sentence boundaries."""
        # Common abbreviations that shouldn't end sentences
        abbreviations = {'Mr', 'Mrs', 'Dr', 'Ms', 'Prof', 'Sr', 'Jr', 'Ph.D', 'M.D', 'B.A', 
                        'M.A', 'D.D.S', 'Ph', 'Inc', 'Corp', 'Co', 'Ltd', 'etc', 'vs', 'i.e', 'e.g'}
        
        # Split by line breaks first
        lines = text.split('\n')
        all_sentences = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Process each line for sentence boundaries
            sentences_in_line = self._split_block_into_sentences(line, abbreviations)
            all_sentences.extend(sentences_in_line)
        
        return all_sentences
    
    def _split_block_into_sentences(self, text: str, abbreviations: set) -> list[str]:
        """Split a block of text into sentences."""
        # Protect abbreviations by replacing their periods temporarily
        protected_text = text
        for abbr in abbreviations:
            protected_text = protected_text.replace(f"{abbr}.", f"{abbr}@@@")
        
        # Split on sentence boundaries
        # This regex looks for periods, exclamation marks, or question marks
        # followed by a space and then a capital letter or quote
        sentences = re.split(r'(?<=[.!?])\s+(?=["\'A-Z])', protected_text)
        
        # Handle edge case where the last sentence might not have a following capital
        if not sentences:
            sentences = [protected_text]
        
        # Restore the periods in abbreviations
        sentences = [s.replace('@@@', '.') for s in sentences]
        
        # Clean up and filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences

    def append_translated_segment(self, translated_text: str, original_segment: SegmentInfo):
        """Appends a translated segment text along with its original context."""
        self.translated_segments.append(SegmentInfo(translated_text, original_segment.chapter_title, original_segment.chapter_filename))

    def save_final_output(self):
        """Saves the final output based on the input file format."""
        print(f"\nSaving final output to {self.output_filename}...")
        if self.input_format == '.epub':
            self._save_as_epub()
        else:
            self._save_as_text()
        print("Save complete.")

    def _save_as_text(self):
        """Saves the translated segments as a single .txt file."""
        with open(self.output_filename, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(self.translated_segments):
                # Write the translated text, preserving original formatting
                f.write(segment.text)
                # Add the separator, but not for the very last segment
                if i < len(self.translated_segments) - 1:
                    f.write("\n" + "="*20 + "\n\n")

    def _save_as_epub(self):
        """Saves the translated content as a very simple, single-chapter EPUB."""
        translated_book = epub.EpubBook()

        # Set basic metadata
        try:
            title = self.original_book.get_metadata('DC', 'title')[0][0]
            translated_book.set_title(f"[KOR] {title}")
        except (IndexError, KeyError):
            translated_book.set_title(f"[KOR] {self.base_filename}")
        translated_book.set_language('ko')
        for author in self.original_book.get_metadata('DC', 'creator'):
            translated_book.add_author(author[0])

        # Find and add cover
        cover_image_item = None
        for item in self.original_book.get_items_of_type(ebooklib.ITEM_IMAGE):
            if 'cover' in item.get_name().lower():
                cover_image_item = item
                break
        
        if cover_image_item:
            translated_book.set_cover(cover_image_item.file_name, cover_image_item.content)

        # Combine all translated text into one block
        full_translated_text = "".join(seg.text for seg in self.translated_segments)

        # Create a single chapter with the full text
        main_chapter = epub.EpubHtml(title='Translated Content', file_name='chap_1.xhtml', lang='ko')
        
        html_body = ""
        for para in full_translated_text.split('\n'):
            if para.strip():
                html_body += f"<p>{para.strip()}</p>"
        
        main_chapter.content = f'<html><head><title>Translation</title></head><body>{html_body}</body></html>'
        
        translated_book.add_item(main_chapter)

        # Basic TOC and Spine
        translated_book.toc = [main_chapter]
        translated_book.spine = ['nav', main_chapter]
        translated_book.add_item(epub.EpubNcx())
        translated_book.add_item(epub.EpubNav())

        epub.write_epub(self.output_filename, translated_book, {})

    def get_previous_segment(self, current_index: int) -> str:
        """Returns the text of the previous segment."""
        return self.segments[current_index - 1].text if current_index > 0 else ""

    def get_previous_translation(self, current_index: int) -> str:
        """Returns the translation of the previous segment."""
        return self.translated_segments[current_index - 1].text if current_index > 0 else ""