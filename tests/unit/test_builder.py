"""
Unit tests for lineardoc/builder.py module.
"""

import pytest
from python.lib.lineardoc import Doc
from python.lib.lineardoc.builder import Builder


class TestBuilderCreation:
    """Test Builder initialization."""

    def test_builder_creation(self):
        """Test creating a builder."""
        builder = Builder()
        assert builder.block_tags == []
        assert builder.inline_annotation_tags == []
        assert builder.doc is not None
        assert isinstance(builder.doc, Doc)
        assert builder.parent is None

    def test_builder_with_parent(self):
        """Test creating builder with parent."""
        parent = Builder()
        wrapper = {"name": "span", "attributes": {}}
        child = Builder(parent, wrapper)
        assert child.parent is parent
        assert child.doc.wrapper_tag == wrapper


class TestBuilderPushBlockTag:
    """Test push_block_tag method."""

    def test_push_block_tag_simple(self):
        """Test pushing a simple block tag."""
        builder = Builder()
        tag = {"name": "p", "attributes": {}}
        builder.push_block_tag(tag)
        assert len(builder.block_tags) == 1
        assert builder.block_tags[0] == tag
        assert len(builder.doc.items) == 1

    def test_push_block_tag_figure(self):
        """Test pushing figure tag adds rel attribute."""
        builder = Builder()
        tag = {"name": "figure", "attributes": {}}
        builder.push_block_tag(tag)
        # Figure should have cx:Figure rel
        assert "rel" in tag["attributes"]
        assert tag["attributes"]["rel"] == "cx:Figure"


class TestBuilderPopBlockTag:
    """Test pop_block_tag method."""

    def test_pop_block_tag_simple(self):
        """Test popping a block tag."""
        builder = Builder()
        tag = {"name": "p", "attributes": {}}
        builder.push_block_tag(tag)
        popped = builder.pop_block_tag("p")
        assert popped == tag
        assert len(builder.block_tags) == 0

    def test_pop_block_tag_mismatch(self):
        """Test popping mismatched tag raises error."""
        builder = Builder()
        builder.push_block_tag({"name": "div", "attributes": {}})
        with pytest.raises(Exception) as excinfo:
            builder.pop_block_tag("p")
        assert "Mismatched" in str(excinfo.value)


class TestBuilderInlineAnnotationTags:
    """Test inline annotation tag methods."""

    def test_push_inline_annotation_tag(self):
        """Test pushing inline annotation tag."""
        builder = Builder()
        tag = {"name": "b", "attributes": {}}
        builder.push_inline_annotation_tag(tag)
        assert len(builder.inline_annotation_tags) == 1
        assert builder.inline_annotation_tags[0] == tag

    def test_pop_inline_annotation_tag(self):
        """Test popping inline annotation tag."""
        builder = Builder()
        tag = {"name": "b", "attributes": {}}
        builder.push_inline_annotation_tag(tag)
        builder.pop_inline_annotation_tag("b")
        assert len(builder.inline_annotation_tags) == 0


class TestBuilderTextChunks:
    """Test text chunk handling."""

    def test_add_text_chunk_simple(self):
        """Test adding a text chunk."""
        builder = Builder()
        builder.add_text_chunk("Hello", True)
        assert len(builder.text_chunks) > 0

    def test_finish_text_block(self):
        """Test finishing a text block."""
        builder = Builder()
        builder.add_text_chunk("Hello", True)
        builder.finish_text_block()
        # Should have added textblock to doc
        assert any(item.item_type == "textblock" for item in builder.doc.items)


class TestBuilderChildBuilder:
    """Test child builder creation."""

    def test_create_child_builder(self):
        """Test creating a child builder."""
        parent = Builder()
        wrapper = {"name": "span", "attributes": {}}
        child = parent.create_child_builder(wrapper)
        assert child.parent is parent
        assert child.doc.wrapper_tag == wrapper


class TestBuilderIsCategory:
    """Test is_category method."""

    def test_is_category_true(self):
        """Test detecting category link."""
        builder = Builder()
        tag = {"name": "link", "attributes": {"rel": "mw:PageProp/Category"}}
        assert builder.is_category(tag) is True

    def test_is_category_false(self):
        """Test non-category link."""
        builder = Builder()
        tag = {"name": "link", "attributes": {"rel": "other"}}
        assert builder.is_category(tag) is False

    def test_is_category_not_dict(self):
        """Test is_category with non-dict."""
        builder = Builder()
        assert builder.is_category("not a tag") is False  # pyright: ignore[reportArgumentType]


class TestBuilderIsSection:
    """Test is_section method."""

    def test_is_section_true(self):
        """Test detecting section."""
        builder = Builder()
        tag = {"name": "section", "attributes": {"data-mw-section-id": "1"}}
        # is_section returns the value, not a boolean
        assert builder.is_section(tag) == "1"

    def test_is_section_false(self):
        """Test non-section."""
        builder = Builder()
        tag = {"name": "section", "attributes": {}}
        # Returns None if not a section
        assert builder.is_section(tag) is None

    def test_is_section_wrong_name(self):
        """Test wrong tag name."""
        builder = Builder()
        tag = {"name": "div", "attributes": {"data-mw-section-id": "1"}}
        # Returns False because name != 'section'
        result = builder.is_section(tag)
        assert result is False or result is None
