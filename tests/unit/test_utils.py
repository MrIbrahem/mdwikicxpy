"""
Unit tests for lineardoc/utils.py module.
"""

import os
import sys

import pytest
from python.lib.lineardoc import utils
from python.lib.lineardoc.text_chunk import TextChunk


class TestEscapeFunctions:
    """Test HTML escape functions."""

    def test_esc_basic(self):
        """Test basic text escaping."""
        assert utils.esc("hello") == "hello"
        assert utils.esc("hello & goodbye") == "hello &#38; goodbye"
        assert utils.esc("hello < world") == "hello &#60; world"
        assert utils.esc("hello > world") == "hello &#62; world"

    def test_esc_multiple_chars(self):
        """Test escaping multiple special characters."""
        assert utils.esc("<div>&text</div>") == "&#60;div&#62;&#38;text&#60;/div&#62;"
        assert utils.esc("a & b < c > d") == "a &#38; b &#60; c &#62; d"

    def test_esc_empty_string(self):
        """Test escaping empty string."""
        assert utils.esc("") == ""

    def test_esc_attr_basic(self):
        """Test attribute escaping."""
        assert utils.esc_attr("hello") == "hello"
        assert utils.esc_attr("hello & goodbye") == "hello &#38; goodbye"

    def test_esc_attr_quotes(self):
        """Test escaping quotes in attributes."""
        # Note: & in numeric entities gets escaped too (double-escaping)
        assert utils.esc_attr('say "hello"') == "say &#34;hello&#34;"
        assert utils.esc_attr("it's fine") == "it&#39;s fine"

    def test_esc_attr_all_special_chars(self):
        """Test escaping all special characters in attributes."""
        # Note: The order matters - & is replaced first, affecting numeric entities
        result = utils.esc_attr("\"'&<>")
        assert result == "&#34;&#39;&#38;&#60;&#62;"

    def test_esc_attr_number(self):
        """Test escaping number values."""
        assert utils.esc_attr(42) == "42"
        assert utils.esc_attr(3.14) == "3.14"


class TestTagHtmlGeneration:
    """Test HTML tag generation functions."""

    def test_get_open_tag_html_simple(self):
        """Test generating simple open tag."""
        tag = {"name": "div"}
        assert utils.get_open_tag_html(tag) == "<div>"

    def test_get_open_tag_html_with_attributes(self):
        """Test generating open tag with attributes."""
        tag = {"name": "div", "attributes": {"class": "container", "id": "main"}}
        result = utils.get_open_tag_html(tag)
        # Attributes are sorted alphabetically
        assert result == '<div class="container" id="main">'

    def test_get_open_tag_html_with_special_chars(self):
        """Test generating open tag with special characters in attributes."""
        tag = {"name": "div", "attributes": {"data-value": '<test & "value">'}}
        result = utils.get_open_tag_html(tag)
        # Note: esc_attr double-escapes & in numeric entities
        assert '<div data-value="' in result
        assert "&#60;test" in result  # <
        assert "&#38;" in result  # &
        assert "&#62;" in result  # >

    def test_get_open_tag_html_self_closing(self):
        """Test generating self-closing tag."""
        tag = {"name": "br", "isSelfClosing": True}
        assert utils.get_open_tag_html(tag) == "<br />"

    def test_get_close_tag_html_simple(self):
        """Test generating simple close tag."""
        tag = {"name": "div"}
        assert utils.get_close_tag_html(tag) == "</div>"

    def test_get_close_tag_html_self_closing(self):
        """Test generating close tag for self-closing element."""
        tag = {"name": "br", "isSelfClosing": True}
        assert utils.get_close_tag_html(tag) == ""


class Testclone_open_tag:
    """Test tag cloning function."""

    def test_clone_simple_tag(self):
        """Test cloning simple tag."""
        tag = {"name": "div"}
        cloned = utils.clone_open_tag(tag)
        assert cloned["name"] == "div"
        assert cloned["attributes"] == {}

    def test_clone_tag_with_attributes(self):
        """Test cloning tag with attributes."""
        tag = {"name": "div", "attributes": {"class": "test", "id": "main"}}
        cloned = utils.clone_open_tag(tag)
        assert cloned["name"] == "div"
        assert cloned["attributes"] == {"class": "test", "id": "main"}

    def test_clone_tag_independence(self):
        """Test that cloned tag is independent from original."""
        tag = {"name": "div", "attributes": {"class": "original"}}
        cloned = utils.clone_open_tag(tag)
        cloned["attributes"]["class"] = "modified"
        # Original should remain unchanged
        assert tag["attributes"]["class"] == "original"


class TestTagTypeDetection:
    """Test tag type detection functions."""

    def test_is_inline_empty_tag_br(self):
        """Test detecting br as inline empty tag."""
        assert utils.is_inline_empty_tag("br") is True

    def test_is_inline_empty_tag_img(self):
        """Test detecting img as inline empty tag."""
        assert utils.is_inline_empty_tag("img") is True

    def test_is_inline_empty_tag_div(self):
        """Test detecting div as not inline empty tag."""
        assert utils.is_inline_empty_tag("div") is False

    def test_is_inline_empty_tag_span(self):
        """Test detecting span as not inline empty tag."""
        assert utils.is_inline_empty_tag("span") is False

    def test_is_segment(self):
        """Test detecting segment tags."""
        tag = {"name": "span", "attributes": {"class": "cx-segment"}}
        assert utils.is_segment(tag) is True

    def test_is_segment_negative(self):
        """Test detecting non-segment tags."""
        tag = {"name": "span", "attributes": {"class": "other"}}
        assert utils.is_segment(tag) is False

    def test_is_reference(self):
        """Test detecting reference tags."""
        # Reference with mw:Extension/ref
        tag = {"name": "span", "attributes": {"typeof": "mw:Extension/ref"}}
        assert utils.is_reference(tag) is True

    def test_is_reference_sup(self):
        """Test detecting sup reference tags."""
        tag = {"name": "sup", "attributes": {"class": "reference"}}
        assert utils.is_reference(tag) is True

    def test_is_reference_negative(self):
        """Test detecting non-reference tags."""
        tag = {"name": "span", "attributes": {"class": "normal"}}
        assert utils.is_reference(tag) is False

    def test_is_transclusion(self):
        """Test detecting transclusion tags."""
        tag = {"name": "div", "attributes": {"typeof": "mw:Transclusion"}}
        assert utils.is_transclusion(tag) is True

    def test_is_transclusion_negative(self):
        """Test detecting non-transclusion tags."""
        tag = {"name": "div", "attributes": {"class": "normal"}}
        assert utils.is_transclusion(tag) is False


class Testdump_tags:
    """Test dump_tags function."""

    def test_dump_tags_empty(self):
        """Test dumping empty tag array."""
        result = utils.dump_tags([])
        assert result == ""

    def test_dump_tags_single(self):
        """Test dumping single tag."""
        tags = [{"name": "b"}]
        result = utils.dump_tags(tags)
        assert "b" in result

    def test_dump_tags_multiple(self):
        """Test dumping multiple tags."""
        tags = [{"name": "b"}, {"name": "i", "attributes": {"class": "test"}}]
        result = utils.dump_tags(tags)
        assert "b" in result
        assert "i" in result
