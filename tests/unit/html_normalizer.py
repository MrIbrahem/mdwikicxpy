""" """

import re

from python.lib.lineardoc import normalize

import pywikibot

def show_html_diff(result: str, expected_result: str) -> None:
    if result != expected_result:
        result2 = re.sub(r">\s*<", ">\n<", result)
        expected = re.sub(r">\s*<", ">\n<", expected_result)
        pywikibot.showDiff(expected, result2)


def normalize_test_base(cleaned: str, sort_attrs: bool = True) -> str:
    """Normalize HTML using normalizer module."""
    cleaned = cleaned.strip()
    cleaned = re.sub(r">\s+<", "><", cleaned)
    cleaned = cleaned.replace("&nbsp;", "\u00a0")
    cleaned = cleaned.strip()
    cleaned = normalize(cleaned, sort_attrs=sort_attrs)
    return cleaned


def normalize_test(cleaned: str, sort_attrs: bool = True) -> str:
    """Normalize HTML using normalizer module."""
    cleaned = re.sub(r"\s+", " ", cleaned)
    return normalize_test_base(cleaned, sort_attrs=sort_attrs)
