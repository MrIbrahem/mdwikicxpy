"""
Test the HTML processing pipeline.
"""

import re
from pathlib import Path

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

    assert normalize_test(result) == normalize_test(expected_text), "Result should match expected output"
