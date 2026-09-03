"""
Unit tests for lineardoc/utils.py module.
"""

import json
import re
from pathlib import Path

import pytest
from python.lib.lineardoc import MwContextualizer, Normalizer, Parser
from python.lib.segmentation import CXSegmenter

cx_segmenter_tests_path = Path(__file__).parent / "SegmentationTests.json"

alltests = {}
with open(cx_segmenter_tests_path, "r", encoding="utf-8") as f:
    alltests = json.load(f)


def get_parsed_doc(content):
    parser = Parser(MwContextualizer())

    parser.init()
    parser.write(content.strip())
    parsed_doc = parser.builder.doc
    return parsed_doc


def normalize(html):
    normalizer = Normalizer()
    normalizer.init()
    normalizer.write(re.sub(r"[\t\r\n]+", "", html))  # html.replace(/[\t\r\n]+/gm, '' )
    return normalizer.get_html()


test_params = [(lang, test_case) for lang, cases in alltests.items() for test_case in cases]


@pytest.mark.parametrize("lang, test_case", test_params)
def test_cx_segmenter(lang, test_case):
    date_path = Path(__file__).parent / "data"
    output_path = Path(__file__).parent / "output"

    with open(date_path / test_case["source"], "r", encoding="utf-8") as f:
        test_data = f.read()

    parsed_doc = get_parsed_doc(test_data)
    segmenter = CXSegmenter()
    segmented_linear_doc = segmenter.segment(parsed_doc, lang)

    result = segmented_linear_doc.get_html()
    normalized_result = normalize(result)

    with open(date_path / test_case["result"], "r", encoding="utf-8") as f:
        expected_result_data = normalize(f.read())

    if expected_result_data != normalized_result:
        with open(output_path / test_case["result"], "w", encoding="utf-8") as f:
            f.write(result)

    assert normalized_result == expected_result_data, f"{test_case['source']}: {test_case['desc'] or ''}"
