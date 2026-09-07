"""
Unit tests for lineardoc/Utils.py module.
"""

import json
import re
from pathlib import Path

import pytest
from python.lib.lineardoc import Doc, MwContextualizer, Parser, normalize
from python.lib.segmentation import CXSegmenter
from python.lib.mw.mw_page_loader import MWPageLoader

cx_segmenter_tests_path = Path(__file__).parent / "SegmentationTests.json"

alltests = {}
with open(cx_segmenter_tests_path, "r", encoding="utf-8") as f:
    alltests = json.load(f)

test_params = [{"lang":lang, **test_case} for lang, cases in alltests.items() for test_case in cases]


def normalize_test(html: str) -> str:
    """ """
    html = normalize(html)
    html = html.strip()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", " ", html)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html


def get_parsed_doc(content) -> Doc:
    parser = Parser(MwContextualizer())
    parser.init()
    parser.write(content.strip())
    parsed_doc = parser.builder.doc
    return parsed_doc

def get_result(lang, test_data):
    segmenter = CXSegmenter()
    result = segmenter.segment(get_parsed_doc(test_data), lang).get_html()
    return result


def get_result1(lang, test_data):
    return MWPageLoader().get_page(
        source_html=test_data,
        lang=lang,
    )


@pytest.mark.parametrize("test_case", test_params, ids=lambda x: x["source"])
@pytest.mark.integration
def test_cx_segmenter(test_case):

    date_path = Path(__file__).parent / "data"
    output_path = Path(__file__).parent / "output"
    output_path.mkdir(parents=True, exist_ok=True)

    source_path = date_path / test_case["source"]
    expected_path = date_path / test_case["result"]

    test_data = source_path.read_text(encoding="utf-8")
    expected_text = expected_path.read_text(encoding="utf-8")

    result = get_result(test_case["lang"], test_data)

    normalized_result = normalize_test(result)

    output_path = output_path / test_case["result"]

    result2 = re.sub(r">\s*<", ">\n<", result)
    output_path.write_text(result2, encoding="utf-8")

    # expected
    expected_result_data = expected_text
    # expected_result_data = segmenter.segment(get_parsed_doc(expected_text), lang).get_html()

    expected_result_data = normalize_test(expected_result_data)

    assert normalized_result == expected_result_data, f"{test_case['source']}: {test_case['desc'] or ''}"
