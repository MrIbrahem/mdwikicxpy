"""
Unit tests for lineardoc/utils.py module.
"""

import json
from pathlib import Path

import pytest
from python.lib.lineardoc import Doc, MwContextualizer, Parser
from python.lib.segmentation import CXSegmenter
from python.lib.processor import normalize

cx_segmenter_tests_path = Path(__file__).parent / "SegmentationTests.json"

alltests = {}
with open(cx_segmenter_tests_path, "r", encoding="utf-8") as f:
    alltests = json.load(f)


def get_parsed_doc(content) -> Doc:
    parser = Parser(MwContextualizer())
    parser.init()
    parser.write(content.strip())
    parsed_doc = parser.builder.doc
    return parsed_doc

test_params = [(lang, test_case) for lang, cases in alltests.items() for test_case in cases]


@pytest.mark.parametrize("lang, test_case", test_params)
@pytest.mark.integration
def test_cx_segmenter(lang, test_case):
    date_path = Path(__file__).parent / "data"
    output_path = Path(__file__).parent / "output"
    output_path.mkdir(parents=True, exist_ok=True)

    with open(date_path / test_case["source"], "r", encoding="utf-8") as f:
        test_data = f.read()

    segmenter = CXSegmenter()

    if not segmenter.is_language_supported(lang):
        pytest.skip(f"Language {lang} not supported")

    result = segmenter.segment(get_parsed_doc(test_data), lang).get_html()

    normalized_result = normalize(result)

    with open(output_path / test_case["result"], "w", encoding="utf-8") as f:
        f.write(result)

    with open(date_path / test_case["result"], "r", encoding="utf-8") as f:
        expected_text = f.read()

    # expected
    expected_result_data = normalize(segmenter.segment(get_parsed_doc(expected_text), lang).get_html())

    # assert normalize(expected_text) == expected_result_data

    assert normalized_result == expected_result_data, f"{test_case['source']}: {test_case['desc'] or ''}"
