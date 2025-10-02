"""Tests for HTTP utility functions."""

import pytest
from backend.utils.http import build_content_disposition, split_content_disposition


class TestAsciiFilenames:
    """Test cases for pure ASCII filenames."""

    def test_simple_ascii(self):
        """Pure ASCII filename should only have basic filename parameter."""
        result = build_content_disposition("document.pdf")
        assert result == 'attachment; filename="document.pdf"'

    def test_ascii_with_underscores(self):
        """ASCII with allowed characters."""
        result = build_content_disposition("my_file-2024.txt")
        assert result == 'attachment; filename="my_file-2024.txt"'


class TestKoreanFilenames:
    """Test cases for Korean (non-ASCII) filenames."""

    def test_korean_simple(self):
        """Korean filename should have both fallback and UTF-8 encoded version."""
        result = build_content_disposition("한글.pdf")
        fallback, extended = split_content_disposition(result)

        assert fallback == "download.pdf"  # Korean chars stripped, fallback used
        assert "UTF-8''" in extended
        assert "%ED%95%9C%EA%B8%80.pdf" in extended

    def test_korean_with_english(self):
        """Mixed Korean-English filename."""
        result = build_content_disposition("소설_권1_translation.pdf")
        fallback, extended = split_content_disposition(result)

        # Fallback has Korean stripped, keeping ASCII parts
        assert "1_translation.pdf" in fallback
        assert "UTF-8''" in extended
        # Verify the Korean parts are percent-encoded
        assert "%EC%86%8C%EC%84%A4" in extended  # 소설
        assert "%EA%B6%8C" in extended  # 권

    def test_korean_novel_title(self):
        """Real-world case: Korean novel title."""
        result = build_content_disposition("나의_이야기_제1권.pdf")
        fallback, extended = split_content_disposition(result)

        # Fallback should have extension (Korean stripped, only "1" remains)
        assert fallback.endswith(".pdf")
        assert "1" in fallback  # The only remaining ASCII character

        # Extended should be UTF-8 encoded with full filename
        assert "UTF-8''" in extended
        assert ".pdf" in extended
        assert "%EB%82%98%EC%9D%98" in extended  # 나의


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_filename(self):
        """Empty filename should use default."""
        result = build_content_disposition("")
        assert 'filename="download"' in result

    def test_no_extension(self):
        """Filename without extension."""
        result = build_content_disposition("한글파일")
        fallback, extended = split_content_disposition(result)

        assert fallback == "download"
        assert "UTF-8''" in extended

    def test_special_chars(self):
        """Special characters that need escaping."""
        result = build_content_disposition("파일 (1).pdf")
        fallback, extended = split_content_disposition(result)

        # Fallback should replace spaces and parens
        assert " " not in fallback or fallback == "download.pdf"

        # Extended should percent-encode everything
        assert "UTF-8''" in extended
        assert "%28" in extended  # (
        assert "%29" in extended  # )
        assert "%20" in extended  # space

    def test_very_long_filename(self):
        """Very long filename should be truncated in fallback."""
        long_name = "a" * 200 + ".pdf"
        result = build_content_disposition(long_name)
        fallback, extended = split_content_disposition(result)

        # Fallback should be limited (120 chars base + extension)
        assert len(fallback) <= 125

        # Extended should have full name
        assert "UTF-8''" in extended
        assert long_name in extended or "a" * 100 in extended


class TestRFC5987Compliance:
    """Test RFC 5987 / RFC 6266 compliance."""

    def test_header_is_ascii_only(self):
        """Entire header value must be ASCII-encodable (latin-1 compatible)."""
        result = build_content_disposition("한글파일.pdf")

        # This should not raise UnicodeEncodeError
        try:
            result.encode('latin-1')
        except UnicodeEncodeError:
            pytest.fail("Header value contains non-latin-1 characters")

    def test_filename_star_format(self):
        """filename* should follow UTF-8''<encoded> format."""
        result = build_content_disposition("테스트.txt")

        assert 'filename*=UTF-8\'\'' in result
        # The part after UTF-8'' should be percent-encoded
        parts = result.split("filename*=UTF-8''")
        if len(parts) > 1:
            encoded_part = parts[1]
            assert "%" in encoded_part  # Should have percent encoding
