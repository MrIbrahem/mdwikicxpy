"""
Test the HTML processing pipeline.
"""

from pathlib import Path

import pytest

from python.lib.processor import process_html

@pytest.mark.parametrize("num", [1, 2, 3, 4])
def test_run_processing_test(num):
    """Test HTML processing with a specific fixture file number."""
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    test_path = fixtures_dir / f"test{num}"
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
