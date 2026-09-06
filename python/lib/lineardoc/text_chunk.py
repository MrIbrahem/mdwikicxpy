"""
text_chunk - A chunk of uniformly-annotated inline text

The annotations consist of a list of inline tags (<a>, <i> etc), and an
optional "inline element" (br/img tag, or a sub-document e.g. for a
reference span). The tags and/or reference apply to the whole text;
therefore text with varying markup must be split into multiple chunks.

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/TextChunk.js
"""

from __future__ import annotations

from typing import Any


class TextChunk:
    """A chunk of uniformly-annotated inline text."""

    def __init__(
        self,
        text: str,
        tags: list[dict[str, Any]],
        *,
        inline_content: Any | dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize a text_chunk.

        Args:
            text: Plaintext in the chunk (can be '')
            tags: Array of SAX open tag objects, for the applicable tags
            inline_content: Tag or sub-doc (optional)
        """
        self.text = text
        self.tags = tags
        self.inline_content = inline_content

        from .utils import Utils

        self.utils = Utils

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return self.text

    def get_inline_content_html(self, sort_attrs: bool = True):
        html = []
        from .doc import Doc

        # if hasattr(self.inline_content, "get_html"):
        if isinstance(self.inline_content, Doc):
            # a sub-doc
            html.append(self.inline_content.get_html())

        elif isinstance(self.inline_content, dict):
            # an empty inline tag
            html.append(self.utils.get_open_tag_html(self.inline_content, sort_attrs=sort_attrs))
            html.append(self.utils.get_close_tag_html(self.inline_content))
        else:
            raise ValueError("inline_content must be a Doc or dict")
        return html

    def generate_xml_chunk(self, pad: str = "") -> list[str]:
        chunk_dump = []
        tags_dump = self.dump_tags()
        tags_attr = f' tags="{tags_dump}"' if tags_dump else ""

        if self.text:
            formatted_text_chunk = self.utils.esc(self.text).replace("\n", "&#10;")
            chunk_dump.append(f"{pad}<cxtextchunk{tags_attr}>" + formatted_text_chunk + "</cxtextchunk>")

        if self.inline_content:
            chunk_dump.append(f"{pad}<cxinlineelement{tags_attr}>")
            from .doc import Doc

            if isinstance(self.inline_content, Doc):
                # sub-doc: concatenate
                chunk_dump.extend(self.inline_content.dump_xml_array(pad + "  "))
            elif isinstance(self.inline_content, dict):
                chunk_dump.append(f'{pad}  <{self.inline_content["name"]}/>')
            else:
                raise ValueError("inline_content must be a Doc or dict")

            chunk_dump.append(f"{pad}</cxinlineelement>")

        return chunk_dump

    def dump_tags(self) -> str:
        """
        Represent an inline tag as a single XML attribute, for debugging.

        Args:
            tag_array: Array of SAX open tags

        Returns:
            String representation of tag names
        """
        if not self.tags:
            return ""

        tag_dumps = []
        for tag in self.tags:
            attr_dumps = []
            for attr, value in tag.get("attributes", {}).items():
                attr_dumps.append(f"{attr}={self.utils.esc_attr(value)}")
            tag_name = tag["name"]
            if attr_dumps:
                tag_dumps.append(f"{tag_name}:{','.join(attr_dumps)}")
            else:
                tag_dumps.append(tag_name)

        return " ".join(tag_dumps)


__all__ = [
    "TextChunk",
]
