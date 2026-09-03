"""
Unit tests for lineardoc/doc.py module.
"""

import os
import sys

import pytest
from python.lib.lineardoc import Doc, TextBlock, TextChunk


class TestDocCreation:
    """Test Doc initialization."""

    def test_doc_creation_simple(self):
        """Test creating a simple Doc."""
        doc = Doc()
        assert doc.items == []
        assert doc.wrapper_tag is None
        assert doc.categories == []

    def test_doc_creation_with_wrapper(self):
        """Test creating Doc with wrapper tag."""
        wrapper = {"name": "div", "attributes": {}}
        doc = Doc(wrapper)
        assert doc.wrapper_tag == wrapper


class TestDocAddItem:
    """Test add_item method."""

    def test_add_open_tag(self):
        """Test adding an open tag."""
        doc = Doc()
        tag = {"name": "p", "attributes": {}}
        doc.add_item("open", tag)
        assert len(doc.items) == 1
        assert doc.items[0]["type"] == "open"
        assert doc.items[0]["item"] == tag

    def test_add_close_tag(self):
        """Test adding a close tag."""
        doc = Doc()
        tag = {"name": "p"}
        doc.add_item("close", tag)
        assert len(doc.items) == 1
        assert doc.items[0]["type"] == "close"

    def test_add_textblock(self):
        """Test adding a text block."""
        doc = Doc()
        chunks = [TextChunk("text", [])]
        block = TextBlock(chunks)
        doc.add_item("textblock", block)
        assert len(doc.items) == 1
        assert doc.items[0]["type"] == "textblock"

    def test_add_blockspace(self):
        """Test adding block space."""
        doc = Doc()
        doc.add_item("blockspace", "  ")
        assert len(doc.items) == 1
        assert doc.items[0]["type"] == "blockspace"

    def test_add_item_chaining(self):
        """Test that add_item returns self for chaining."""
        doc = Doc()
        result = doc.add_item("open", {"name": "div"})
        assert result is doc


class TestDocItemManagement:
    """Test item management methods."""

    def test_get_current_item(self):
        """Test getting current item."""
        doc = Doc()
        tag = {"name": "p", "attributes": {}}
        doc.add_item("open", tag)
        current = doc.get_current_item()
        assert current["type"] == "open"
        assert current["item"] == tag

    def test_get_current_item_empty(self):
        """Test getting current item from empty doc."""
        doc = Doc()
        current = doc.get_current_item()
        assert current is None

    def test_undo_add_item(self):
        """Test undoing add item."""
        doc = Doc()
        doc.add_item("open", {"name": "div"})
        doc.add_item("open", {"name": "p"})
        assert len(doc.items) == 2
        doc.undo_add_item()
        assert len(doc.items) == 1
        assert doc.items[0]["item"]["name"] == "div"


class TestDocGetRootItem:
    """Test get_root_item method."""

    def test_get_root_item_with_wrapper(self):
        """Test getting root item with wrapper."""
        wrapper = {"name": "div", "attributes": {}}
        doc = Doc(wrapper)
        root = doc.get_root_item()
        assert root == wrapper

    def test_get_root_item_without_wrapper(self):
        """Test getting root item without wrapper."""
        doc = Doc()
        tag = {"name": "p", "attributes": {}}
        doc.add_item("open", tag)
        root = doc.get_root_item()
        assert root == tag

    def test_get_root_item_skip_blockspace(self):
        """Test that get_root_item skips blockspace."""
        doc = Doc()
        doc.add_item("blockspace", " ")
        doc.add_item("open", {"name": "div", "attributes": {}})
        root = doc.get_root_item()
        assert root["name"] == "div"

    def test_get_root_item_empty(self):
        """Test getting root from empty doc."""
        doc = Doc()
        root = doc.get_root_item()
        assert root is None


class TestDocGetHtml:
    """Test get_html method."""

    def test_get_html_simple(self):
        """Test getting HTML from simple doc."""
        doc = Doc()
        doc.add_item("open", {"name": "p", "attributes": {}})
        chunks = [TextChunk("Hello", [])]
        doc.add_item("textblock", TextBlock(chunks))
        doc.add_item("close", {"name": "p"})
        html = doc.get_html()
        assert "<p>" in html
        assert "Hello" in html
        assert "</p>" in html

    def test_get_html_with_wrapper(self):
        """Test getting HTML with wrapper tag."""
        wrapper = {"name": "div", "attributes": {"class": "wrapper"}}
        doc = Doc(wrapper)
        chunks = [TextChunk("content", [])]
        doc.add_item("textblock", TextBlock(chunks))
        html = doc.get_html()
        assert "<div" in html
        assert 'class="wrapper"' in html
        assert "</div>" in html

    def test_get_html_blockspace(self):
        """Test that blockspace is included."""
        doc = Doc()
        doc.add_item("blockspace", "\n  ")
        html = doc.get_html()
        assert "\n  " in html

    def test_get_html_skip_segment_block(self):
        """Test that cx-segment-block divs are skipped."""
        doc = Doc()
        doc.add_item("open", {"name": "div", "attributes": {"class": "cx-segment-block"}})
        chunks = [TextChunk("text", [])]
        doc.add_item("textblock", TextBlock(chunks))
        doc.add_item("close", {"name": "div"})
        html = doc.get_html()
        # cx-segment-block should not be in output
        assert "cx-segment-block" not in html
        # But text should still be there
        assert "text" in html


class TestDocClone:
    """Test clone method."""

    def test_clone_simple(self):
        """Test cloning a doc."""
        doc = Doc()
        doc.add_item("open", {"name": "p", "attributes": {}})

        def callback(item):
            return item  # No modification

        cloned = doc.clone(callback)
        assert len(cloned.items) == len(doc.items)
        assert cloned is not doc

    def test_clone_with_modification(self):
        """Test cloning with modification."""
        doc = Doc()
        doc.add_item("open", {"name": "p", "attributes": {}})

        def callback(item):
            # Add a class to all open tags
            if item["type"] == "open":
                new_item = {
                    "type": item["type"],
                    "item": {"name": item["item"]["name"], "attributes": dict(item["item"].get("attributes", {}))},
                }
                new_item["item"]["attributes"]["class"] = "modified"
                return new_item
            return item

        cloned = doc.clone(callback)
        assert cloned.items[0]["item"]["attributes"]["class"] == "modified"


class TestDocWrapSections:
    """Test wrap_sections method."""

    def test_wrap_sections_simple(self):
        """Test wrapping simple sections."""
        doc = Doc()
        doc.add_item("open", {"name": "body", "attributes": {}})
        doc.add_item("open", {"name": "h2", "attributes": {}})
        chunks = [TextChunk("Heading", [])]
        doc.add_item("textblock", TextBlock(chunks))
        doc.add_item("close", {"name": "h2"})
        doc.add_item("close", {"name": "body"})

        wrapped = doc.wrap_sections()
        html = wrapped.get_html()
        # Should contain section tags
        assert "<section" in html
        assert 'rel="cx:Section"' in html

    def test_wrap_sections_preserves_categories(self):
        """Test that wrap_sections preserves categories."""
        doc = Doc()
        doc.categories = ["Category:Test"]
        wrapped = doc.wrap_sections()
        assert wrapped.categories == ["Category:Test"]


class TestDocGetSegments:
    """Test get_segments method."""

    def test_get_segments_simple(self):
        """Test getting segments from doc."""
        doc = Doc()
        chunks1 = [TextChunk("First", [])]
        chunks2 = [TextChunk("Second", [])]
        doc.add_item("textblock", TextBlock(chunks1))
        doc.add_item("textblock", TextBlock(chunks2))

        segments = doc.get_segments()
        assert len(segments) == 2
        assert isinstance(segments[0], str)
        assert isinstance(segments[1], str)

    def test_get_segments_skip_non_textblocks(self):
        """Test that get_segments only returns textblocks."""
        doc = Doc()
        doc.add_item("open", {"name": "p", "attributes": {}})
        chunks = [TextChunk("Text", [])]
        doc.add_item("textblock", TextBlock(chunks))
        doc.add_item("close", {"name": "p"})

        segments = doc.get_segments()
        # Should only have one segment (the textblock)
        assert len(segments) == 1
