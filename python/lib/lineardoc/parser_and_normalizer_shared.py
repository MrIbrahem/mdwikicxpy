"""
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Any

from lxml import etree, html as lxml_html


logger = logging.getLogger(__name__)

# HTML void elements that cannot have content and should be self-closing
VOID_ELEMENTS = [
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
]


class SharedParserNormalizer(ABC):
    """Parser to read an HTML stream into a Doc."""

    def __init__(self, lowercase: bool = False) -> None:
        self.lowercase = lowercase

    def write(self, html: str) -> None:
        """
        Parse and normalize HTML.

        Args:
            html: HTML string to normalize
        """
        parser = etree.HTMLParser(encoding="utf-8")
        tree = etree.fromstring(html, parser)
        self._process_element(tree)

    def write_z(self, html: str) -> None:
        """
        Parse and normalize HTML.

        Args:
            html: HTML string to normalize
        """
        parser = etree.HTMLParser(encoding="utf-8")

        try:
            tree = etree.fromstring(html, parser)
            self._process_element(tree)
        except Exception as exc:
            logger.error("Failed to parse HTML error: %s", str(exc))
            # Try with wrapping
            try:
                tree = etree.fromstring(f"<div>{html}</div>", parser)
                for child in tree:
                    self._process_element(child)
            except Exception as e:
                raise Exception(f"Failed to parse HTML: {e}") from e

    def write_lxml_html(self, html: str) -> None:
        """
        Parse HTML into the document.

        Uses ``lxml.html.fragments_fromstring`` so that HTML *fragments* (such as
        a bare ``<p>…</p>``) are parsed without the implicit ``<html><body>``
        wrapper that ``etree.HTMLParser`` would inject. This keeps the behaviour
        consistent with the upstream (sax-based) parser, which only emits the
        elements actually present in the input.
        """
        try:
            fragments = lxml_html.fragments_fromstring(html)
        except Exception as exc:
            # Fallback: wrap in a div and try again
            try:
                fragments = lxml_html.fragments_fromstring(f"<div>{html}</div>")
            except Exception as exc2:
                raise Exception(f"Failed to parse HTML: {exc2}") from exc2

        for fragment in fragments:
            if isinstance(fragment, str):
                # Leading/trailing text outside any tag (e.g. before the first tag)
                if fragment.strip():
                    self.on_text(fragment)
                continue
            self._process_element(fragment)

    def _process_element(self, element: etree.Element | Any) -> None:
        """
        Process an element and its children recursively.
        """
        # Skip comments and other special nodes
        if element is None:
            return

        # Create tag dict
        tag_name = element.tag
        if self.lowercase:
            tag_name = str(tag_name).lower()

        # Create tag dict
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

    @abstractmethod
    def on_open_tag(self, tag: dict[str, Any]) -> None:
        """
        Handle open tag event.

        Args:
            tag: Tag dict with 'name' and 'attributes'
        """
        ...

    @abstractmethod
    def on_close_tag(self, tag_name) -> None:
        """
        Handle close tag event.

        Args:
            tag_name: Name of tag to close
        """
        ...

    @abstractmethod
    def on_text(self, text: str) -> None:
        """
        Handle text event.

        Args:
            text: Text content
        """
        ...

__all__ = [
    "SharedParserNormalizer",
]
