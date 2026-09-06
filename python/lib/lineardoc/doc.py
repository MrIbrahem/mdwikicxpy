"""
Doc - An HTML document in linear representation.

The document is a list of items, where each item is:
- a block open tag (e.g. <p>); or
- a block close tag (e.g. </p>); or
- a text_block of annotated inline text; or
- "block whitespace" (a run of whitespace separating two block boundaries)

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/Doc.js
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from .doc_item import (
    DocDict,
    DocStr,
    DocTextBlock,
)
from .text_block import TextBlock
from .utils import Utils

DOC_ITEM_VARS = DocTextBlock | DocDict | DocStr


class Doc:
    """An HTML document in linear representation."""

    def __init__(
        self,
        wrapper_tag: dict[str, Any] | None = None,
        sort_attrs: bool = True,
    ) -> None:
        """
        Initialize a Doc.

        Args:
            wrapper_tag: Open/close tags
        """
        self.items: list[DOC_ITEM_VARS] = []
        self.wrapper_tag = wrapper_tag
        self.sort_attrs = sort_attrs
        self.categories = []

    # ----------------
    # Write
    # ----------------
    def add_textblock_item(self, item: TextBlock) -> Doc:
        self.items.append(DocTextBlock(item))
        return self

    def add_dict_item(self, item_type, item: dict[str, Any]) -> Doc:
        self.items.append(DocDict.load(item_type=item_type, obj=item))
        return self

    def add_blockspace_item(self, item: str) -> Doc:
        self.items.append(DocStr(item=item))
        return self

    def add_item(self, item_type: str, item: Any) -> Doc:
        """
        Add an item to the document.
        """
        if item_type == "textblock":
            return self.add_textblock_item(item)

        if item_type == "blockspace":
            return self.add_blockspace_item(item)

        if item_type in ("open", "close"):
            return self.add_dict_item(item_type, item)

        raise TypeError(f"Invalid type for Item: {type(item)}")

    def undo_add_item(self) -> None:
        """Remove the top item from the linear array of items."""
        self.items.pop()

    # ----------------
    # ----------------
    def get_current_item(self):
        """
        Get the top item in the linear array of items.

        Returns:
            Current item
        """
        item = self.items[-1] if self.items else None

        if item and hasattr(item, "to_json"):
            return item.to_json()

        return item

    def get_root_item(self) -> None | dict[str, Any]:
        """
        Get the root item in the doc.

        Returns:
            Root item
        """
        if self.wrapper_tag:
            return self.wrapper_tag

        for i_item in self.items:
            # Ignore all blockspaces, loop till we see a tag opening
            if i_item.item_type == "open" and isinstance(i_item, DocDict):
                return i_item.item.to_json()
        return None

    def segment(self, get_boundaries: Callable) -> Doc:
        """
        Segment the document into sentences.

        Args:
            get_boundaries: Function taking plaintext, returning offset array

        Returns:
            Segmented version of document
        """
        new_doc = Doc(sort_attrs=self.sort_attrs)
        next_section_id = 0
        next_id = 0
        section_number = 0

        def get_next_id(id_type: str, tag_name: str | None = None) -> str:
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

        for i, i_item in enumerate(self.items):
            if i_item.item_type == "open" and isinstance(i_item, DocDict):
                tag = i_item.item.clone()

                if tag.attributes.get("id"):
                    # If the item is a header, we make it a fixed length id using hash of
                    # the text content. Header ids are originally the header text to get
                    # the URL fragments working, but for CX, it is irrelevant and we need
                    # a fixed length id that can be used as DB key.
                    # The text inside this 'open tag' is in the next item(i+1).
                    if (
                        tag.name in ["h1", "h2", "h3", "h4", "h5"]
                        and i + 1 < len(self.items)
                        and self.items[i + 1].item_type == "textblock"
                    ):
                        h = hashlib.sha256()
                        h.update(self.items[i + 1]["item"].get_plain_text().encode("utf-8"))
                        # 30 is the max length of ids we allow. We also prepend the sequence id
                        # just to make sure the ids don't collide if the same text repeats.
                        tag.attributes["id"] = h.hexdigest()[:30]
                    elif len(tag.attributes["id"]) > 30:
                        # At any case, make sure that the section id never exceeds 30 bytes
                        tag.attributes["id"] = tag.attributes["id"][:30]
                else:
                    tag.attributes["id"] = get_next_id("block", tag.name)
                    # Section headers (<h2> tags) mark the start of a new section
                    if i + 1 < len(self.items):
                        item_z = self.items[i + 1]
                        # if item_z.item_type == "open" and item_z["item"].get("name") == "h2":
                        if (
                            item_z.item_type == "open"
                            and item_z.item.name == "h2"  # pyright: ignore[reportAttributeAccessIssue]
                        ):  # pyright: ignore[reportAttributeAccessIssue]
                            section_number += 1

                if tag.name == "section":
                    tag.attributes["data-mw-section-number"] = section_number

                new_doc.add_dict_item(i_item.item_type, tag.to_json())

                # Content of tags that are either mw:Transclusion or mw:Extension need not be segmented
                about = tag.attributes.get("about")
                typeof = tag.attributes.get("typeof")
                if about and typeof:
                    transclusion_context = about

            elif i_item.item_type == "close" and isinstance(i_item, DocDict):
                tag = i_item.item
                about = tag.attributes.get("about")
                if about and about == transclusion_context:
                    transclusion_context = None
                new_doc.add_dict_item(i_item.item_type, tag.to_json())

            elif i_item.item_type == "textblock" and isinstance(i_item, DocTextBlock):
                text_block = i_item.item

                if text_block.can_segment and not transclusion_context:
                    segmented_text_block = text_block.segment(get_boundaries, get_next_id)
                else:
                    segmented_text_block = text_block.set_link_ids(get_next_id)

                new_doc.add_textblock_item(segmented_text_block)
            else:
                raise Exception(f"Unknown item type: {i_item.item_type}")

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
            html.append(Utils.get_open_tag_html(self.wrapper_tag, self.sort_attrs))

        for i_item in self.items:
            item_type = i_item.item_type

            if isinstance(i_item, DocDict):
                if i_item.item.attributes.get("class") == "cx-segment-block":
                    continue

            if item_type in ("open", "close") and isinstance(i_item, DocDict):
                html.append(i_item.get_html(self.sort_attrs))

            elif item_type == "blockspace" and isinstance(i_item, DocStr):
                html.append(i_item.get_html())

            elif item_type == "textblock" and isinstance(i_item, DocTextBlock):
                html.append(i_item.get_html())
            else:
                raise Exception(f"Unknown item type: {item_type}")

        if self.wrapper_tag:
            html.append(Utils.get_close_tag_html(self.wrapper_tag))

        return "".join(html)

    def wrap_sections(self) -> Doc:
        """
        Wrap the content into sections.

        Returns:
            Doc with wrapped sections
        """
        new_doc = Doc(sort_attrs=self.sort_attrs)
        in_body = False
        prev_section = None
        curr_section = None

        # Copy the categories already collected
        new_doc.categories = self.categories

        def get_tag_id(tag: dict[str, Any]):
            """
            Get something that can identify the tag.

            For a given tag, get something that can be used to identify the tag.
            `about` attribute has more preference in our context since it connects
            template fragments. If `about` is not present, use id attribute.
            If no attributes, then it is tag name. In real wiki content, the case
            of no attributes is not found.
            """
            tag_id = None
            if tag.get("attributes"):
                tag_id = tag["attributes"].get("about") or tag["attributes"].get("id")

            return tag_id or tag["name"]

        def open_section(doc: Doc):
            doc.add_dict_item("open", {"name": "section", "attributes": {"rel": "cx:Section"}})

        def close_section(doc: Doc):
            nonlocal prev_section, curr_section
            doc.add_dict_item("close", {"name": "section"})
            prev_section = curr_section
            curr_section = None

        def insert_to_prev_section(item, doc: Doc):
            nonlocal curr_section, prev_section
            new_item = new_doc.get_current_item()

            if new_item and new_item["item"]["name"] != "section":
                raise Exception(f"Sectionwrap: Attempting to remove a non-section tag: {item['name']}")

            # Undo last section close
            doc.undo_add_item()
            curr_section = prev_section
            doc.add_item(item.item_type, item.item)
            close_section(new_doc)

        for i_item in self.items:
            item_type = i_item.item_type

            if not in_body:
                # Till we reach body, keep on adding items to new_doc
                new_doc.add_item(item_type, i_item.item)
                if getattr(i_item.item, "name", None) == "body":
                    in_body = True
                continue

            if item_type == "open" and isinstance(i_item, DocDict):
                tag = i_item.item
                if not curr_section:
                    if prev_section == tag.get_tag_id():
                        # This tag is connected to previous section. Can be a template fragment.
                        # Undo last section close
                        new_doc.undo_add_item()
                        curr_section = prev_section
                    else:
                        open_section(new_doc)
                        curr_section = tag.get_tag_id()

                new_doc.add_item(item_type, tag)

            elif item_type == "close" and isinstance(i_item, DocDict):
                tag = i_item.item
                if curr_section and tag.name == "body":
                    close_section(new_doc)
                    in_body = False

                new_doc.add_item(item_type, tag)
                if tag.get_tag_id() == curr_section:
                    close_section(new_doc)

            elif item_type == "blockspace" and isinstance(i_item, DocStr):
                tag = i_item.item
                new_item = new_doc.get_current_item()
                if prev_section and new_item and new_item["item"]["name"] == "section":
                    insert_to_prev_section(tag, new_doc)
                else:
                    new_doc.add_blockspace_item(tag)

            elif item_type == "textblock" and isinstance(i_item, DocTextBlock):
                tag = i_item.item
                text_block = i_item.item
                tag_for_id = text_block.get_tag_for_id() or {}

                if not tag_for_id and not curr_section:
                    new_item = new_doc.get_current_item()
                    # Textblock with no tag identifier. Add it to the previous section
                    if prev_section and new_item and new_item["item"]["name"] == "section":
                        insert_to_prev_section(tag, new_doc)
                        continue

                # No previous section to attach to; fall through to open a new one
                is_connected = tag_for_id and not curr_section and prev_section == get_tag_id(tag_for_id)

                if is_connected:
                    # This tag is connected to previous section. Can be a template fragment.
                    insert_to_prev_section(tag, new_doc)
                    continue

                if not curr_section:
                    open_section(new_doc)
                    curr_section = get_tag_id(tag_for_id)
                    if not curr_section:
                        raise Exception(f'No id for the opened section for tag {tag_for_id.get("name")}')

                    new_doc.add_textblock_item(text_block)
                    # There was no open sections. Close the section now itself. If this tag is a template
                    # fragment, `is_connected` check above will insert the fragments to closed section.

                    close_section(new_doc)
                    continue

                new_doc.add_textblock_item(text_block)

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

        for i_item in self.items:

            if i_item.item_type == "open" and isinstance(i_item, DocDict):
                tag = i_item.item
                dump.append(tag.opening_tag(pad))

                if tag.name == "head":
                    # Add a few things for easy display
                    dump.append(f'{pad}<meta charset="UTF-8" />')
                    dump.append(f"{pad}<style>cxtextblock {{ border: solid #88f 1px }}")
                    dump.append(f"{pad}cxtextchunk {{ border-right: solid #f88 1px }}</style>")

            elif i_item.item_type == "close" and isinstance(i_item, DocDict):
                # close block tag
                tag = i_item.item
                dump.append(tag.closing_tag(pad))

            elif i_item.item_type == "blockspace" and isinstance(i_item, DocStr):
                # Non-inline whitespace
                dump.append(f"{pad}<cxblockspace/>")

            elif i_item.item_type == "textblock" and isinstance(i_item, DocTextBlock):
                # Block of inline text
                dump.extend(i_item.generate_textblock_xml(pad))

            else:
                raise Exception(f"Unknown item type: {i_item.item_type}")

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

        for i_item in self.items:
            if i_item.item_type != "textblock":
                continue
            text_block = i_item.item
            segments.append(text_block.get_html())

        return segments

    def clone(self, callback: Callable) -> Doc:
        """
        Clone the Doc, modifying as we go.

        Args:
            callback: The function to modify a node

        Returns:
            Clone with modifications
        """
        new_doc = Doc(self.wrapper_tag, self.sort_attrs)

        for i_item in self.items:
            new_item = callback(i_item)
            if isinstance(new_item, dict):
                new_doc.add_item(new_item["item_type"], new_item["item"])
            else:
                new_doc.add_item(new_item.item_type, new_item.item)

        return new_doc

    def is_ignorable_block(self) -> bool:
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

        for i, i_item in enumerate(self.items):
            if i == 0:
                continue

            item_type = i_item.item_type

            if item_type == "open" and isinstance(i_item, DocDict):
                tag_dict = i_item.item.to_json()
                block_stack.append(tag_dict)
                if not first_block_template and (Utils.is_transclusion(tag_dict) or Utils.is_reference_list(tag_dict)):
                    first_block_template = tag_dict

            if item_type == "close" and isinstance(i_item, DocDict):
                tag_dict = i_item.item.to_json()
                if block_stack:
                    current_close_tag = block_stack.pop()
                    if Utils.is_closing_template_match(block_stack, first_block_template, current_close_tag):
                        return True

            # Also check for textblocks
            if item_type == "textblock" and isinstance(i_item, DocTextBlock):
                if not first_block_template:
                    root_item = i_item.item.get_root_item()
                    if root_item and Utils.is_non_translatable(root_item):
                        first_block_template = root_item
                        ignorable = True
                    else:
                        # There is non ignorable content to translate
                        return False

        return ignorable


__all__ = [
    "Doc",
]
