"""
Utility functions for HTML processing and tag manipulation.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from . import util as cxutil
from .text_chunk import TextChunk


def find_all(text, regex, callback: Callable) -> list:
    """
    Find all matches of regex in text, calling callback with each match object.

    Args:
        text: The text to search
        regex: The regex to search
        callback: Function to call with each match

    Returns:
        The return values from the callback
    """
    boundaries = []
    for match in regex.finditer(text):
        boundary = callback(text, match)
        if boundary is not None:
            boundaries.append(boundary)
    return boundaries


def esc(s):
    """
    Escape text for inclusion in HTML, not inside a tag.

    Args:
        s: String to escape

    Returns:
        Escaped version of the string
    """
    return s.replace("&", "&#38;").replace("<", "&#60;").replace(">", "&#62;")


html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}


def esc_attr(s) -> str:
    s = str(s)
    # Replace ", ', &, <, > with their HTML numeric entities
    # return "".join(html_escape_table.get(c, c) for c in s)
    return re.sub(r'["\'&<>]', lambda m: f"&#{ord(m.group(0))};", s)


def get_open_tag_html(tag: dict[str, Any]) -> str:
    """
    Render a SAX open tag into an HTML string.

    Args:
        tag: Tag dict with 'name' and 'attributes'

    Returns:
        HTML representation of open tag
    """
    html = ["<" + esc(tag["name"])]
    attributes = sorted(tag.get("attributes", {}).keys())
    for attr in attributes:
        html.append(" " + esc(attr) + '="' + esc_attr(tag["attributes"][attr]) + '"')
    if tag.get("isSelfClosing"):
        html.append(" /")
    html.append(">")
    return "".join(html)


def get_close_tag_html(tag: dict[str, Any]) -> str:
    """
    Render a SAX close tag into an HTML string.

    Args:
        tag: Tag dict with 'name'

    Returns:
        HTML representation of close tag
    """
    if tag.get("isSelfClosing"):
        return ""
    return "</" + esc(tag["name"]) + ">"


def clone_open_tag(tag: dict[str, Any]) -> dict:
    """
    Clone a SAX open tag.

    Args:
        tag: Tag to clone

    Returns:
        Cloned tag
    """
    new_tag = {"name": tag["name"], "attributes": {}}
    for attr, value in tag.get("attributes", {}).items():
        new_tag["attributes"][attr] = value
    return new_tag


def dump_tags(tag_array: list[dict[str, Any]]) -> str:
    """
    Represent an inline tag as a single XML attribute, for debugging.

    Args:
        tag_array: Array of SAX open tags

    Returns:
        String representation of tag names
    """
    if not tag_array:
        return ""

    tag_dumps = []
    for tag in tag_array:
        attr_dumps = []
        for attr, value in tag.get("attributes", {}).items():
            attr_dumps.append(f"{attr}={esc_attr(value)}")
        tag_name = tag["name"]
        if attr_dumps:
            tag_dumps.append(f"{tag_name}:{','.join(attr_dumps)}")
        else:
            tag_dumps.append(tag_name)

    return " ".join(tag_dumps)


def is_reference(tag: dict[str, Any]) -> bool:
    """
    Detect whether this is a mediawiki reference span.

    Args:
        tag: SAX open tag object

    Returns:
        Whether the tag is a mediawiki reference span
    """
    if (tag["name"] == "span" or tag["name"] == "sup") and tag.get("attributes", {}).get(
        "typeof"
    ) == "mw:Extension/ref":
        return True
    elif tag["name"] == "sup" and tag.get("attributes", {}).get("class") == "reference":
        return True
    return False


def is_math(tag: dict[str, Any]) -> bool:
    """
    Detect whether this is a mediawiki maths span.

    Args:
        tag: SAX open tag object

    Returns:
        Whether the tag is a mediawiki math span
    """
    return (tag["name"] == "span" or tag["name"] == "sup") and tag.get("attributes", {}).get(
        "typeof"
    ) == "mw:Extension/math"


def is_gallery(tag: dict[str, Any]) -> bool:
    """
    Detect whether this is a mediawiki Gallery.

    Args:
        tag: SAX open tag object

    Returns:
        Whether the tag is a mediawiki Gallery
    """
    return tag["name"] == "ul" and tag.get("attributes", {}).get("typeof") == "mw:Extension/gallery"


def is_reference_list(tag: dict[str, Any]) -> bool:
    """Check if tag is a reference list."""
    return (
        tag["name"] == "div"
        and tag.get("attributes", {}).get("typeof") == "mw:Extension/references"
        and tag.get("attributes", {}).get("data-mw")
    )


def is_external_link(tag: dict[str, Any]) -> bool:
    """
    If a tag is MediaWiki external link or not.

    Args:
        tag: SAX open tag object

    Returns:
        Whether the tag is an external link or not
    """
    rel = tag.get("attributes", {}).get("rel", "")
    return tag["name"] == "a" and f" {rel} ".find(" mw:ExtLink ") != -1


def is_segment(tag: dict[str, Any]) -> bool:
    """
    Detect whether this is a segment.

    Args:
        tag: SAX open tag object

    Returns:
        Whether the tag is a segment or not
    """
    return tag["name"] == "span" and tag.get("attributes", {}).get("class") == "cx-segment"


def is_transclusion(tag: dict[str, Any]) -> bool:
    """Check if tag is a transclusion."""
    typeof = tag.get("attributes", {}).get("typeof", "")
    return bool(re.search(r"(^|\s)(mw:Transclusion|mw:Placeholder)\b", typeof))


def is_transclusion_fragment(tag: dict[str, Any]) -> bool:
    """Check if tag is a transclusion fragment."""
    result = cxutil.get_prop(["attributes", "about"], tag) and not cxutil.get_prop(["attributes", "data-mw"], tag)
    return result  # pyright: ignore[reportReturnType]


def is_non_translatable(tag: dict[str, Any]) -> bool:
    """
    Check if the tag need to be translated by an MT service.

    Args:
        tag: SAX open tag object

    Returns:
        Whether the tag is non-translatable
    """
    non_translatable_tags = ["style", "svg", "script"]
    non_translatable_rdfa = ["mw:Entity", "mw:Extension/math", "mw:Extension/references", "mw:Transclusion"]

    if tag["name"] in non_translatable_tags:
        return True

    if not tag.get("attributes"):
        return False

    rel = tag.get("attributes", {}).get("rel", "").split()
    typeof = tag.get("attributes", {}).get("typeof", "").split()
    rdfa = rel + typeof

    return any(ntr in rdfa for ntr in non_translatable_rdfa)


def is_inline_empty_tag(tag_name) -> bool:
    """
    Determine whether a tag is an inline empty tag.

    Args:
        tag_name: The name of the tag (lowercase)

    Returns:
        Whether the tag is an inline empty tag
    """
    inline_empty_tags = ["br", "img", "source", "track", "link", "meta"]
    return tag_name in inline_empty_tags


def get_chunk_boundary_groups(boundaries, chunks, get_length) -> list:
    """
    Find the boundaries that lie in each chunk.

    Boundaries lying between chunks lie in the latest chunk possible.
    Boundaries at the start of the first chunk, or the end of the last, are not included.

    Args:
        boundaries: Boundary offsets
        chunks: Chunks to which the boundaries apply
        get_length: Function returning the length of a chunk

    Returns:
        Array of {'chunk': ch, 'boundaries': [...]}
    """
    groups = []
    offset = 0
    boundary_ptr = 0

    # Get boundaries in order, disregarding the start of the first chunk
    boundaries = sorted(boundaries)
    while boundary_ptr < len(boundaries) and boundaries[boundary_ptr] == 0:
        boundary_ptr += 1

    for chunk in chunks:
        group_boundaries = []
        chunk_length = get_length(chunk)

        while boundary_ptr < len(boundaries):
            boundary = boundaries[boundary_ptr]
            if boundary > offset + chunk_length - 1:
                # beyond the interior of this chunk
                break
            # inside the interior of this chunk
            group_boundaries.append(boundary)
            boundary_ptr += 1

        offset += chunk_length
        groups.append({"chunk": chunk, "boundaries": group_boundaries})

    return groups


def add_common_tag(text_chunks, tag: dict[str, Any]) -> list:
    """
    Add a tag to consecutive text chunks, above common tags but below others.

    Args:
        text_chunks: Consecutive text chunks
        tag: Tag to add

    Returns:
        Copy of the text chunks with the tag inserted
    """
    if len(text_chunks) == 0:
        return []

    # Find length of common tags
    common_tags = text_chunks[0].tags[:]
    for i in range(1, len(text_chunks)):
        tags = text_chunks[i].tags
        j = 0
        for j in range(min(len(common_tags), len(tags))):
            if common_tags[j] is not tags[j]:
                break
        else:
            j += 1
        if len(common_tags) > j:
            common_tags = common_tags[:j]

    common_tag_length = len(common_tags)

    # Build new chunks with segment span inserted
    new_text_chunks = []
    for t_chunk in text_chunks:
        new_tags = t_chunk.tags[:]
        new_tags.insert(common_tag_length, tag)
        new_text_chunks.append(TextChunk(t_chunk.text, new_tags, t_chunk.inline_content))

    return new_text_chunks


def set_link_ids_in_place(text_chunks, get_next_id: Callable) -> None:
    """
    Set link IDs in-place on text chunks.

    Args:
        text_chunks: Consecutive text chunks
        get_next_id: Function accepting 'link' and returning next ID
    """
    for t_chunk in text_chunks:
        for tag in t_chunk.tags:
            if (
                tag["name"] == "a"
                and tag.get("attributes", {}).get("href") is not None
                and tag.get("attributes", {}).get("rel")
                and f" {tag['attributes']['rel']} ".find(" mw:WikiLink ") != -1
                and tag.get("attributes", {}).get("data-linkid") is None
            ):

                # Copy href, then remove it, then re-add it
                href = tag["attributes"]["href"]
                # split href before ?
                if "?" in href:
                    href = href.split("?")[0]

                tag["attributes"].pop("typeof", None)
                tag["attributes"].pop("href", None)
                tag["attributes"].pop("data-mw-i18n", None)
                tag["attributes"]["class"] = "cx-link"
                tag["attributes"]["data-linkid"] = get_next_id("link")
                tag["attributes"]["href"] = href


def is_ignorable_block(section_doc) -> bool:
    """
    Check if the passed document is a section containing block level template or reference list.

    Args:
        section_doc: Doc object

    Returns:
        Whether the section is ignorable
    """
    ignorable = False
    block_stack = []
    first_block_template = None

    # We start with index 1 since the first tag will be <section>.
    for i in range(1, len(section_doc.items)):
        item = section_doc.items[i]
        tag = item["item"]
        item_type = item["type"]

        if item_type == "open":
            block_stack.append(tag)
            if not first_block_template and (is_transclusion(tag) or is_reference_list(tag)):
                first_block_template = tag

        if item_type == "close":
            if block_stack:
                current_close_tag = block_stack.pop()
                if is_closing_template_match(block_stack, first_block_template, current_close_tag):
                    return True

        # Also check for textblocks
        if not first_block_template and item_type == "textblock":
            root_item = item["item"].get_root_item()
            if root_item and is_non_translatable(root_item):
                first_block_template = root_item
                ignorable = True
            else:
                # There is non ignorable content to translate
                return False

    return ignorable


def is_closing_template_match(
    block_stack: list[Any],
    first_block_template: dict[str, Any] | None,
    current_close_tag: Any,
) -> bool:
    first_block_about = first_block_template.get("attributes", {}).get("about") if first_block_template else None
    return (
        current_close_tag
        and len(block_stack) == 0
        and (
            (
                is_transclusion(current_close_tag)
                and current_close_tag.get("attributes", {}).get("about") == first_block_about
            )
            or is_reference_list(current_close_tag)
        )
    )


__all__ = [
    "find_all",
    "esc",
    "esc_attr",
    "get_open_tag_html",
    "get_close_tag_html",
    "clone_open_tag",
    "dump_tags",
    "is_reference",
    "is_math",
    "is_gallery",
    "is_reference_list",
    "is_external_link",
    "is_segment",
    "is_transclusion",
    "is_transclusion_fragment",
    "is_non_translatable",
    "is_inline_empty_tag",
    "get_chunk_boundary_groups",
    "add_common_tag",
    "set_link_ids_in_place",
    "is_ignorable_block",
]
