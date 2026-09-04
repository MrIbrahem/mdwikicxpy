"""
Functions for working with text chunks in the LinearDoc library.

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/TextBlock.js
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from . import utils
from .text_chunk import TextChunk

# Placeholder characters used when a text block is flattened to a plain
# string. These are Unicode noncharacters (U+FDD0 and U+FDD1), guaranteed
# absent from interchanged text.
REF_CHAR = "\ufdd0"
INLINE_CHAR = "\ufdd1"


def is_reference_chunk(chunk: TextChunk) -> bool:
    """
    Whether the text chunk represents a reference marker.

    Args:
        chunk: The text chunk to check

    Returns:
        True if reference marker, False otherwise
    """
    inline = chunk.inline_content
    if inline and getattr(inline, "wrapper_tag", None):
        wrapper_tag = inline.wrapper_tag
        if getattr(wrapper_tag, "attributes", None) and utils.is_reference(wrapper_tag):
            return True

    return any(tag.get("attributes") and utils.is_reference(tag) for tag in chunk.tags)


def to_char_items(chunks: list[TextChunk]) -> list[dict[str, Any]]:
    """
    Flatten chunks into one item per string position. Reference markers and
    other inline content become a single placeholder item; text chunks
    contribute one item per code unit, each remembering its source chunk.
    The concatenated chars form the plain text of the block, so rules matched
    against it do not depend on how the text is split into chunks.

    Args:
        chunks: list[TextChunk] List of TextChunk objects

    Returns:
        List of item dicts of shape { "char": str, "chunk": TextChunk, "atomic": bool }
    """
    items = []
    for chunk in chunks:
        if is_reference_chunk(chunk):
            items.append({"char": REF_CHAR, "chunk": chunk, "atomic": True})
        elif chunk.inline_content:
            items.append({"char": INLINE_CHAR, "chunk": chunk, "atomic": True})
        else:
            for char in chunk.text:
                items.append({"char": char, "chunk": chunk, "atomic": False})
    return items


def to_chunks(items: list[dict[str, Any]]) -> list[TextChunk]:
    """
    Rebuild a chunk list from (reordered) flattened items. Atomic items emit
    their original chunk; consecutive characters from the same source chunk
    merge back into a single chunk. Source tags arrays are reused by
    reference, which keeps the serialized markup of untouched regions
    byte-identical.

    Args:
        items: list[dict] Items produced by to_char_items

    Returns:
        list[TextChunk] New chunk list
    """
    chunks = []
    text = ""
    source = None

    def flush():
        nonlocal text, source
        if text != "":
            tags = getattr(source, "tags", [])
            chunks.append(TextChunk(text, tags))
            text = ""

    for item in items:
        if item.get("atomic"):
            flush()
            source = None
            chunks.append(item["chunk"])
        elif item["chunk"] is source:
            text += item["char"]
        else:
            flush()
            source = item["chunk"]
            text = item["char"]

    flush()
    return chunks


def escape_for_char_class(char: str) -> str:
    """
    Escape a character for use inside a regex character class.

    Args:
        char: Character to escape

    Returns:
        Escaped character string
    """
    return re.sub(r"[\\\]^-]", r"\\\g<0>", char)


def move_punctuation_across_references(chunks: list[TextChunk], policy: str, punctuation: list[str]) -> list[TextChunk]:
    """
    Move sentence punctuation across reference runs to the side preferred by
    the target language. The block is flattened to a plain string in which
    every reference marker is a single placeholder character, so the rule is
    one regex over the visible text, independent of chunk boundaries. The
    whitespace that separated the word, punctuation and references is dropped
    so that the three stay glued together; whitespace between the references
    of a run is preserved.

    Args:
        chunks: list[TextChunk] List of text chunks
        policy: 'before' or 'after'
        punctuation: list[str] Punctuation marks to reposition around

    Returns:
        list[TextChunk] New chunk list
    """
    items = to_char_items(chunks)
    text = "".join(item["char"] for item in items)
    punct = "([" + "".join(escape_for_char_class(p) for p in punctuation) + "])"
    # run = f"({re.escape(REF_CHAR)}(?:\\s*{re.escape(REF_CHAR)})*)"
    run = f"({REF_CHAR}(?:\\s*{REF_CHAR})*)"
    if policy == "before":
        pattern = re.compile(f"{punct}\\s*{run}")
    else:
        pattern = re.compile(f"\\s*{run}\\s*{punct}")

    reordered = []
    position = 0

    for match in pattern.finditer(text):
        if policy == "before":
            run_start, run_end = match.span(2)
        else:
            run_start, run_end = match.span(1)
        run_items = items[run_start:run_end]

        # The moved punctuation inherits the reference tags (e.g. the segment
        # span) so it stays inside the same markup as the reference run.
        punct_char = match.group(1) if policy == "before" else match.group(2)
        punct_item = {
            "char": punct_char,
            "chunk": TextChunk("", run_items[-1]["chunk"].tags),
        }

        reordered.extend(items[position : match.start()])
        if policy == "before":
            reordered.extend(run_items)
            reordered.append(punct_item)
        else:
            reordered.append(punct_item)
            reordered.extend(run_items)

        position = match.end()

    reordered.extend(items[position:])
    return to_chunks(reordered)


def get_chunk_about_values(chunk: TextChunk) -> list[str]:
    """
    Get the values of the "about" attribute of a text chunk.

    The values come from the annotation tags of the chunk and from its
    inline content. Inline content is not always a tag: for references it
    is a sub-document with no attributes property. Read attributes only
    when they are present.

    Args:
        chunk: The text chunk to process

    Returns:
        list[str] The about values; can be empty
    """
    values = []
    for tag in chunk.tags:
        attributes = tag.get("attributes") if isinstance(tag, dict) else getattr(tag, "attributes", None)
        if attributes and isinstance(attributes, dict) and "about" in attributes:
            values.append(attributes["about"])

    inline = chunk.inline_content
    if inline:
        attributes = inline.get("attributes") if isinstance(inline, dict) else getattr(inline, "attributes", None)
        if attributes and isinstance(attributes, dict) and "about" in attributes:
            values.append(attributes["about"])

    return values


def suppress_about_group_boundaries(boundaries: list[int], text_chunks: list[TextChunk]) -> list[int]:
    """
    Remove sentence boundaries that fall inside a transclusion about-group.

    Parsoid puts an inline transclusion into sibling elements that share one
    "about" attribute. These siblings must stay together. A sentence boundary
    between them would put the fragments into different segments and thus
    into different parent elements (T213262). A boundary is inside a group
    when the chunks on the two sides of it share an about value. The run
    before the boundary includes zero-width chunks, such as category links.

    Args:
        boundaries: list[int] Sentence boundary offsets
        text_chunks: list[TextChunk] The chunks of the text block

    Returns:
        list[int] The boundaries that do not break an about-group
    """
    starts = []
    offset = 0
    for chunk in text_chunks:
        starts.append(offset)
        offset += len(chunk.text)

    def keep(boundary):
        # Find the first chunk with content at or after the boundary.
        # Zero-width chunks at the boundary belong to the run before it.
        i = 0
        length = len(text_chunks)
        while i < length and starts[i] + len(text_chunks[i].text) <= boundary:
            i += 1
        if i == length:
            return True

        after_abouts = get_chunk_about_values(text_chunks[i])
        if len(after_abouts) == 0:
            return True

        if starts[i] < boundary:
            # The boundary is in the interior of a chunk that carries an
            # about value: the two sides share it.
            return False

        before_abouts = []
        j = i - 1
        while j >= 0:
            before_abouts.extend(get_chunk_about_values(text_chunks[j]))
            if len(text_chunks[j].text) > 0:
                break
            j -= 1

        return not any(about in before_abouts for about in after_abouts)

    return [b for b in boundaries if keep(b)]


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
        valid_boundaries = suppress_about_group_boundaries(get_boundaries(self.get_plain_text()), self.text_chunks)
        groups = utils.get_chunk_boundary_groups(
            valid_boundaries,
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
    "is_reference_chunk",
    "to_char_items",
    "to_chunks",
    "escape_for_char_class",
    "move_punctuation_across_references",
    "get_chunk_about_values",
    "suppress_about_group_boundaries",
]
