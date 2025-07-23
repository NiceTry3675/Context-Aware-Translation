# file_parser.py

import os
import docx
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import markdown
import fitz  # PyMuPDF

def _parse_txt(filepath):
    """Parses a .txt file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def _parse_docx(filepath):
    """Parses a .docx file and returns its text content."""
    try:
        doc = docx.Document(filepath)
        # Join paragraphs with double newlines to preserve structure
        return "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        print(f"Error parsing DOCX file {filepath}: {e}")
        raise

def _parse_epub(filepath):
    """Parses an .epub file and returns its text content."""
    try:
        book = epub.read_epub(filepath)
        content = []
        # Iterate through all document items in the book
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            # Extract text and append, preserving paragraph breaks with newlines
            text = soup.get_text(separator='\n', strip=True)
            if text:
                content.append(text)
        return "\n\n".join(content)
    except Exception as e:
        print(f"Error parsing EPUB file {filepath}: {e}")
        raise

def _parse_md(filepath):
    """Parses a .md file and returns its text content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            md_text = f.read()
        # Convert markdown to HTML, then extract text
        html = markdown.markdown(md_text)
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        print(f"Error parsing Markdown file {filepath}: {e}")
        raise

def _parse_pdf(filepath):
    """Parses a .pdf file and returns its text content."""
    try:
        doc = fitz.open(filepath)
        content = []
        for page in doc:
            content.append(page.get_text())
        doc.close()
        return "\n\n".join(content)
    except Exception as e:
        print(f"Error parsing PDF file {filepath}: {e}")
        raise

def parse_document(filepath: str) -> str:
    """
    Detects the file type based on its extension and uses the appropriate
    parser to extract clean, plain text.

    Args:
        filepath: The absolute path to the file.

    Returns:
        The extracted plain text from the document.
    
    Raises:
        ValueError: If the file format is not supported.
    """
    # Get the file extension and convert to lowercase for matching
    _, extension = os.path.splitext(filepath.lower())
    
    parser_map = {
        '.txt': _parse_txt,
        '.docx': _parse_docx,
        '.epub': _parse_epub,
        '.md': _parse_md,
        '.pdf': _parse_pdf,
    }

    if extension in parser_map:
        print(f"Detected '{extension}' file. Using the appropriate parser.")
        return parser_map[extension](filepath)
    else:
        # If the extension is not found in our map, raise an error
        supported_formats = ", ".join(parser_map.keys())
        raise ValueError(f"Unsupported file format: '{extension}'. Supported formats are: {supported_formats}")
