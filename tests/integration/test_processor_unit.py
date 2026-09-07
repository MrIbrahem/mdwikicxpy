"""
Unit tests for processor.py module.
"""

import re

from python.lib.lineardoc import MwContextualizer, Parser
from python.lib.segmentation import CXSegmenter


def normalize_test(html: str) -> str:
    """ """
    html = html.strip()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", "", html)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html


def test_process_html_simple():
    """Test processing simple HTML."""
    html = "<p>This is a test.</p>"

    parser = Parser(
        contextualizer=MwContextualizer({"removableSections": {}}),
        options={"wrapSections": False},
        sort_attrs=True,
    )

    parser.init()
    parser.write(html)
    parsed_doc = parser.create_wrapped_doc()

    # segmented_doc = CXSegmenter().segment(parsed_doc, "en")

    result = parsed_doc.get_html()

    assert normalize_test(result) == normalize_test(
    """
        <html>
            <body>
                <section rel="cx:Section">
                    <p>This is a test.</p>
                </section>
            </body>
        </html>
    """
    )


def test_process_html_simple2():
    """Test processing simple HTML."""
    html = "<p>This is a test.</p>"

    parser = Parser(
        contextualizer=MwContextualizer({"removableSections": {}}),
        options={"wrapSections": True},
        sort_attrs=True,
    )

    parser.init()
    parser.write(html)
    parsed_doc = parser.create_wrapped_doc()

    segmented_doc = CXSegmenter().segment(parsed_doc, "en")

    result = segmented_doc.get_html()


    assert normalize_test(result) == normalize_test(
    """
        <html id="0">
            <body id="1">
                <section data-mw-section-number="0" id="cxSourceSection0" rel="cx:Section">
                    <p id="2"><span class="cx-segment" data-segmentid="3">This is a test.</span></p>
                </section>
            </body>

        </html>
    """
    )
