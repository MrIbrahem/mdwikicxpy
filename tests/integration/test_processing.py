"""
Test the HTML processing pipeline.
"""

from pathlib import Path

from python.lib.processor import process_html


def run_processing_test(num):
    """Test HTML processing with a specific fixture file number."""
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    input_path = fixtures_dir / f"input_{num}.html"
    output_path = fixtures_dir / f"output_{num}.html"

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


def test_processing_1():
    run_processing_test(1)


def test_processing_2():
    run_processing_test(2)


def test_processing_3():
    run_processing_test(3)


def test_processing_4():
    run_processing_test(4)
