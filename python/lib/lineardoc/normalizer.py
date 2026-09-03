"""
Normalizer - Parser to normalize XML.
"""

from __future__ import annotations
import logging
from typing import Any

from . import utils
from .parser_and_normalizer_shared import SharedParserNormalizer

logger = logging.getLogger(__name__)

def esc(s):
    """Escape text for inclusion in HTML."""
    return s.replace("&", "&#38;").replace("<", "&#60;").replace(">", "&#62;")


class Normalizer(SharedParserNormalizer):
    """Parser to normalize XML."""

    def __init__(self) -> None:
        """
        Initialize the parser.
        """
        self.lowercase = True
        super().__init__(lowercase=self.lowercase)

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
        self.doc.append(utils.get_open_tag_html(tag))

    def on_close_tag(self, tag_name) -> None:
        """
        Handle close tag event.

        Args:
            tag_name: Name of tag to close
        """
        tag = self.tags.pop()

        if tag["name"] != tag_name:
            raise Exception(f'Unmatched tags: {tag["name"]} !== {tag_name}')

        self.doc.append(utils.get_close_tag_html(tag))

    def on_text(self, text: str) -> None:
        """
        Handle text event.

        Args:
            text: Text content
        """
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
