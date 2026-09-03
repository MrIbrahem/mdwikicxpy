#!/usr/bin/env python3
"""
Comprehensive test suite for the CX HTML processing pipeline.
"""

import json
import os
import sys

from python.lib.lineardoc import Doc, Parser, MwContextualizer, TextBlock
from python.lib.processor import process_html
from python.lib.segmentation import CXSegmenter


def test_basic_html_processing():
    """Test basic HTML processing."""
    print("Testing basic HTML processing...")

    html = "<p>This is a test. This is another sentence.</p>"
    result = process_html(html)

    assert "cx-segment" in result, "Should contain segments"
    assert "data-segmentid" in result, "Should contain segment IDs"
    assert "<section" in result, "Should contain section wrapper"

    print("✓ Basic HTML processing works")


def test_mediawiki_elements():
    """Test MediaWiki-specific elements."""
    print("\nTesting MediaWiki elements...")

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

    print("✓ MediaWiki elements processed correctly")


def test_section_wrapping():
    """Test section wrapping."""
    print("\nTesting section wrapping...")

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

    print(f"✓ Section wrapping works ({section_count} sections)")


def test_segmentation():
    """Test text segmentation."""
    print("\nTesting segmentation...")

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

    print(f"✓ Segmentation works ({segment_count} segments)")


def test_reference_handling():
    """Test reference handling."""
    print("\nTesting reference handling...")

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

    print("✓ Reference handling works")


def test_empty_input():
    """Test empty input handling."""
    print("\nTesting empty input...")

    html = ""
    try:
        result = process_html(html)
        # Should not crash
        print("✓ Empty input handled gracefully")
    except Exception as e:
        print(f"✗ Failed with: {e}")
        raise


def test_complex_nesting():
    """Test complex nested structures."""
    print("\nTesting complex nesting...")

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

    print("✓ Complex nesting handled correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("CX HTML Processing Pipeline - Comprehensive Test Suite")
    print("=" * 60)

    try:
        test_basic_html_processing()
        test_mediawiki_elements()
        test_section_wrapping()
        test_segmentation()
        test_reference_handling()
        test_empty_input()
        test_complex_nesting()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"TESTS FAILED ✗: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
