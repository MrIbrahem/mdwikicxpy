"""
Normalizer - Parser to normalize XML.
"""

from __future__ import annotations

from typing import Any

from lxml import etree

from . import utils
from .parser import VOID_ELEMENTS


def esc(s):
    """Escape text for inclusion in HTML."""
    return s.replace("&", "&#38;").replace("<", "&#60;").replace(">", "&#62;")


class Normalizer:
    """Parser to normalize XML."""

    def __init__(self) -> None:
        """Initialize the normalizer."""
        self.lowercase = True

    def init(self) -> None:
        """Initialize state for parsing."""
        self.doc = []
        self.tags: list[dict] = []

    def write(self, html: str) -> None:
        """
        Parse and normalize HTML.

        Args:
            html: HTML string to normalize
        """
        parser = etree.HTMLParser(encoding="utf-8")
        try:
            tree = etree.fromstring(html, parser)
            self._process_element(tree)
        except Exception:
            # Try with wrapping
            try:
                tree = etree.fromstring(f"<div>{html}</div>", parser)
                for child in tree:
                    self._process_element(child)
            except Exception as e:
                raise Exception(f"Failed to parse HTML: {e}") from e

    def _process_element(self, element: etree.Element | Any) -> None:
        """Process an element recursively."""
        # Create tag dict
        tag_name = element.tag.lower() if self.lowercase else element.tag
        tag = {"name": tag_name, "attributes": dict(element.attrib)}

        # Mark HTML void elements as self-closing
        if tag_name in VOID_ELEMENTS:
            tag["isSelfClosing"] = True

        self.on_open_tag(tag)

        # Process text content
        if element.text:
            self.on_text(element.text)

        # Process children
        for child in element:
            self._process_element(child)
            # Process tail text after child
            if child.tail:
                self.on_text(child.tail)

        self.on_close_tag(tag_name)

    def on_open_tag(self, tag: dict[str, Any]) -> None:
        """Handle open tag event."""
        self.tags.append(tag)
        self.doc.append(utils.get_open_tag_html(tag))

    def on_close_tag(self, tag_name) -> None:
        """Handle close tag event."""
        tag = self.tags.pop()

        if tag["name"] != tag_name:
            raise Exception(f'Unmatched tags: {tag["name"]} !== {tag_name}')

        self.doc.append(utils.get_close_tag_html(tag))

    def on_text(self, text: str) -> None:
        """Handle text event."""
        self.doc.append(esc(text))

    def get_html(self) -> str:
        """
        Get the normalized HTML.

        Returns:
            Normalized HTML string
        """
        return "".join(self.doc)


__all__ = [
    "Normalizer",
    "esc",
]
