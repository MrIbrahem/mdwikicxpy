"""
Builder - A document builder for creating linear documents.
"""

from . import utils
from .doc import Doc
from .text_block import TextBlock
from .text_chunk import TextChunk


class Builder:
    """A document builder."""

    def __init__(self, parent=None, wrapper_tag=None):
        """
        Initialize a Builder.

        Args:
            parent: Parent document builder
            wrapper_tag: Tag that wraps document (if there is a parent)
        """
        self.block_tags = []
        # Stack of annotation tags
        self.inline_annotation_tags = []
        # The height of the annotation tags that have been used, minus one
        self.inline_annotation_tags_used = 0
        self.doc = Doc(wrapper_tag)
        self.text_chunks = []
        self.is_block_segmentable = True
        self.parent = parent

    def create_child_builder(self, wrapper_tag):
        """
        Create a child builder.

        Args:
            wrapper_tag: Wrapper tag for child

        Returns:
            New Builder instance
        """
        return Builder(self, wrapper_tag)

    def push_block_tag(self, tag):
        """Push a block tag."""
        self.finish_text_block()
        self.block_tags.append(tag)
        if self.is_ignored_tag(tag):
            return
        if tag["name"] == "figure":
            tag["attributes"]["rel"] = "cx:Figure"
        self.doc.add_item("open", tag)

    def is_section(self, tag):
        """Check if tag is a section."""
        return tag["name"] == "section" and tag.get("attributes", {}).get("data-mw-section-id")

    def is_ignored_tag(self, tag):
        """Check if tag should be ignored."""
        return self.is_section(tag) or self.is_category(tag)

    def is_category(self, tag):
        """Check if tag is a category."""
        # content can be a Doc instance, not just a tag
        if not isinstance(tag, dict):
            return False
        rel = tag.get("attributes", {}).get("rel", "")
        return (
            tag["name"] == "link"
            and f" {rel} ".find(" mw:PageProp/Category ") != -1
            and not tag.get("attributes", {}).get("about")
        )

    def pop_block_tag(self, tag_name):
        """
        Pop a block tag.

        Args:
            tag_name: Name of tag to pop

        Returns:
            The popped tag
        """
        if not self.block_tags:
            tag = None
        else:
            tag = self.block_tags.pop()

        if not tag or tag["name"] != tag_name:
            raise Exception(f"Mismatched block tags: open={tag['name'] if tag else None}, close={tag_name}")

        self.finish_text_block()

        if not self.is_ignored_tag(tag):
            self.doc.add_item("close", tag)

        return tag

    def push_inline_annotation_tag(self, tag):
        """Push an inline annotation tag."""
        self.inline_annotation_tags.append(tag)

    def pop_inline_annotation_tag(self, tag_name):
        """Pop an inline annotation tag."""
        if not self.inline_annotation_tags:
            tag = None
        else:
            tag = self.inline_annotation_tags.pop()

        if self.inline_annotation_tags_used == len(self.inline_annotation_tags):
            self.inline_annotation_tags_used -= 1

        if not tag or tag["name"] != tag_name:
            raise Exception(f"Mismatched inline tags: open={tag['name'] if tag else None}, close={tag_name}")

        if not tag.get("attributes"):
            # Skip tags which have no attributes
            return

        # Check for empty/whitespace-only data tags
        replace = True
        whitespace = []
        i = len(self.text_chunks) - 1
        while i >= 0:
            text_chunk = self.text_chunks[i]
            chunk_tag = text_chunk.tags[-1] if text_chunk.tags else None
            if not chunk_tag:
                break
            if text_chunk.text.strip() or text_chunk.inline_content or chunk_tag is not tag:
                # text_chunk has non whitespace content
                replace = False
                break
            whitespace.append(text_chunk.text)
            i -= 1

        # Allow empty external links and references
        if replace and (utils.is_reference(tag) or utils.is_external_link(tag) or utils.is_transclusion(tag)):
            # truncate list and add data span as new sub-Doc
            self.text_chunks = self.text_chunks[: i + 1]
            whitespace.reverse()
            self.add_inline_content(
                Doc()
                .add_item("open", tag)
                .add_item("textblock", TextBlock([text_chunk("".join(whitespace), [])]))
                .add_item("close", tag)
            )

    def add_text_chunk(self, text, can_segment):
        """
        Add a text chunk.

        Args:
            text: Text content
            can_segment: Whether this can be segmented
        """
        self.text_chunks.append(TextChunk(text, self.inline_annotation_tags[:]))
        self.inline_annotation_tags_used = len(self.inline_annotation_tags)
        # Inside a textblock, if a textchunk becomes segmentable
        self.is_block_segmentable = can_segment

    def add_inline_content(self, content, can_segment=True) -> None:
        """
        Add content that doesn't need linearizing, to appear inline.

        Args:
            content: Sub-document or empty SAX tag
            can_segment: Whether this can be segmented
        """
        # If the content is a category tag, capture it separately
        if self.is_category(content):
            self.doc.categories.append(content)
            return

        self.text_chunks.append(TextChunk("", self.inline_annotation_tags[:], content))
        self.inline_annotation_tags_used = len(self.inline_annotation_tags)
        if not can_segment:
            self.is_block_segmentable = False

    def finish_text_block(self):
        """Finish the current text block."""
        if len(self.text_chunks) == 0:
            return

        whitespace = []
        whitespace_only = True

        for text_chunk in self.text_chunks:
            if text_chunk.inline_content or text_chunk.text.strip():
                whitespace_only = False
                break
            else:
                whitespace.append(text_chunk.text)

        if whitespace_only:
            self.doc.add_item("blockspace", "".join(whitespace))
        else:
            self.doc.add_item("textblock", TextBlock(self.text_chunks, self.is_block_segmentable))

        self.text_chunks = []
        self.is_block_segmentable = True
