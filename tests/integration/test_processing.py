"""
Test the HTML processing pipeline.
"""

from pathlib import Path

import re
import pytest

from python.lib.processor import process_html

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

def normalize_test(html: str) -> str:
    """ """
    html = html.strip()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", "", html)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html


@pytest.mark.parametrize("num", [1, 2, 3, 4])
def test_run_processing_test(num: int):
    """Test HTML processing with a specific fixture file number."""
    test_path = FIXTURES_DIR / f"test{num}"
    input_path = test_path / "input.html"
    output_path = test_path / "output.html"

    with open(input_path, "r", encoding="utf-8") as f:
        input_html = f.read()

    # Process the input
    result = process_html(input_html)

    # Save result for inspection
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    # Validation
    assert "<section" in result, f"Result {num} should contain section tags"
    assert "cx-segment" in result, f"Result {num} should contain cx-segment spans"
    assert "data-segmentid" in result, f"Result {num} should contain segment IDs"
    assert len(result) > len(input_html) * 0.5, f"Result {num} should have reasonable size"


def test_process_html():
    """Test HTML processing with a specific fixture file number."""
    test_path = FIXTURES_DIR / "data-section-number"

    input_path = test_path / "test-data-section-number.html"
    expected_path = test_path / "result-data-section-number.html"

    output_path = test_path / "output.html"

    input_html = input_path.read_text(encoding="utf-8")

    # Process the input
    result = process_html(input_html)

    # Save result for inspection
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    expected_text = expected_path.read_text(encoding="utf-8")

    # Validation
    is_start = result.strip().startswith("<html")
    assert not is_start, "Result should not startswith <html tag"

    assert normalize_test(result) == normalize_test(expected_text) , "Result should match expected output"


def test_process_html_sections():
    """Test HTML processing with a specific fixture file number."""
    input_html = """
        <body>
            <h2 id="History">History</h2>
            <p id="mwUA">content</p>
            <p id="mwUB">content</p>
            <h3 id="History-16">16th century</h3>
            <p id="mwUC">content</p>
            <p id="mwUD">content</p>
        </body>
    """
    expected_text = """
    <body id="0">
        <section rel="cx:Section" id="cxSourceSection0" data-mw-section-number="1">
        <h2 id="0e769600933790607b2a13b33ddfad">
            <span class="cx-segment" data-segmentid="1">History</span>
        </h2>
        </section>
        <section rel="cx:Section" id="cxSourceSection1" data-mw-section-number="1"><p id="mwUA"><span class="cx-segment" data-segmentid="2">content</span></p>
        </section>
        <section rel="cx:Section" id="cxSourceSection2" data-mw-section-number="1"><p id="mwUB"><span class="cx-segment" data-segmentid="3">content</span></p>
        </section>
        <section rel="cx:Section" id="cxSourceSection3" data-mw-section-number="1"><h3 id="0311fc66ff8b0cf80103792799fe14"><span class="cx-segment" data-segmentid="4">16th century</span></h3>
        </section>
        <section rel="cx:Section" id="cxSourceSection4" data-mw-section-number="1"><p id="mwUC"><span class="cx-segment" data-segmentid="5">content</span></p>
        </section>
        <section rel="cx:Section" id="cxSourceSection5" data-mw-section-number="1"><p id="mwUD"><span class="cx-segment" data-segmentid="6">content</span></p>
        </section>
    </body>
    """
    # Process the input
    result = process_html(input_html)

    is_start = result.strip().startswith("<html")
    assert not is_start, "Result should not startswith <html tag"

    assert normalize_test(result) == normalize_test(expected_text) , "Result should match expected output"
