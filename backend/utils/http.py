"""HTTP related utility helpers.

Currently includes helpers for building standards-compliant headers that
need to carry non-ASCII values (e.g. filenames with Korean characters).

We follow RFC 5987 / RFC 6266 for Content-Disposition with both an ASCII
fallback filename and UTF-8 encoded extended filename (filename*).
"""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
from typing import Tuple


_FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _ascii_fallback(filename: str) -> str:
    """Create a conservative ASCII fallback for a potentially unicode filename.

    Steps:
      1. Separate extension.
      2. NFKD normalize and strip non-ASCII by encode/decode.
      3. Replace disallowed chars with underscore.
      4. Ensure not empty; if empty use 'download'.

    We keep the original extension (lowercased) when possible.
    """
    if not filename:
        return "download"

    # Split extension
    if "." in filename:
        base, ext = filename.rsplit(".", 1)
        dot_ext = "." + ext.lower()
    else:
        base, dot_ext = filename, ""

    normalized = unicodedata.normalize("NFKD", base)
    ascii_part = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_part = _FILENAME_SAFE_PATTERN.sub("_", ascii_part)
    ascii_part = ascii_part.strip("._- ")
    if not ascii_part:
        ascii_part = "download"
    # Limit length to something reasonable to avoid header bloat
    if len(ascii_part) > 120:
        ascii_part = ascii_part[:120]
    return ascii_part + dot_ext


def build_content_disposition(filename: str) -> str:
    """Build a Content-Disposition header value that is safe for non-ASCII filenames.

    Returns a value like:
        attachment; filename="fallback.pdf"; filename*=UTF-8''%EC%9D%B4%EB%A6%84.pdf

    Starlette encodes header values as latin-1, so we must keep the *entire* header
    value ASCII-only. We therefore percent-encode the UTF-8 form for filename*.
    """
    fallback = _ascii_fallback(filename)
    # Percent-encode original (UTF-8) per RFC 5987
    quoted = urllib.parse.quote(filename, safe="")
    # If original already pure ASCII and equals fallback, we can omit filename*
    if filename == fallback and filename.isascii():
        return f'attachment; filename="{fallback}"'
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quoted}"


def split_content_disposition(header_value: str) -> Tuple[str, str]:
    """Simple helper mainly for tests: returns (fallback, extended) parts.
    If extended part missing, second item is empty string.
    """
    parts = header_value.split(";")
    fallback = ""
    extended = ""
    for p in parts:
        p = p.strip()
        if p.startswith("filename="):
            fallback = p[len("filename="):].strip('"')
        elif p.startswith("filename*="):
            extended = p[len("filename*="):]
    return fallback, extended

__all__ = [
    "build_content_disposition",
    "split_content_disposition",
]
