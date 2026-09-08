"""
"""

import re
from python.lib.lineardoc import normalize

def normalize_test(html: str, sort_attrs: bool = True) -> str:
    """Normalize HTML using normalizer module."""
    cleaned = re.sub(r"<span[^>]*class=\"Z3988\"[^>]*>.*?</span>", "", html, flags=re.DOTALL)
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r">\s+<", "><", cleaned)
    cleaned = cleaned.replace("&nbsp;", "\u00a0")
    cleaned = cleaned.strip()
    cleaned = normalize(cleaned, sort_attrs=sort_attrs)
    return cleaned
