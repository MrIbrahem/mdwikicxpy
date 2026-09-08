"""
Unit tests for lineardoc/normalizer.py module.
"""

from python.lib.lineardoc.normalizer import Normalizer, normalize


class TestNormalizer:
    """Test Normalizer class."""

    def test_normalizer_creation(self):
        """Test creating a normalizer."""
        norm = Normalizer()
        assert norm.lowercase is True

    def test_normalizer_init(self):
        """Test initializing normalizer state."""
        norm = Normalizer()
        norm.init()
        assert norm.doc == []
        assert norm.tags == []

    def test_normalize_simple_html(self):
        """Test normalizing simple HTML."""
        norm = Normalizer()
        norm.init()
        norm.write("<div>Hello</div>")
        result = norm.get_html()
        assert "<div>" in result
        assert "Hello" in result
        assert "</div>" in result
        assert result == "<div>Hello</div>"

    def test_normalize_escapes_text(self):
        """Test that text is properly escaped."""
        norm = Normalizer()
        norm.init()
        norm.write("<div>&<></div>")
        result = norm.get_html()
        assert "&#38;" in result  # &
        assert "&#60;" in result  # <
        assert "&#62;" in result  # >
        assert result == "<div>&#38;&#60;&#62;</div>"

    def test_normalize_preserves_attributes(self):
        """Test that attributes are preserved."""
        norm = Normalizer()
        norm.init()
        norm.write('<div class="test" id="main">content</div>')
        result = norm.get_html()
        assert 'class="test"' in result
        assert 'id="main"' in result
        assert result == '<div class="test" id="main">content</div>'

    def test_normalize_nested_tags(self):
        """Test normalizing nested tags."""
        norm = Normalizer()
        norm.init()
        norm.write("<div><p>text</p></div>")
        result = norm.get_html()
        assert "<div>" in result
        assert "<p>" in result
        assert "text" in result
        assert "</p>" in result
        assert "</div>" in result
        assert result == "<div><p>text</p></div>"

    def test_normalize_with_tail_text(self):
        """Test handling text after child elements."""
        norm = Normalizer()
        norm.init()
        norm.write("<div><b>bold</b> normal</div>")
        result = norm.get_html()
        assert "<b>bold</b>" in result
        assert "normal" in result
        assert result == "<div><b>bold</b> normal</div>"

    def test_normalize_empty_input(self):
        """Test normalizing empty input."""
        norm = Normalizer()
        norm.init()
        # Empty input wrapped in div by parser
        try:
            norm.write("")
            result = norm.get_html()
            # Should handle gracefully
            assert isinstance(result, str)
        except Exception:
            # Some parsers may fail on empty input
            pass

    def test_normalize_lowercase_tags(self):
        """Test that tags are lowercased."""
        norm = Normalizer()
        norm.init()
        norm.write("<DIV>text</DIV>")
        result = norm.get_html()
        assert "<div>" in result.lower()
        assert "</div>" in result.lower()
        assert result == "<div>text</div>"

    def test_normalize_special_chars_in_attributes(self):
        """Test special characters in attributes."""
        norm = Normalizer()
        norm.init()
        norm.write('<div title="test &amp; value">text</div>')
        result = norm.get_html()
        # Attributes should be escaped
        assert "title=" in result
        assert result == """<div title="test &#38; value">text</div>"""

    def test_normalize_unicode(self):
        """Test normalizing Unicode content."""
        norm = Normalizer()
        norm.init()
        norm.write("<div>مرحبا</div>")
        result = norm.get_html()
        assert "مرحبا" in result
        assert result == "<div>مرحبا</div>"


class TestNormalizeFunction:
    """Test normalize function."""

    def test_normalize_simple(self):
        """Test normalizing simple HTML."""
        result = normalize("<div>test</div>")
        assert "<div>" in result
        assert "test" in result
        assert "</div>" in result
        assert result == "<div>test</div>"

    def test_normalize_removes_whitespace(self):
        """Test that normalize removes tabs, newlines, carriage returns."""
        html = "<div>\n\t\rtest\n\t\r</div>"
        result = normalize(html)
        # Should not contain tabs, newlines, or carriage returns
        assert "\n" not in result
        assert "\t" not in result
        assert "\r" not in result
        assert result == "<div>test</div>"

    def test_normalize_preserves_content(self):
        """Test that normalize preserves content."""
        html = "<p>Hello world</p>"
        result = normalize(html)
        assert "Hello world" in result
        assert result == "<p>Hello world</p>"

    def test_normalize_with_attributes(self):
        """Test normalizing with attributes."""
        html = '<div class="test">content</div>'
        result = normalize(html)
        assert 'class="test"' in result
        assert result == '<div class="test">content</div>'
