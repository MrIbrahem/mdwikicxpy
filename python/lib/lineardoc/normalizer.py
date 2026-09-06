"""
Normalizer - Parser to normalize XML.

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/Normalizer.js
"""

from __future__ import annotations

import logging
import re
from typing import Any

from lxml import etree

from .elements import VOID_ELEMENTS
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

    def write(self, html: str) -> None:
        """
        Parse and normalize HTML.

        Args:
            html: HTML string to normalize
        """
        parser = etree.HTMLParser(encoding="utf-8")
        try:
            root = etree.fromstring(html, parser)
            self._process_element(root)
        except Exception as exc:
            logger.error("Failed to parse HTML error: %s", str(exc))
            # Try with wrapping
            try:
                root = etree.fromstring(f"<div>{html}</div>", parser)
                for child in root:
                    self._process_element(child)
            except Exception as e:
                raise Exception(f"Failed to parse HTML: {e}") from e

    def _process_element(self, element: etree._Element | Any, tag_name: str | None = None) -> None:
        """
        Process an element and its children recursively.
        """
        if element is None:
            return

        if tag_name is None:
            tag_name = element.tag  # pyright: ignore[reportAssignmentType]

        if tag_name and self.lowercase:
            tag_name = tag_name.lower()

        # Create tag dict
        tag = {"name": tag_name, "attributes": dict(element.attrib)}

        # Mark HTML void elements as self-closing
        tag["isSelfClosing"] = tag_name in VOID_ELEMENTS

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

        self.on_close_tag(tag_name)  # pyright: ignore[reportArgumentType]

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

    def get_html(self) -> str:
        """
        Get the normalized HTML.

        Returns:
            Normalized HTML string
        """
        return "".join(self.doc)


def normalize(html: str, sort_attrs: bool = True) -> str:
    """
    Normalize HTML by parsing and re-serializing.

    Args:
        html: HTML string to normalize

    Returns:
        Normalized HTML string
    """
    html = html.strip()
    normalizer = Normalizer(sort_attrs=sort_attrs)
    normalizer.init()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", "", html)
    normalizer.write(html)
    return normalizer.get_html()


__all__ = [
    "Normalizer",
    "normalize",
]
