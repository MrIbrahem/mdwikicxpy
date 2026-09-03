"""
Unit tests for lineardoc/utils.py module.
"""
import pytest
from pathlib import Path

from python.lib.lineardoc import MwContextualizer, Parser
from python.lib.lineardoc.utils import is_ignorable_block

test_files = [
    Path(__file__).parent / "data" / "test-block-template-section-1.html",
    Path(__file__).parent / "data" / "test-block-template-section-2.html",
    Path(__file__).parent / "data" / "test-block-template-section-3.html",
    Path(__file__).parent / "data" / "test-block-template-section-4.html",
]


@pytest.mark.parametrize("test_file", test_files)
def test_is_ignorable_block(test_file):
    with open(test_file, "r", encoding="utf-8") as f:
        html = f.read()
    parser = Parser(MwContextualizer())

    parser.init()
    parser.write(html.strip())
    parsed_doc = parser.builder.doc
    result = is_ignorable_block(parsed_doc)
    assert result is True, f"Expected block to be ignorable for file: {test_file.name}"
