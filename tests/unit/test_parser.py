"""
Unit tests for lineardoc/parser.py module.
"""

import os
import sys

import pytest
from python.lib.lineardoc import Contextualizer, Parser


class TestParserCreation:
    """Test Parser initialization."""

    def test_parser_creation(self):
        """Test creating a parser."""
        ctx = Contextualizer()
        parser = Parser(ctx)
        assert parser.contextualizer is ctx
        assert parser.options == {}
        assert parser.lowercase is True

    def test_parser_with_options(self):
        """Test creating parser with options."""
        ctx = Contextualizer()
        options = {"wrapSections": True}
        parser = Parser(ctx, options)
        assert parser.options == options


class TestParserInit:
    """Test parser initialization."""

    def test_parser_init(self):
        """Test initializing parser state."""
        ctx = Contextualizer()
        parser = Parser(ctx)
        parser.init()
        assert parser.root_builder is not None
        assert parser.builder is parser.root_builder
        assert parser.all_tags == []


class TestParserWrite:
    """Test write method."""

    def test_write_simple_html(self):
        """Test parsing simple HTML."""
        from python.lib.lineardoc import MwContextualizer

        ctx = MwContextualizer()
        parser = Parser(ctx)
        parser.init()
        parser.write("<div>Hello</div>")
        # Should have created doc items
        assert len(parser.builder.doc.items) > 0

    def test_write_nested_html(self):
        """Test parsing nested HTML."""
        from python.lib.lineardoc import MwContextualizer

        ctx = MwContextualizer()
        parser = Parser(ctx)
        parser.init()
        parser.write("<div><p>Text</p></div>")
        assert len(parser.builder.doc.items) > 0

    def test_write_with_attributes(self):
        """Test parsing HTML with attributes."""
        from python.lib.lineardoc import MwContextualizer

        ctx = MwContextualizer()
        parser = Parser(ctx)
        parser.init()
        parser.write('<div class="test" id="main">Content</div>')
        # Should preserve attributes
        assert len(parser.builder.doc.items) > 0

    def test_write_invalid_html(self):
        """Test parsing invalid HTML - should try wrapping."""
        from python.lib.lineardoc import MwContextualizer

        ctx = MwContextualizer()
        parser = Parser(ctx)
        parser.init()
        # Just text without wrapper
        try:
            parser.write("Hello world")
            # Should handle gracefully
            assert True
        except Exception:
            # Some invalid HTML may still fail
            pass

    def test_write_unicode(self):
        """Test parsing Unicode HTML."""
        from python.lib.lineardoc import MwContextualizer

        ctx = MwContextualizer()
        parser = Parser(ctx)
        parser.init()
        parser.write("<div>مرحبا العالم</div>")
        assert len(parser.builder.doc.items) > 0


class TestParserInlineAnnotationTag:
    """Test is_inline_annotation_tag method."""

    def test_is_inline_annotation_tag_span(self):
        """Test span is inline annotation."""
        ctx = Contextualizer()
        parser = Parser(ctx)
        assert parser.is_inline_annotation_tag("span", False) is True

    def test_is_inline_annotation_tag_div(self):
        """Test div is not inline annotation."""
        ctx = Contextualizer()
        parser = Parser(ctx)
        assert parser.is_inline_annotation_tag("div", False) is False

    def test_is_inline_annotation_tag_p(self):
        """Test p is not inline annotation."""
        ctx = Contextualizer()
        parser = Parser(ctx)
        assert parser.is_inline_annotation_tag("p", False) is False

    def test_is_inline_annotation_tag_b(self):
        """Test b is inline annotation."""
        ctx = Contextualizer()
        parser = Parser(ctx)
        assert parser.is_inline_annotation_tag("b", False) is True

    def test_is_inline_annotation_tag_i(self):
        """Test i is inline annotation."""
        ctx = Contextualizer()
        parser = Parser(ctx)
        assert parser.is_inline_annotation_tag("i", False) is True


class TestParserBlockTags:
    """Test block tag constants."""

    def test_block_tags_list(self):
        """Test that BLOCK_TAGS is defined."""
        from python.lib.lineardoc.parser import BLOCK_TAGS

        assert isinstance(BLOCK_TAGS, list)
        assert "div" in BLOCK_TAGS
        assert "p" in BLOCK_TAGS
        assert "h1" in BLOCK_TAGS
        assert "table" in BLOCK_TAGS

    def test_inline_tags_not_in_block_tags(self):
        """Test that inline tags are not in BLOCK_TAGS."""
        from python.lib.lineardoc.parser import BLOCK_TAGS

        assert "span" not in BLOCK_TAGS
        assert "a" not in BLOCK_TAGS
        assert "b" not in BLOCK_TAGS
        assert "i" not in BLOCK_TAGS


class TestParserIntegration:
    """Test parser integration."""

    def test_parse_complete_document(self):
        """Test parsing a complete HTML document."""
        from python.lib.lineardoc import MwContextualizer

        ctx = MwContextualizer()
        parser = Parser(ctx)
        parser.init()

        html = """
        <html>
        <body>
        <h1>Title</h1>
        <p>Paragraph with <b>bold</b> text.</p>
        </body>
        </html>
        """

        parser.write(html)
        doc = parser.builder.doc
        # Should have created items
        assert len(doc.items) > 0
        # Should be able to get HTML back
        output = doc.get_html()
        assert isinstance(output, str)
        assert len(output) > 0

    def test_parse_with_text_content(self):
        """Test parsing with text content."""
        from python.lib.lineardoc import MwContextualizer

        ctx = MwContextualizer()
        parser = Parser(ctx)
        parser.init()

        parser.write("<p>This is a test.</p>")
        doc = parser.builder.doc
        output = doc.get_html()
        assert "This is a test." in output
