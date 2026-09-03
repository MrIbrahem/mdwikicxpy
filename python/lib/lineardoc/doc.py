"""
Doc - An HTML document in linear representation.

The document is a list of items, where each item is:
- a block open tag (e.g. <p>); or
- a block close tag (e.g. </p>); or
- a text_block of annotated inline text; or
- "block whitespace" (a run of whitespace separating two block boundaries)
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from . import util as cxutil
from . import utils
from .text_block import TextBlock


class Doc:
    """An HTML document in linear representation."""

    def __init__(self, wrapper_tag=None) -> None:
        """
        Initialize a Doc.

        Args:
            wrapper_tag: Open/close tags
        """
        self.items = []
        self.wrapper_tag = wrapper_tag
        self.categories = []

    def clone(self, callback: Callable) -> Doc:
        """
        Clone the Doc, modifying as we go.

        Args:
            callback: The function to modify a node

        Returns:
            Clone with modifications
        """
        new_doc = Doc(self.wrapper_tag)
        for item in self.items:
            new_item = callback(item)
            new_doc.add_item(new_item["type"], new_item["item"])
        return new_doc

    def add_item(self, item_type, item: dict[str, Any] | TextBlock | str) -> Doc:
        """
        Add an item to the document.

        Args:
            item_type: Type of item: open|close|blockspace|textblock
            item: Open/close tag, space or text block

        Returns:
            Self for chaining
        """
        self.items.append({"type": item_type, "item": item})
        return self

    def undo_add_item(self) -> None:
        """Remove the top item from the linear array of items."""
        self.items.pop()

    def get_current_item(self):
        """
        Get the top item in the linear array of items.

        Returns:
            Current item
        """
        return self.items[-1] if self.items else None

    def get_root_item(self) -> None | Any:
        """
        Get the root item in the doc.

        Returns:
            Root item
        """
        if self.wrapper_tag:
            return self.wrapper_tag

        for item in self.items:
            # Ignore all blockspaces, loop till we see a tag opening
            if item["type"] == "open":
                return item["item"]
        return None

    def segment(self, get_boundaries: Callable) -> Doc:
        """
        Segment the document into sentences.

        Args:
            get_boundaries: Function taking plaintext, returning offset array

        Returns:
            Segmented version of document
        """
        new_doc = Doc()
        next_section_id = 0
        next_id = 0
        section_number = 0

        def get_next_id(id_type, tag_name=None):
            nonlocal next_section_id, next_id, section_number
            if tag_name == "section":
                result = f"cxSourceSection{next_section_id}"
                next_section_id += 1
                return result
            if id_type in ("segment", "link", "block"):
                result = str(next_id)
                next_id += 1
                return result
            else:
                raise Exception(f"Unknown ID type: {id_type}")

        transclusion_context = None
        for i, item in enumerate(self.items):
            if item["type"] == "open":
                tag = utils.clone_open_tag(item["item"])

                if tag.get("attributes", {}).get("id"):
                    # If the item is a header, we make it a fixed length id
                    if (
                        tag["name"] in ["h1", "h2", "h3", "h4", "h5"]
                        and i + 1 < len(self.items)
                        and self.items[i + 1]["type"] == "textblock"
                    ):
                        h = hashlib.sha256()
                        h.update(self.items[i + 1]["item"].get_plain_text().encode("utf-8"))
                        tag["attributes"]["id"] = h.hexdigest()[:30]
                    elif len(tag["attributes"]["id"]) > 30:
                        tag["attributes"]["id"] = tag["attributes"]["id"][:30]
                else:
                    tag["attributes"]["id"] = get_next_id("block", tag["name"])
                    # Section headers (<h2> tags) mark the start of a new section
                    if (
                        i + 1 < len(self.items)
                        and self.items[i + 1]["type"] == "open"
                        and self.items[i + 1]["item"].get("name") == "h2"
                    ):
                        section_number += 1

                if tag["name"] == "section":
                    tag["attributes"]["data-mw-section-number"] = section_number

                new_doc.add_item(item["type"], tag)

                # Content of tags that are either mw:Transclusion or mw:Extension need not be segmented
                about = cxutil.get_prop(["attributes", "about"], tag)
                typeof = cxutil.get_prop(["attributes", "typeof"], tag)
                if about and typeof:
                    transclusion_context = about

            elif item["type"] == "close":
                tag = item["item"]
                about = cxutil.get_prop(["attributes", "about"], tag)
                if about and about == transclusion_context:
                    transclusion_context = None
                new_doc.add_item(item["type"], item["item"])

            elif item["type"] != "textblock":
                new_doc.add_item(item["type"], item["item"])

            else:
                text_block: TextBlock = item["item"]
                segmented_text_block = (
                    text_block.segment(get_boundaries, get_next_id)
                    if (text_block.can_segment and not transclusion_context)
                    else text_block.set_link_ids(get_next_id)
                )

                new_doc.add_item(
                    "textblock",
                    segmented_text_block,
                )

        return new_doc

    def dump_xml(self) -> str:
        """
        Dump an XML version of the linear representation, for debugging.

        Returns:
            XML version of the linear representation
        """
        return "\n".join(self.dump_xml_array(""))

    def get_html(self) -> str:
        """
        Dump the document in HTML format.

        Returns:
            HTML document
        """
        html = []

        if self.wrapper_tag:
            html.append(utils.get_open_tag_html(self.wrapper_tag))

        for item in self.items:
            item_type = item["type"]
            item_obj = item["item"]

            if isinstance(item_obj, dict) and item_obj.get("attributes", {}).get("class") == "cx-segment-block":
                continue

            if item_type == "open":
                html.append(utils.get_open_tag_html(item_obj))
            elif item_type == "close":
                html.append(utils.get_close_tag_html(item_obj))
            elif item_type == "blockspace":
                html.append(item_obj)
            elif item_type == "textblock":
                html.append(item_obj.get_html())  # pyright: ignore[reportAttributeAccessIssue]
            else:
                raise Exception(f"Unknown item type: {item_type}")

        if self.wrapper_tag:
            html.append(utils.get_close_tag_html(self.wrapper_tag))

        return "".join(html)

    def wrap_sections(self) -> Doc:
        """
        Wrap the content into sections.

        Returns:
            Doc with wrapped sections
        """
        new_doc = Doc()
        in_body = False
        prev_section = None
        curr_section = None

        # Copy the categories already collected
        new_doc.categories = self.categories

        def get_tag_id(tag):
            """Get something that can identify the tag."""
            tag_id = None
            if tag.get("attributes"):
                tag_id = tag["attributes"].get("about") or tag["attributes"].get("id")
            return tag_id or tag["name"]

        def open_section(doc):
            doc.add_item("open", {"name": "section", "attributes": {"rel": "cx:Section"}})

        def close_section(doc):
            nonlocal prev_section, curr_section
            doc.add_item("close", {"name": "section"})
            prev_section = curr_section
            curr_section = None

        def insert_to_prev_section(item, doc):
            nonlocal curr_section, prev_section
            new_item = new_doc.get_current_item()
            if new_item and new_item["item"]["name"] != "section":
                raise Exception(f"Sectionwrap: Attempting to remove a non-section tag: {item['name']}")
            # Undo last section close
            doc.undo_add_item()
            curr_section = prev_section
            doc.add_item(item["type"], item["item"])
            close_section(new_doc)

        for item in self.items:
            item_obj = item["item"]
            item_type = item["type"]

            if not in_body:
                # Till we reach body, keep on adding items to new_doc
                new_doc.add_item(item_type, item_obj)
                if isinstance(item_obj, dict) and item_obj.get("name") == "body":
                    in_body = True
                continue

            if item_type == "open":
                tag = item_obj
                if not curr_section:
                    if prev_section == get_tag_id(tag):
                        # This tag is connected to previous section
                        new_doc.undo_add_item()
                        curr_section = prev_section
                    else:
                        open_section(new_doc)
                        curr_section = get_tag_id(tag)

                new_doc.add_item(item_type, tag)

            elif item_type == "close":
                tag = item_obj
                if curr_section and tag.get("name") == "body":
                    close_section(new_doc)
                    in_body = False

                new_doc.add_item(item_type, tag)
                if get_tag_id(tag) == curr_section:
                    close_section(new_doc)

            elif item_type == "blockspace":
                new_item = new_doc.get_current_item()
                if prev_section and new_item and new_item["item"]["name"] == "section":
                    insert_to_prev_section(item, new_doc)
                else:
                    new_doc.add_item(item_type, item_obj)

            elif item_type == "textblock":
                text_block = item_obj
                tag_for_id = text_block.get_tag_for_id()

                if not tag_for_id and not curr_section:
                    # Textblock with no tag identifier
                    insert_to_prev_section(item, new_doc)
                    continue

                is_connected = tag_for_id and prev_section == get_tag_id(tag_for_id)

                if is_connected:
                    # This tag is connected to previous section
                    insert_to_prev_section(item, new_doc)
                    continue

                if not curr_section:
                    open_section(new_doc)
                    curr_section = get_tag_id(tag_for_id)
                    if not curr_section:
                        raise Exception(f'No id for the opened section for tag {tag_for_id.get("name")}')
                    new_doc.add_item(item_type, text_block)
                    close_section(new_doc)
                    continue

                new_doc.add_item(item_type, text_block)

            else:
                raise Exception(f"Unknown item type: {item_type}")

        return new_doc

    def dump_xml_array(self, pad: str) -> list:
        """
        Dump an XML Array version of the linear representation, for debugging.

        Args:
            pad: Indentation whitespace

        Returns:
            Array that will concatenate to an XML string representation
        """
        dump = []

        if self.wrapper_tag:
            dump.append(f"{pad}<cxwrapper>")

        for item in self.items:
            item_type = item["type"]
            item_obj = item["item"]

            if item_type == "open":
                tag = item_obj
                dump.append(f'{pad}<{tag["name"]}>')
                if tag["name"] == "head":
                    # Add a few things for easy display
                    dump.append(f'{pad}<meta charset="UTF-8" />')
                    dump.append(f"{pad}<style>cxtextblock {{ border: solid #88f 1px }}")
                    dump.append(f"{pad}cxtextchunk {{ border-right: solid #f88 1px }}</style>")

            elif item_type == "close":
                tag = item_obj
                dump.append(f'{pad}</{tag["name"]}>')

            elif item_type == "blockspace":
                dump.append(f"{pad}<cxblockspace/>")

            elif item_type == "textblock":
                text_block = item_obj
                dump.append(f"{pad}<cxtextblock>")
                dump.extend(text_block.dump_xml_array(pad + "  "))
                dump.append(f"{pad}</cxtextblock>")

            else:
                raise Exception(f"Unknown item type: {item_type}")

        if self.wrapper_tag:
            dump.append(f"{pad}</cxwrapper>")

        return dump

    def get_segments(self) -> list:
        """
        Extract the text segments from the document.

        Returns:
            Balanced html fragments, one per segment
        """
        segments = []

        for item in self.items:
            if item["type"] != "textblock":
                continue
            text_block = item["item"]
            segments.append(text_block.get_html())

        return segments


__all__ = [
    "Doc",
]
