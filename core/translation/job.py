import os
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from ..utils.file_parser import parse_document
from collections.abc import Generator

class SegmentInfo:
    """A simple class to hold segment data and its context."""
    def __init__(self, text, chapter_title=None, chapter_filename=None):
        self.text = text
        self.chapter_title = chapter_title
        self.chapter_filename = chapter_filename

class TranslationJob:
    """
    Represents a single translation job, handling different file formats
    and orchestrating the segmentation and saving process in a memory-efficient way.
    """
    def __init__(self, filepath: str, original_filename: str = None, target_segment_size: int = 15000):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file '{filepath}' does not exist.")
        
        self.filepath = filepath
        user_facing_filename = original_filename if original_filename else os.path.basename(filepath)
        self.user_base_filename = os.path.splitext(user_facing_filename)[0]
        unique_base_filename = os.path.splitext(os.path.basename(filepath))[0]
        
        self.input_format = os.path.splitext(user_facing_filename.lower())[1]
        
        self.glossary = {}
        self.character_styles = {}
        self.target_segment_size = target_segment_size

        output_dir = 'translated_novel'
        os.makedirs(output_dir, exist_ok=True)
        
        if self.input_format == '.epub':
            self.output_filename = os.path.join(output_dir, f"{unique_base_filename}_translated.epub")
            self.original_book = epub.read_epub(self.filepath)
        else:
            self.output_filename = os.path.join(output_dir, f"{unique_base_filename}_translated.txt")
        
        # Clean up previous partial files before starting a new job
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)

    def stream_segments(self) -> Generator[SegmentInfo, None, None]:
        """Yields segments one by one from the source file."""
        print(f"Streaming segments for {self.input_format} file...")
        full_text = parse_document(self.filepath)
        yield from self._segment_text_generator(full_text, self.target_segment_size)

    def _segment_text_generator(self, text: str, target_size: int) -> Generator[SegmentInfo, None, None]:
        """A generator that yields text segments of a target size."""
        raw_paragraphs = re.split(r'\n\s*\n', text)
        
        normalized_paragraphs = []
        for para in raw_paragraphs:
            if not para.strip():
                continue
            lines = para.strip().split('\n')
            processed_lines = []
            current_sentence = ""
            for line in lines:
                line = line.strip()
                if not line: continue
                if current_sentence and re.search(r'[.!?]["\\]?$', current_sentence):
                    processed_lines.append(current_sentence)
                    current_sentence = line
                else:
                    current_sentence += (" " + line) if current_sentence else line
            if current_sentence:
                processed_lines.append(current_sentence)
            normalized_paragraphs.append("\n".join(processed_lines))
        
        current_segment_text = ""
        segment_count = 0
        for para in normalized_paragraphs:
            if len(current_segment_text) + len(para) > target_size and current_segment_text:
                segment_count += 1
                yield SegmentInfo(current_segment_text.strip())
                current_segment_text = ""
            
            if len(para) > target_size:
                sentences = para.split('\n')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence: continue
                    if len(current_segment_text) + len(sentence) > target_size and current_segment_text:
                        segment_count += 1
                        yield SegmentInfo(current_segment_text.strip())
                        current_segment_text = ""
                    current_segment_text += sentence + "\n"
                current_segment_text = current_segment_text.strip() + "\n\n"
            else:
                current_segment_text += para + "\n\n"
        
        if current_segment_text.strip():
            segment_count += 1
            yield SegmentInfo(current_segment_text.strip())
        
        print(f"Finished streaming. Total segments yielded: {segment_count}")

    def append_translated_segment(self, translated_text: str):
        """Appends a translated segment directly to the output file."""
        if self.input_format == '.epub':
            # For EPUB, we still need to collect content to build the HTML file at the end.
            # This is a trade-off. We store translated text in a temporary list.
            if not hasattr(self, '_temp_translated_segments'):
                self._temp_translated_segments = []
            self._temp_translated_segments.append(translated_text)
        else:
            with open(self.output_filename, 'a', encoding='utf-8') as f:
                f.write(translated_text + "\n")

    def finalize_translation(self):
        """Finalizes the translation process, especially for complex formats like EPUB."""
        print(f"\nFinalizing output for {self.output_filename}...")
        if self.input_format == '.epub' and hasattr(self, '_temp_translated_segments'):
            self._save_as_epub(self._temp_translated_segments)
            del self._temp_translated_segments # Clean up memory
        print("Finalization complete.")

    def _save_as_epub(self, translated_segments: list[str]):
        """Saves the translated content as a simple, single-chapter EPUB."""
        translated_book = epub.EpubBook()
        try:
            title = self.original_book.get_metadata('DC', 'title')[0][0]
            translated_book.set_title(f"[KOR] {title}")
        except (IndexError, KeyError):
            translated_book.set_title(f"[KOR] {self.user_base_filename}")
        
        translated_book.set_language('ko')
        for author in self.original_book.get_metadata('DC', 'creator'):
            translated_book.add_author(author[0])

        cover_image_item = next((item for item in self.original_book.get_items_of_type(ebooklib.ITEM_IMAGE) if 'cover' in item.get_name().lower()), None)
        if cover_image_item:
            translated_book.set_cover(cover_image_item.file_name, cover_image_item.content)

        full_translated_text = "".join(translated_segments)
        main_chapter = epub.EpubHtml(title='Translated Content', file_name='chap_1.xhtml', lang='ko')
        
        html_body = "".join([f"<p>{para.strip()}</p>" for para in full_translated_text.split('\n') if para.strip()])
        main_chapter.content = f'<html><head><title>Translation</title></head><body>{html_body}</body></html>'
        
        translated_book.add_item(main_chapter)
        translated_book.toc = [main_chapter]
        translated_book.spine = ['nav', main_chapter]
        translated_book.add_item(epub.EpubNcx())
        translated_book.add_item(epub.EpubNav())

        epub.write_epub(self.output_filename, translated_book, {})
