"""
Unit tests for lineardoc/Utils.py module.
"""

import json
import re
from pathlib import Path

import pytest
from python.lib.lineardoc import Doc, MwContextualizer, Parser
from python.lib.mw.mw_page_loader import MWPageLoader
from python.lib.segmentation import CXSegmenter

cx_segmenter_tests_path = Path(__file__).parent / "SegmentationTests.json"

alltests = {}
with open(cx_segmenter_tests_path, "r", encoding="utf-8") as f:
    alltests = json.load(f)

test_params = [{"lang": lang, **test_case} for lang, cases in alltests.items() for test_case in cases]


def normalize_test(html: str) -> str:
    """ """
    # html = normalize(html)
    html = html.strip()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", " ", html)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    # HTML void elements may be serialized as either ``<img/>`` or
    # ``<img />`` without changing the document structure.
    html = re.sub(r"\s*/>", "/>", html)
    html = re.sub(r">\s*<", ">\n<", html)
    return html


def get_parsed_doc(content, config=None, options=None) -> Doc:
    parser = Parser(MwContextualizer(config=config), options=options)
    parser.init()
    parser.write(content)
    return parser.builder.doc


@pytest.mark.parametrize("test_case", test_params, ids=lambda x: x["source"])
@pytest.mark.integration
def test_cx_segmenter(test_case: dict[str, str]):
    test_desc = test_case["desc"]
    date_path = Path(__file__).parent / "data"
    output_path = Path(__file__).parent / "output"
    output_path.mkdir(parents=True, exist_ok=True)

    source_path = date_path / test_case["source"]
    expected_path = date_path / test_case["result"]

    source_text = source_path.read_text(encoding="utf-8")
    expected_text = expected_path.read_text(encoding="utf-8")

    """
    doc = MWPageLoader().get_page(
        source_html=source_text,
        lang=test_case["lang"],
        sort_attrs=True,
        wrap_sections=False,
    )
    """
    options = {
        "wrapSections": True,
        "isolateSegments": False,
        "sort_attrs": True,
    }
    parsed_doc = get_parsed_doc(source_text, options=options)
    segmenter = CXSegmenter()
    doc = segmenter.segment(parsed_doc, test_case["lang"])
    result = doc.get_html()

    normalized_result = normalize_test(result)

    output_path = output_path / test_case["result"]

    output_path.write_text(normalized_result, encoding="utf-8")

    # expected
    expected_result_data = expected_text
    # expected_result_data = segmenter.segment(get_parsed_doc(expected_text), test_case["lang"]).get_html()

    expected_result_data = normalize_test(expected_result_data)

    # if normalized_result != expected_result_data: print(f"{doc.dump_xml()}")

    assert normalized_result == expected_result_data, f"{source_path.name}: {test_desc}"

    if normalized_result == expected_result_data:
        expected_path.write_text(expected_result_data, encoding="utf-8")


def test_cx_segmenter_1():

    source_text = "<p>Some in the UK. Others in the US.</p>"

    expected_text = """
        <p id="0">
            <span class="cx-segment" data-segmentid="1">Some in the UK. </span>
            <span class="cx-segment" data-segmentid="2">Others in the US.</span>
        </p>
    """

    doc = MWPageLoader().get_page(
        source_html=source_text,
        lang="en",
        sort_attrs=True,
        wrap_sections=False,
    )
    result = doc.get_html()

    normalized_result = normalize_test(result)

    expected_result_data = normalize_test(expected_text)

    assert normalized_result == expected_result_data
