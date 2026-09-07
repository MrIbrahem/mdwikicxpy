"""
Comprehensive test suite for the CX HTML processing pipeline.
"""

from python.lib.processor import process_html


def test_basic_html_processing():
    """Test basic HTML processing."""

    html = "<body><h2>test</h2><p>This is a test. This is another sentence.</p></body>"
    result = process_html(html)

    assert "cx-segment" in result, "Should contain segments"
    assert "data-segmentid" in result, "Should contain segment IDs"
    assert "<section" in result, "Should contain section wrapper"


def test_mediawiki_elements():
    """Test MediaWiki-specific elements."""

    html = """
    <html>
    <body>
    <h2>Heading</h2>
    <p>Paragraph with <a href="/wiki/Link" rel="mw:WikiLink">a link</a>.</p>
    <figure>
        <img src="image.jpg" />
        <figcaption>Caption text.</figcaption>
    </figure>
    </body>
    </html>
    """

    result = process_html(html)

    assert "cx-link" in result, "Should process WikiLinks"
    assert "data-linkid" in result, "Should add link IDs"
    assert "cx:Figure" in result, "Should mark figures"


def test_section_wrapping():
    """Test section wrapping."""

    html = """
    <html>
    <body>
    <h2>Section 1</h2>
    <p>Content 1.</p>
    <h2>Section 2</h2>
    <p>Content 2.</p>
    </body>
    </html>
    """

    result = process_html(html)

    section_count = result.count("<section")
    assert section_count >= 2, f"Should have at least 2 sections, got {section_count}"
    assert "cx:Section" in result, "Should mark sections"


def test_segmentation():
    """Test text segmentation."""

    html = """
    <html>
    <body>
    <p>First sentence. Second sentence. Third sentence!</p>
    </body>
    </html>
    """

    result = process_html(html)

    segment_count = result.count("cx-segment")
    assert segment_count >= 2, f"Should have at least 2 segments, got {segment_count}"


def test_reference_handling():
    """Test reference handling."""

    html = """
    <html>
    <body>
    <p>Text with reference<sup class="reference"><a href="#cite_note-1">[1]</a></sup>.</p>
    </body>
    </html>
    """

    result = process_html(html)

    # References should be preserved as inline content
    assert "reference" in result, "Should preserve references"


def test_empty_input():
    """Test empty input handling."""

    html = ""
    _result = process_html(html)


def test_complex_nesting():
    """Test complex nested structures."""

    html = """
    <html>
    <body>
    <div>
        <p>Outer paragraph.</p>
        <blockquote>
            <p>Quoted text with <b>bold</b> and <i>italic</i>.</p>
        </blockquote>
        <ul>
            <li>Item 1.</li>
            <li>Item 2.</li>
        </ul>
    </div>
    </body>
    </html>
    """

    result = process_html(html)

    # Tags should be preserved (either as-is or escaped)
    assert "<b>" in result or "bold" in result, "Should preserve bold content"
    assert "<i>" in result or "italic" in result, "Should preserve italic content"
    assert "<li" in result, "Should preserve list items"
    assert "Item 1" in result, "Should preserve list content"
