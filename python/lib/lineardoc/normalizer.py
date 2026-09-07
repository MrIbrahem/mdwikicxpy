"""
Normalizer - Parser to normalize XML.

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/Normalizer.js
"""

from __future__ import annotations

import logging
import re
from typing import Any
from .sax_html_parser import SaxHTMLParser
from .utils import Utils

logger = logging.getLogger(__name__)


class Normalizer:
    """Parser to normalize XML."""

    def __init__(self, sort_attrs: bool = True) -> None:
        """
        Initialize the parser.
        """
        self.lowercase = True
        self.sort_attrs = sort_attrs

    def init(self) -> None:
        """
        Initialize state for parsing.
        """
        self.doc = []
        self.tags: list[dict] = []

    def on_open_tag(self, tag: dict[str, Any]) -> None:
        """
        Handle open tag event.

        Args:
            tag: Tag dict with 'name' and 'attributes'
        """
        self.tags.append(tag)
        self.doc.append(Utils.get_open_tag_html(tag, self.sort_attrs))

    def on_close_tag(self, tag_name: str) -> None:
        """
        Handle close tag event.

        Args:
            tag_name: Name of tag to close
        """
        tag = self.tags.pop()

        if tag["name"] != tag_name:
            raise Exception(f'Unmatched tags: {tag["name"]} !== {tag_name}')

        self.doc.append(Utils.get_close_tag_html(tag))

    def on_text(self, text: str) -> None:
        """
        Handle text event.

        Args:
            text: Text content
        """
        self.doc.append(Utils.esc(text))

    def on_script(self, text: str) -> None:
        """Handle script text."""

    def get_html(self) -> str:
        """
        Get the normalized HTML.

        Returns:
            Normalized HTML string
        """
        return "".join(self.doc)

    def write(self, html: str) -> None:
        """
        Parse HTML into the document.

        Args:
            html: HTML string to parse
        """
        parser = SaxHTMLParser(self, html)
        parser.feed(html)
        parser.close()


def normalize(html: str, sort_attrs: bool = True) -> str:
    """
    Normalize HTML by parsing and re-serializing.

    Args:
        html: HTML string to normalize

    Returns:
        Normalized HTML string
    """
    html = html.strip()
    html = html.replace("&nbsp;", "\u00a0")
    normalizer = Normalizer(sort_attrs=sort_attrs)
    normalizer.init()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", "", html)
    html = re.sub(r">\s+<", "><", html)
    normalizer.write(html)
    return normalizer.get_html()


__all__ = [
    "Normalizer",
    "normalize",
]
