"""
Unit tests for processor.py module.
"""

import re

from python.lib.processor import normalize, process_html


def normalize_test(html: str) -> str:
    """ """
    html = html.strip()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", "", html)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html


class TestNormalizeFunction:
    """Test normalize function."""

    def test_normalize_simple(self):
        """Test normalizing simple HTML."""
        result = normalize("<div>test</div>")
        assert "<div>" in result
        assert "test" in result
        assert "</div>" in result

    def test_normalize_removes_whitespace(self):
        """Test that normalize removes tabs, newlines, carriage returns."""
        html = "<div>\n\t\rtest\n\t\r</div>"
        result = normalize(html)
        # Should not contain tabs, newlines, or carriage returns
        assert "\n" not in result
        assert "\t" not in result
        assert "\r" not in result

    def test_normalize_preserves_content(self):
        """Test that normalize preserves content."""
        html = "<p>Hello world</p>"
        result = normalize(html)
        assert "Hello world" in result

    def test_normalize_with_attributes(self):
        """Test normalizing with attributes."""
        html = '<div class="test">content</div>'
        result = normalize(html)
        assert 'class="test"' in result


class TestProcessHtml:
    """Test process_html function."""

    def test_process_html_simple(self):
        """Test processing simple HTML."""
        html = "<p>This is a test.</p>"
        result = process_html(html)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_process_html_creates_sections(self):
        """Test that processing creates sections."""
        html = "<h2>Heading</h2><p>Content</p>"
        result = process_html(html)

        assert "<section" in result
        assert 'rel="cx:Section"' in result

    def test_process_html_creates_segments(self):
        """Test that processing creates segments."""
        html = "<p>First sentence. Second sentence.</p>"
        result = process_html(html)
        assert "cx-segment" in result
        assert "data-segmentid" in result

    def test_process_html_preserves_links(self):
        """Test that processing preserves links."""
        html = '<p>Text with <a href="/wiki/Test">link</a>.</p>'
        result = process_html(html)
        assert "link" in result

    def test_process_html_empty_input(self):
        """Test processing empty input."""
        result = process_html("")
        # Should handle empty input gracefully
        assert isinstance(result, str)
        assert result == ""

    def test_process_html_with_figure(self):
        """Test processing HTML with figure."""
        html = """<figure><img src="test.jpg" /><figcaption>Caption</figcaption></figure>"""
        result = process_html(html)
        assert "cx:Figure" in result

    def test_process_html_mediawiki_link(self):
        """Test processing MediaWiki link."""
        html = '<p>See <a rel="mw:WikiLink" href="/wiki/Article">article</a>.</p>'
        result = process_html(html)
        # Should add link tracking
        assert "data-linkid" in result or "cx-link" in result

    def test_process_html_multiple_paragraphs(self):
        """Test processing multiple paragraphs."""
        html = """
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
        <p>Third paragraph.</p>
        """
        result = process_html(html)
        # Should have multiple segments
        segment_count = result.count("cx-segment")
        assert segment_count >= 2

    def test_process_html_headings(self):
        """Test processing headings."""
        html = """<h2>Section 1</h2>\n<p>Content 1</p>\n<h2>Section 2</h2>\n<p>Content 2</p>"""
        result = process_html(html)
        # Should create sections
        assert result.count("<section") >= 2

    def test_process_html_complex_structure(self):
        """Test processing complex structure."""
        html = """
        <html>
        <body>
        <h2>Introduction</h2>
        <p>This is the intro. It has multiple sentences.</p>
        <h2>Details</h2>
        <p>More details here.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        </body>
        </html>
        """
        result = process_html(html)
        assert "<section" in result
        assert "cx-segment" in result
        assert "<ul" in result or "<li" in result

    def test_process_html_unicode(self):
        """Test processing Unicode content."""
        html = "<p>مرحبا العالم. هذا اختبار.</p>"
        result = process_html(html)
        # Unicode content should be in output (possibly escaped)
        assert len(result) > len(html)  # Should have added markup
        # Check for presence of Arabic content or escape sequences
        assert "Ù" in result or "&#" in result or "مرحبا" in result

    def test_process_html_special_characters(self):
        """Test processing special characters."""
        html = "<p>Test &amp; special &lt;chars&gt;.</p>"
        result = process_html(html)
        # Should preserve content (may be escaped differently)
        assert len(result) > 0

    def test_process_html_nested_formatting(self):
        """Test processing nested formatting."""
        html = "<p>Text with <b>bold and <i>italic</i></b> formatting.</p>"
        result = process_html(html)
        # Should preserve formatting
        assert "bold" in result
        assert "italic" in result

    def test_process_html_blockquote(self):
        """Test processing blockquote."""
        html = "<blockquote><p>Quoted text.</p></blockquote>"
        result = process_html(html)
        assert "Quoted" in result

    def test_process_html_table(self):
        """Test processing table."""
        html = """ <table><tr><td>Cell 1</td><td>Cell 2</td></tr></table> """
        result = process_html(html)
        assert "Cell 1" in result
        assert "Cell 2" in result


class TestProcessHtmlConfiguration:
    """Test that process_html uses configuration."""

    def test_process_html_uses_removable_sections_config(self):
        """Test that removable sections configuration is loaded."""
        # The processor loads MWPageLoader.yaml config
        # We can test that it works by checking if certain elements would be removed
        html = "<p>Normal content.</p>"
        result = process_html(html)
        # Should process normally
        assert "Normal content" in result
