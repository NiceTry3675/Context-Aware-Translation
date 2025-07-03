import os
import re

class TranslationJob:
    """
    Represents a single translation job, responsible for handling the source text
    and storing the results.
    """
    def __init__(self, filepath: str, target_segment_size: int = 30000):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file '{filepath}' does not exist.")
        
        self.filepath = filepath
        self.base_filename = os.path.splitext(os.path.basename(filepath))[0]
        self.segments = self._create_segments_from_file(target_segment_size)
        self.translated_segments = []
        
        self.output_filename = os.path.join('translated_novel', f"{self.base_filename}_translated.txt")
        # Clear the output file at the start of the job
        with open(self.output_filename, 'w', encoding='utf-8') as f:
            f.write("")

    def _create_segments_from_file(self, target_size: int) -> list[str]:
        """Reads the source file and splits it into segments."""
        print(f"Reading and segmenting file: {self.filepath}")
        with open(self.filepath, 'r', encoding='utf-8') as f:
            full_text = f.read()
        
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', full_text) if p.strip()]
        segments, current_segment_paras, current_length = [], [], 0
        for para in paragraphs:
            current_segment_paras.append(para)
            current_length += len(para)
            if current_length >= target_size:
                segments.append("\n\n".join(current_segment_paras))
                current_segment_paras, current_length = [], 0
        if current_segment_paras:
            segments.append("\n\n".join(current_segment_paras))
        print(f"Text divided into {len(segments)} segments.")
        return segments

    def append_translated_segment(self, translated_text: str):
        """Appends a translated segment to the list and the output file."""
        self.translated_segments.append(translated_text)
        with open(self.output_filename, 'a', encoding='utf-8') as f:
            f.write(translated_text + "\n\n" + "="*20 + "\n\n")
        print(f"Appended translated segment to {self.output_filename}")

    def get_previous_segment(self, current_index: int) -> str:
        """Returns the content of the previous segment."""
        return self.segments[current_index - 1] if current_index > 0 else ""

    def get_previous_translation(self, current_index: int) -> str:
        """Returns the translation of the previous segment."""
        return self.translated_segments[current_index - 1] if current_index > 0 else ""
