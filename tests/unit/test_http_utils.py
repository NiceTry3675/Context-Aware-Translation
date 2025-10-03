import re

from backend.utils.http import build_content_disposition, split_content_disposition


def test_build_content_disposition_ascii():
    header = build_content_disposition("example_translation.pdf")
    # Pure ASCII should not include filename*
    assert "filename*=" not in header
    assert 'filename="example_translation.pdf"' in header


def test_build_content_disposition_unicode():
    filename = "소설_1권_translation.pdf"
    header = build_content_disposition(filename)
    # Should include ASCII fallback AND extended attribute
    assert "filename*=" in header
    fallback, extended = split_content_disposition(header)
    assert fallback.endswith("_translation.pdf")
    # Fallback must be ASCII-only
    assert fallback.isascii()
    # Extended must contain percent-encoded bytes for Korean
    assert "%EC%86%8C" in extended  # '소'


def test_build_content_disposition_empty():
    header = build_content_disposition("")
    assert 'filename="download"' in header
