"""
Unit tests for lineardoc/text_chunk.py module.
"""

import os
import sys

import pytest
from python.lib.lineardoc.text_chunk import TextChunk


class TestTextChunk:
    """Test text_chunk class."""

    def test_text_chunk_creation_simple(self):
        """Test creating a simple text_chunk."""
        chunk = TextChunk("hello", [])
        assert chunk.text == "hello"
        assert chunk.tags == []
        assert chunk.inline_content is None

    def test_text_chunk_creation_with_tags(self):
        """Test creating text_chunk with tags."""
        tags = [{"name": "b"}, {"name": "i"}]
        chunk = TextChunk("bold italic text", tags)
        assert chunk.text == "bold italic text"
        assert chunk.tags == tags
        assert chunk.inline_content is None

    def test_text_chunk_creation_with_inline_content(self):
        """Test creating text_chunk with inline content."""
        tags = [{"name": "span"}]
        inline_content = {"name": "img", "attributes": {"src": "test.jpg"}}
        chunk = TextChunk("", tags, inline_content)
        assert chunk.text == ""
        assert chunk.tags == tags
        assert chunk.inline_content == inline_content

    def test_text_chunk_empty_text(self):
        """Test creating text_chunk with empty text."""
        chunk = TextChunk("", [])
        assert chunk.text == ""
        assert len(chunk.text) == 0

    def test_text_chunk_tags_with_attributes(self):
        """Test creating text_chunk with tags containing attributes."""
        tags = [{"name": "a", "attributes": {"href": "http://example.com", "class": "link"}}]
        chunk = TextChunk("link text", tags)
        assert chunk.text == "link text"
        assert len(chunk.tags) == 1
        assert chunk.tags[0]["name"] == "a"
        assert chunk.tags[0]["attributes"]["href"] == "http://example.com"

    def test_text_chunk_nested_tags(self):
        """Test text_chunk with nested tag structure."""
        tags = [{"name": "b"}, {"name": "i"}, {"name": "u"}]
        chunk = TextChunk("formatted", tags)
        assert len(chunk.tags) == 3
        assert chunk.tags[0]["name"] == "b"
        assert chunk.tags[1]["name"] == "i"
        assert chunk.tags[2]["name"] == "u"

    def test_text_chunk_unicode_text(self):
        """Test text_chunk with Unicode text."""
        chunk = TextChunk("مرحبا العالم", [])
        assert chunk.text == "مرحبا العالم"

        chunk2 = TextChunk("こんにちは世界", [])
        assert chunk2.text == "こんにちは世界"

        chunk3 = TextChunk("Hello 🌍", [])
        assert chunk3.text == "Hello 🌍"

    def test_text_chunk_special_characters(self):
        """Test text_chunk with special characters."""
        chunk = TextChunk("Text with & < > \" ' characters", [])
        assert "&" in chunk.text
        assert "<" in chunk.text
        assert ">" in chunk.text

    def test_text_chunk_whitespace(self):
        """Test text_chunk with various whitespace."""
        chunk1 = TextChunk("  spaces  ", [])
        assert chunk1.text == "  spaces  "

        chunk2 = TextChunk("\t\ttabs\t\t", [])
        assert chunk2.text == "\t\ttabs\t\t"

        chunk3 = TextChunk("\n\nlines\n\n", [])
        assert chunk3.text == "\n\nlines\n\n"
