"""
text_block - A block of annotated inline text.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from . import utils
from .text_chunk import TextChunk


class TextBlock:
    """A block of annotated inline text."""

    def __init__(self, text_chunks: list[TextChunk], can_segment: bool = True) -> None:
        """
        Initialize a text_block.

        Args:
            text_chunks: Annotated inline text
            can_segment: This is a block which can be segmented
        """
        self.text_chunks = text_chunks
        self.can_segment = can_segment
        self.offsets = []

        cursor = 0
        for t_chunk in self.text_chunks:
            self.offsets.append({"start": cursor, "length": len(t_chunk.text), "tags": t_chunk.tags})
            cursor += len(t_chunk.text)

    def get_tag_offsets(self) -> list:
        """
        Get the start and length of each non-common annotation.

        Returns:
            Array of offset dicts
        """
        common_tags = self.get_common_tags()
        result = []
        for i, offset in enumerate(self.offsets):
            t_chunk = self.text_chunks[i]
            if len(t_chunk.tags) > len(common_tags) and len(t_chunk.text) > 0:
                result.append(offset)
        return result

    def get_text_chunk_at(self, char_offset) -> TextChunk:
        """
        Get the (last) text chunk at a given char offset.

        Args:
            char_offset: The char offset of the t_chunk

        Returns:
            The text chunk
        """
        i = 0
        for i in range(len(self.text_chunks) - 1):
            if self.offsets[i + 1]["start"] > char_offset:
                break

        return self.text_chunks[i]

    def get_common_tags(self) -> list:
        """
        Returns the list of SAX tags that apply to the whole text block.

        Returns:
            List of common SAX tags
        """
        if len(self.text_chunks) == 0:
            return []

        common_tags = self.text_chunks[0].tags[:]
        for t_chunk in self.text_chunks:
            tags = t_chunk.tags
            if len(tags) < len(common_tags):
                common_tags = common_tags[: len(tags)]

            for j in range(len(common_tags)):
                if common_tags[j]["name"] != tags[j]["name"]:
                    common_tags = common_tags[:j]
                    break

        return common_tags

    def translate_tags(self, target_text: str, range_mappings) -> TextBlock:
        """
        Create a new text_block, applying our annotations to a translation.

        Args:
            target_text: Translated plain text
            range_mappings: Array of source-target range index mappings

        Returns:
            Translated textblock with tags applied
        """
        # map of { offset: x, text_chunks: [...] }
        empty_text_chunks = {}
        empty_text_chunk_offsets = []
        # list of { start: x, length: x, t_chunk: x }
        text_chunks = []

        def push_empty_text_chunks(offset, chunks):
            for chunk in chunks:
                text_chunks.append({"start": offset, "length": 0, "t_chunk": chunk})

        # Create map of empty text chunks, by offset
        for i, t_chunk in enumerate(self.text_chunks):
            offset = self.offsets[i]["start"]
            if len(t_chunk.text) > 0:
                continue
            if offset not in empty_text_chunks:
                empty_text_chunks[offset] = []
            empty_text_chunks[offset].append(t_chunk)

        empty_text_chunk_offsets = sorted(empty_text_chunks.keys())

        for range_mapping in range_mappings:
            # Copy tags from source text start offset
            source_range_end = range_mapping["source"]["start"] + range_mapping["source"]["length"]
            target_range_end = range_mapping["target"]["start"] + range_mapping["target"]["length"]
            source_text_chunk = self.get_text_chunk_at(range_mapping["source"]["start"])
            text = target_text[range_mapping["target"]["start"] : target_range_end]
            text_chunks.append(
                {
                    "start": range_mapping["target"]["start"],
                    "length": range_mapping["target"]["length"],
                    "text_chunk": TextChunk(text, source_text_chunk.tags, source_text_chunk.inline_content),
                }
            )

            # Empty source text chunks will not be represented in the target plaintext
            j = 0
            while j < len(empty_text_chunk_offsets):
                offset = empty_text_chunk_offsets[j]
                # Check whether chunk is in range
                if offset < range_mapping["source"]["start"] or offset > source_range_end:
                    j += 1
                    continue
                # Push chunk into target text at the current point
                push_empty_text_chunks(target_range_end, empty_text_chunks[offset])
                # Remove chunk from remaining list
                del empty_text_chunks[offset]
                empty_text_chunk_offsets.pop(j)

        # Sort by start position
        text_chunks.sort(key=lambda x: x["start"])

        # Fill in any t_chunk gaps using text with common_tags
        pos = 0
        common_tags = self.get_common_tags()
        i = 0
        while i < len(text_chunks):
            t_chunk = text_chunks[i]
            if t_chunk["start"] < pos:
                raise Exception(f"Overlapping chunks at pos={pos}, text_chunks={i} start={t_chunk['start']}")
            elif t_chunk["start"] > pos:
                # Unmapped chunk: insert plaintext and adjust offset
                text_chunks.insert(
                    i,
                    {
                        "start": pos,
                        "length": t_chunk["start"] - pos,
                        "text_chunk": TextChunk(target_text[pos : t_chunk["start"]], common_tags),
                    },
                )
                i += 1
            pos = t_chunk["start"] + t_chunk["length"]
            i += 1

        # Get trailing text and trailing whitespace
        tail = target_text[pos:]
        import re

        tail_space_match = re.search(r"\s*$", tail)
        tail_space = tail_space_match.group(0) if tail_space_match else ""
        if tail_space:
            tail = tail[: -len(tail_space)]

        if tail:
            # Append tail as text with common_tags
            text_chunks.append({"start": pos, "length": len(tail), "text_chunk": TextChunk(tail, common_tags)})
            pos += len(tail)

        # Copy any remaining text_chunks that have no text
        for offset in empty_text_chunk_offsets:
            push_empty_text_chunks(pos, empty_text_chunks[offset])

        if tail_space:
            # Append tail_space as text with common_tags
            text_chunks.append(
                {"start": pos, "length": len(tail_space), "text_chunk": TextChunk(tail_space, common_tags)}
            )

        return TextBlock([x["text_chunk"] for x in text_chunks])

    def get_plain_text(self) -> str:
        """
        Return plain text representation of the text block.

        Returns:
            Plain text representation
        """
        return "".join(chunk.text for chunk in self.text_chunks)

    def get_html(self) -> str:
        """
        Return HTML representation of the text block.

        Returns:
            HTML representation
        """
        html = []
        # Start with no tags open
        old_tags = []

        for t_chunk in self.text_chunks:
            # Compare tag stacks; render close tags and open tags as necessary
            # Find the highest offset up to which the tags match
            match_top = -1
            min_length = min(len(old_tags), len(t_chunk.tags))
            for j in range(min_length):
                if old_tags[j] is t_chunk.tags[j]:
                    match_top = j
                else:
                    break

            for j in range(len(old_tags) - 1, match_top, -1):
                html.append(utils.get_close_tag_html(old_tags[j]))

            for j in range(match_top + 1, len(t_chunk.tags)):
                html.append(utils.get_open_tag_html(t_chunk.tags[j]))

            old_tags = t_chunk.tags

            # Now add text and inline content
            html.append(utils.esc(t_chunk.text))
            if t_chunk.inline_content:
                if hasattr(t_chunk.inline_content, "get_html"):
                    # a sub-doc
                    html.append(t_chunk.inline_content.get_html())
                else:
                    # an empty inline tag
                    html.append(utils.get_open_tag_html(t_chunk.inline_content))
                    html.append(utils.get_close_tag_html(t_chunk.inline_content))

        # Finally, close any remaining tags
        for j in range(len(old_tags) - 1, -1, -1):
            html.append(utils.get_close_tag_html(old_tags[j]))

        return "".join(html)

    def get_root_item(self) -> None | dict[str, Any]:
        """
        Get a root item in the textblock.

        Returns:
            Root item or None
        """
        for t_chunk in self.text_chunks:
            if len(t_chunk.tags) == 0 and t_chunk.text and re.search(r"[^\s]", t_chunk.text):
                # No tags in this textchunk. See if there is non whitespace text
                return None

            for tag in t_chunk.tags:
                if tag:
                    return tag

            if t_chunk.inline_content:
                inline_doc = t_chunk.inline_content
                # Presence of get_root_item confirms that inline_doc is a Doc instance
                if hasattr(inline_doc, "get_root_item"):
                    root_item = inline_doc.get_root_item()
                    return root_item or None
                else:
                    return inline_doc

        return None

    def get_tag_for_id(self) -> None | dict[str, Any]:
        """
        Get a tag that can represent this textblock.

        Returns:
            Tag object
        """
        return self.get_root_item()

    def segment(self, get_boundaries: Callable, get_next_id: Callable) -> TextBlock:
        """
        Segment the text block into sentences.

        Args:
            get_boundaries: Function taking plaintext, returning offset array
            get_next_id: Function taking 'segment'|'link', returning next ID

        Returns:
            Segmented version, with added span tags
        """
        # Setup: current_text_chunks for current segment, and all_text_chunks for all segments
        all_text_chunks = []
        current_text_chunks = []

        def flush_chunks():
            if len(current_text_chunks) == 0:
                return

            modified_text_chunks = utils.add_common_tag(
                current_text_chunks,
                {"name": "span", "attributes": {"class": "cx-segment", "data-segmentid": get_next_id("segment")}},
            )
            utils.set_link_ids_in_place(modified_text_chunks, get_next_id)
            all_text_chunks.extend(modified_text_chunks)
            current_text_chunks.clear()

        root_item = self.get_root_item()
        if root_item and utils.is_transclusion(root_item):
            # Avoid segmenting inside transclusions
            return self

        # for each chunk, split at any boundaries that occur inside the chunk
        groups = utils.get_chunk_boundary_groups(
            get_boundaries(self.get_plain_text()),
            self.text_chunks,
            lambda t_chunk: len(t_chunk.text),
        )

        offset = 0
        for group in groups:
            t_chunk = group["chunk"]
            boundaries = group["boundaries"]

            for boundary in boundaries:
                rel_offset = boundary - offset
                if rel_offset == 0:
                    flush_chunks()
                else:
                    left_part = TextChunk(t_chunk.text[:rel_offset], t_chunk.tags[:])
                    right_part = TextChunk(t_chunk.text[rel_offset:], t_chunk.tags[:], t_chunk.inline_content)
                    current_text_chunks.append(left_part)
                    offset += rel_offset
                    flush_chunks()
                    t_chunk = right_part

            # Even if the t_chunk is zero-width, it may have references
            current_text_chunks.append(t_chunk)
            offset += len(t_chunk.text)

        flush_chunks()
        return TextBlock(all_text_chunks)

    def set_link_ids(self, get_next_id: Callable) -> TextBlock:
        """
        Set the link Ids for the links in all the textchunks in the textblock instance.

        Args:
            get_next_id: Function taking 'segment'|'link', returning next ID

        Returns:
            Self with link IDs set
        """
        utils.set_link_ids_in_place(self.text_chunks, get_next_id)
        return self

    def dump_xml_array(self, pad: str) -> list:
        """
        Dump an XML Array version of the linear representation, for debugging.

        Args:
            pad: Whitespace to indent XML elements

        Returns:
            Array that will concatenate to an XML string representation
        """
        dump = []
        for chunk in self.text_chunks:
            tags_dump = utils.dump_tags(chunk.tags)
            tags_attr = f' tags="{tags_dump}"' if tags_dump else ""

            if chunk.text:
                dump.append(
                    f"{pad}<cxtextchunk{tags_attr}>" + utils.esc(chunk.text).replace("\n", "&#10;") + "</cxtextchunk>"
                )

            if chunk.inline_content:
                dump.append(f"{pad}<cxinlineelement{tags_attr}>")
                if hasattr(chunk.inline_content, "dump_xml_array"):
                    # sub-doc: concatenate
                    dump.extend(chunk.inline_content.dump_xml_array(pad + "  "))
                else:
                    dump.append(f'{pad}  <{chunk.inline_content["name"]}/>')
                dump.append(f"{pad}</cxinlineelement>")

        return dump


__all__ = [
    "TextBlock",
]
