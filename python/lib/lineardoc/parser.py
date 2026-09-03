"""
Parser to read an HTML stream into a Doc.

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/Parser.js
"""

from __future__ import annotations
import logging
from typing import Any

from . import utils
from .builder import Builder

from .parser_and_normalizer_shared import SharedParserNormalizer
logger = logging.getLogger(__name__)

BLOCK_TAGS = [
    "html",
    "head",
    "body",
    "script",
    # head tags
    # In HTML5+RDFa, link/meta are actually allowed anywhere in the body, and are to be
    # treated as void flow content (like <br> and <img>).
    "title",
    "style",
    "meta",
    "link",
    "noscript",
    "base",
    # non-visual content
    "audio",
    "data",
    "datagrid",
    "datalist",
    "dialog",
    "eventsource",
    "form",
    "iframe",
    "main",
    "menu",
    "menuitem",
    "optgroup",
    "option",
    # paragraph
    "div",
    "p",
    # tables
    "table",
    "tbody",
    "thead",
    "tfoot",
    "caption",
    "th",
    "tr",
    "td",
    # lists
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    # HTML5 heading content
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hgroup",
    # HTML5 sectioning content
    "article",
    "aside",
    "body",
    "nav",
    "section",
    "footer",
    "header",
    "figure",
    "figcaption",
    "fieldset",
    "details",
    "blockquote",
    "address",  # added by Giovanni Toffoli
    # other
    "hr",
    "button",
    "canvas",
    "center",
    "col",
    "colgroup",
    "embed",
    "map",
    "object",
    "pre",
    "progress",
    "video",
    # non-annotation inline tags
    "img",
    "br",
]

class Parser(SharedParserNormalizer):
    """Parser to read an HTML stream into a Doc."""

    def __init__(self, contextualizer, options=None) -> None:
        """
        Initialize the parser.

        Args:
            contextualizer: Tag contextualizer
            options: Options dict
        """
        self.contextualizer = contextualizer
        self.options = options or {}
        self.lowercase = True
        super().__init__(lowercase=self.lowercase)

    def init(self) -> None:
        """
        Initialize state for parsing.
        """
        self.root_builder = Builder()
        self.builder = self.root_builder
        # Stack of tags currently open
        self.all_tags = []

    def write_z(self, html: str) -> None:
        """
        Parse and normalize HTML.

        Args:
            html: HTML string to normalize
        """
        return self.write_lxml_html(html)

    def on_open_tag(self, tag: dict[str, Any]) -> None:
        """
        Handle open tag event.

        Args:
            tag: Tag dict with 'name' and 'attributes'
        """
        if self.contextualizer.get_context() == "removable" or self.contextualizer.is_removable(tag):
            self.all_tags.append(tag)
            self.contextualizer.on_open_tag(tag)
            return

        if self.options.get("isolateSegments") and utils.is_segment(tag):
            self.builder.push_block_tag({"name": "div", "attributes": {"class": "cx-segment-block"}})

        if utils.is_reference(tag) or utils.is_math(tag):
            # Start a reference: create a child builder, and move into it
            self.builder = self.builder.create_child_builder(tag)

        elif utils.is_inline_empty_tag(tag["name"]):
            self.builder.add_inline_content(tag, self.contextualizer.can_segment())

        elif self.is_inline_annotation_tag(tag["name"], utils.is_transclusion(tag)):
            self.builder.push_inline_annotation_tag(tag)
        else:
            self.builder.push_block_tag(tag)

        self.all_tags.append(tag)
        self.contextualizer.on_open_tag(tag)

    def on_close_tag(self, tag_name) -> None:
        """
        Handle close tag event.

        Args:
            tag_name: Name of tag to close
        """
        if not self.all_tags:
            return

        tag = self.all_tags.pop()
        is_ann = self.is_inline_annotation_tag(tag_name, utils.is_transclusion(tag))

        if self.contextualizer.is_removable(tag) or self.contextualizer.get_context() == "removable":
            self.contextualizer.on_close_tag(tag)
            return

        self.contextualizer.on_close_tag(tag)

        if utils.is_inline_empty_tag(tag_name):
            return
        elif is_ann and len(self.builder.inline_annotation_tags) > 0:
            self.builder.pop_inline_annotation_tag(tag_name)
            if self.options.get("isolateSegments") and utils.is_segment(tag):
                self.builder.pop_block_tag("div")
        elif is_ann and self.builder.parent is not None:
            # In a sub document: should be a span or sup that closes a reference
            if tag_name not in ("span", "sup"):
                raise Exception(f'Expected close reference - span or sup tags, got "{tag_name}"')
            self.builder.finish_text_block()
            self.builder.parent.add_inline_content(self.builder.doc, self.contextualizer.can_segment())
            # Finished with child now. Move back to the parent builder
            self.builder = self.builder.parent
        elif not is_ann:
            # Block level tag close
            if tag_name == "p" and self.contextualizer.can_segment():
                # Add an empty textchunk before the closing block tag
                self.builder.add_text_chunk("", self.contextualizer.can_segment())
            self.builder.pop_block_tag(tag_name)
        else:
            raise Exception(f"Unexpected close tag: {tag_name}")

    def on_text(self, text: str) -> None:
        """
        Handle text event.

        Args:
            text: Text content
        """
        if self.contextualizer.get_context() == "removable":
            return
        self.builder.add_text_chunk(text, self.contextualizer.can_segment())

    def on_script(self, text: str) -> None:
        """Handle script text."""
        self.builder.add_text_chunk(text, self.contextualizer.can_segment())

    def is_inline_annotation_tag(self, tag_name, is_transclusion) -> bool:
        """
        Determine whether a tag is an inline annotation or not.

        Args:
            tag_name: Tag name in lowercase
            is_transclusion: If the tag is transclusion

        Returns:
            Whether the tag is an inline annotation
        """
        context = self.contextualizer.get_context()

        # <span> inside a media context acts like a block tag
        if tag_name == "span" and context == "media":
            return False

        # Audio or Video are block tags. But in a media-inline context they are inline
        if tag_name in ("audio", "video") and context == "media-inline":
            return True

        # Styles are usually block tags, but sometimes style tags are used as transclusions
        if tag_name == "style" and is_transclusion:
            return True

        # All tags that are not block tags are inline annotation tags
        return tag_name not in BLOCK_TAGS


__all__ = [
    "Parser",
]
