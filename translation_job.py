import os
import re

class TranslationJob:
    """
    Represents a single translation job, responsible for handling the source text
    and storing the results.
    """
    def __init__(self, filepath: str, target_segment_size: int = 15000):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file '{filepath}' does not exist.")
        
        self.filepath = filepath
        self.base_filename = os.path.splitext(os.path.basename(filepath))[0]
        self.segments = self._create_segments_from_file(target_segment_size)
        self.translated_segments = []
        self.glossary = {}
        self.character_styles = {}
        
        self.output_filename = os.path.join('translated_novel', f"{self.base_filename}_translated.txt")
        # Clear the output file at the start of the job
        with open(self.output_filename, 'w', encoding='utf-8') as f:
            f.write("")

    def _create_segments_from_file(self, target_size: int) -> list[str]:
        """
        Reads the source file and splits it into robust segments.
        This version uses a refined pre-processing step to correctly handle
        long paragraphs without introducing extra newlines.
        """
        print(f"Reading and segmenting file: {self.filepath}")
        with open(self.filepath, 'r', encoding='utf-8') as f:
            full_text = f.read()

        # 1. Split the text into paragraphs.
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', full_text) if p.strip()]
        
        # 2. Pre-process: Break down very long paragraphs into sentence-based chunks.
        processed_parts = []
        for para in paragraphs:
            if len(para) > target_size * 1.5:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                
                sub_chunk_sentences = []
                sub_chunk_length = 0
                for sentence in sentences:
                    sub_chunk_sentences.append(sentence)
                    sub_chunk_length += len(sentence)
                    if sub_chunk_length >= target_size:
                        # Join sentences within a chunk with a space.
                        processed_parts.append(" ".join(sub_chunk_sentences))
                        sub_chunk_sentences = []
                        sub_chunk_length = 0
                
                if sub_chunk_sentences:
                    processed_parts.append(" ".join(sub_chunk_sentences))
            else:
                # Keep normal-sized paragraphs as they are.
                processed_parts.append(para)

        # 3. Group the processed parts (paragraphs and chunks) into final segments.
        segments = []
        current_segment_parts = []
        current_length = 0
        for part in processed_parts:
            # If adding the next part would make the segment too large, finalize the current one.
            # This prevents very large segments. A 1.2x multiplier provides some flexibility.
            if current_segment_parts and (current_length + len(part)) > target_size * 1.2:
                 segments.append("\n\n".join(current_segment_parts))
                 current_segment_parts = []
                 current_length = 0

            current_segment_parts.append(part)
            current_length += len(part)
            
            # Finalize if the target size is met or exceeded.
            if current_length >= target_size:
                segments.append("\n\n".join(current_segment_parts))
                current_segment_parts = []
                current_length = 0

        # Add the last remaining parts as the final segment.
        if current_segment_parts:
            segments.append("\n\n".join(current_segment_parts))
        
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
