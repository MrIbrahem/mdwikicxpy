"""
Parser to read an HTML stream into a Doc.

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/Parser.js
"""

from __future__ import annotations

import logging
from typing import Any

from .builder import Builder
from .contextualizer import Contextualizer
from .elements import BLOCK_TAGS
from .mw_contextualizer import MwContextualizer
from .sax_html_parser import SaxHTMLParser
from .utils import Utils

logger = logging.getLogger(__name__)


class Parser:
    """Parser to read an HTML stream into a Doc."""

    def __init__(
        self,
        contextualizer: MwContextualizer | Contextualizer,
        options=None,
    ) -> None:
        """
        Initialize the parser.

        Args:
            contextualizer: Tag contextualizer
            options: Options dict
        """
        self.contextualizer = contextualizer
        self.options = options or {}
        self.lowercase = True

        sort_attrs = bool(self.options.get("sort_attrs"))
        if self.options.get("sort_attrs") is None:
            sort_attrs = True

        self.sort_attrs = sort_attrs

    def init(self) -> None:
        """
        Initialize state for parsing.
        """
        self.root_builder = Builder(sort_attrs=self.sort_attrs)
        self.builder = self.root_builder
        # Stack of tags currently open
        self.all_tags = []

    def on_open_tag(self, tag: dict[str, Any]) -> None:
        """
        Handle open tag event.

        Args:
            tag: Tag dict with 'name' and 'attributes'
        """
        # Check if the tag is an inline annotation
        is_ann = self.is_inline_annotation_tag(tag["name"], Utils.is_transclusion(tag))

        # Handle removable tags or tags in removable context
        if self.contextualizer.get_context() == "removable" or self.contextualizer.is_removable(tag):
            self.all_tags.append(tag)
            self.contextualizer.on_open_tag(tag)
            return

        # Handle segment isolation if enabled
        if self.options.get("isolateSegments") and Utils.is_segment(tag):
            # Wrap segment in a div block with specific class
            self.builder.push_block_tag({"name": "div", "attributes": {"class": "cx-segment-block"}})

        # Handle reference and math tags by creating a child builder
        if Utils.is_reference(tag) or Utils.is_math(tag):
            # Start a reference: create a child builder, and move into it
            self.builder = self.builder.create_child_builder(wrapper_tag=tag)

        # Handle inline empty tags
        elif Utils.is_inline_empty_tag(tag["name"]):
            self.builder.add_inline_content(
                content=tag,
                can_segment=self.contextualizer.can_segment(),
            )

        # Handle inline annotation tags
        elif is_ann:
            self.builder.push_inline_annotation_tag(tag)
        else:
            # Handle all other block tags
            self.builder.push_block_tag(tag)

        # Add tag to all tags list and notify contextualizer
        self.all_tags.append(tag)
        self.contextualizer.on_open_tag(tag)

    def on_close_tag(self, tag_name: str) -> None:
        """
        Handle close tag event.

        Args:
            tag_name: Name of tag to close
        """
        # If there are no tags to close, return immediately
        if not self.all_tags:
            return

        # Get the last opened tag from the stack
        tag = self.all_tags.pop()

        # Check if the tag is an inline annotation
        is_ann = self.is_inline_annotation_tag(tag_name, Utils.is_transclusion(tag))

        # Handle removable tags or tags in removable context
        if self.contextualizer.get_context() == "removable" or self.contextualizer.is_removable(tag):
            self.contextualizer.on_close_tag(tag)
            return

        # Process the tag close for non-removable tags
        self.contextualizer.on_close_tag(tag)

        # Skip processing for empty inline tags
        if Utils.is_inline_empty_tag(tag_name):
            return

        # Handle annotation tags
        if is_ann and len(self.builder.inline_annotation_tags) > 0:
            # Pop the annotation tag from the builder
            self.builder.pop_inline_annotation_tag(tag_name)
            # Handle segment isolation if enabled
            if self.options.get("isolateSegments") and Utils.is_segment(tag):
                self.builder.pop_block_tag("div")

        # Handle annotation tags in sub-documents
        elif is_ann and self.builder.builder_parent is not None:
            # In a sub document: should be a span or sup that closes a reference
            if tag_name not in ("span", "sup"):
                raise Exception(f'Expected close reference - span or sup tags, got "{tag_name}"')
            self.builder.finish_text_block()

            self.builder.builder_parent.add_inline_content(
                content=self.builder.doc,
                can_segment=self.contextualizer.can_segment(),
            )

            # Finished with child now. Move back to the parent builder
            self.builder = self.builder.builder_parent

        elif not is_ann:
            # Block level tag close
            if tag_name == "p" and self.contextualizer.can_segment():
                # Add an empty textchunk before the closing block tag to flush segmentation contexts
                # For example, transclusion based references at the end of paragraphs
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

    def is_inline_annotation_tag(self, tag_name, is_transclusion: bool) -> bool:
        """
        Determine whether a tag is an inline annotation or not.

        Args:
            tag_name: Tag name in lowercase
            is_transclusion: If the tag is transclusion

        Returns:
            Whether the tag is an inline annotation
        """
        context = self.contextualizer.get_context()

        # <span> inside a media context acts like a block tag wrapping another block tag <video>
        # See https://www.mediawiki.org/wiki/Specs/HTML/1.7.0#Audio/Video
        if tag_name == "span" and context == "media":
            return False

        # Audio or Video are block tags. But in a media-inline context they are inline
        if tag_name in ("audio", "video") and context == "media-inline":
            return True

        # Styles are usually block tags, but sometimes style tags are used as transclusions
        # Example: T217585. In such cases treat styles as inline to avoid wrong segmentations.
        if tag_name == "style" and is_transclusion:
            return True

        # All tags that are not block tags are inline annotation tags.
        return tag_name not in BLOCK_TAGS

    def write(self, html: str) -> None:
        """
        Parse HTML into the document.

        Args:
            html: HTML string to parse
        """
        parser = SaxHTMLParser(self, html)
        parser.feed(html)
        parser.close()


__all__ = [
    "Parser",
]
