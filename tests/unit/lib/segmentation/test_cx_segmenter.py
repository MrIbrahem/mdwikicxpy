"""
Unit tests for lineardoc/Utils.py module.
"""

import json
import re
from pathlib import Path

import pytest
from python.lib.lineardoc import Doc, MwContextualizer, Parser, normalize
from python.lib.mw.mw_page_loader import MWPageLoader, removable_sections
from python.lib.segmentation import CXSegmenter

cx_segmenter_tests_path = Path(__file__).parent / "SegmentationTests.json"

alltests = {}
with open(cx_segmenter_tests_path, "r", encoding="utf-8") as f:
    alltests = json.load(f)

test_params = [{"lang": lang, **test_case} for lang, cases in alltests.items() for test_case in cases]


def normalize_test(html: str) -> str:
    """Normalize HTML using normalizer module."""
    cleaned = re.sub(r"<span[^>]*class=\"Z3988\"[^>]*>.*?</span>", "", html, flags=re.DOTALL)
    cleaned = re.sub(r">\s+<", "><", cleaned.strip().rstrip('"').strip())
    cleaned = cleaned.replace("&nbsp;", "\u00a0")
    return normalize(cleaned)


def get_parsed_doc(content, config=None) -> Doc:
    parser = Parser(MwContextualizer(config=config))
    parser.init()
    parser.write(content)
    return parser.builder.doc


def get_result1(lang, source_text):
    segmenter = CXSegmenter()
    result = segmenter.segment(get_parsed_doc(source_text), lang).get_html()
    return result


@pytest.mark.parametrize("test_case", test_params, ids=lambda x: x["source"])
@pytest.mark.integration
def test_cx_segmenter(test_case):

    date_path = Path(__file__).parent / "data"
    output_path = Path(__file__).parent / "output"
    output_path.mkdir(parents=True, exist_ok=True)

    source_path = date_path / test_case["source"]
    expected_path = date_path / test_case["result"]

    source_text = source_path.read_text(encoding="utf-8")
    expected_text = expected_path.read_text(encoding="utf-8")

    cfg = {"removableSections": removable_sections} if test_case["source"] == "test-T253501.html" else None
    parsed_doc = get_parsed_doc(source_text, config=cfg)
    segmenter = CXSegmenter()
    doc = segmenter.segment(parsed_doc, test_case["lang"])
    result = doc.get_html()

    normalized_result = normalize_test(result)

    output_path = output_path / test_case["result"]

    result2 = re.sub(r">\s*<", ">\n<", result)
    output_path.write_text(result2, encoding="utf-8")

    # expected
    expected_result_data = normalize_test(expected_text)

    if normalized_result != expected_result_data:
        print(f"{doc.dump_xml()}")

    assert normalized_result == expected_result_data, f"{test_case['source']}: {test_case['desc'] or ''}"


def test_cx_segmenter_1():

    source_text = "<p>Some in the UK. Others in the US.</p>"

    expected_text = """
        <p id="0">
            <span class="cx-segment" data-segmentid="1">Some in the UK. </span>
            <span class="cx-segment" data-segmentid="2">Others in the US.</span>
        </p>
    """

    parsed_doc = get_parsed_doc(source_text)
    segmenter = CXSegmenter()
    doc = segmenter.segment(parsed_doc, "en")
    result = doc.get_html()

    normalized_result = normalize_test(result)

    expected_result_data = normalize_test(expected_text)

    assert normalized_result == expected_result_data
