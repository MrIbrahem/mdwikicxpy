"""
Unit tests for processor.py module.
"""

import re

from python.lib.lineardoc import MwContextualizer, Parser
from python.lib.processor import process_html
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
        options={"wrapSections": False, "isolateSegments": False},
        sort_attrs=True,
    )

    parser.init()
    parser.write(html)
    parsed_doc = parser.builder.doc
    parsed_doc = parsed_doc.wrap_sections()

    # segmented_doc = CXSegmenter().segment(parsed_doc, "en")

    result = parsed_doc.get_html()

    assert normalize_test(result) == normalize_test("""
        <html>
            <body>
                <section rel="cx:Section">
                    <p>This is a test.</p>
                </section>
            </body>
        </html>
    """)


def test_process_html_simple2():
    """Test processing simple HTML."""
    html = "<p>This is a test.</p>"

    parser = Parser(
        contextualizer=MwContextualizer({"removableSections": {}}),
        options={"wrapSections": True, "isolateSegments": False},
        sort_attrs=True,
    )

    parser.init()
    parser.write(html)
    parsed_doc = parser.builder.doc
    parsed_doc = parsed_doc.wrap_sections()

    segmented_doc = CXSegmenter().segment(parsed_doc, "en")

    result = segmented_doc.get_html()

    assert normalize_test(result) == normalize_test("""
        <html id="0">
            <body id="1">
                <section data-mw-section-number="0" id="cxSourceSection0" rel="cx:Section">
                    <p id="2"><span class="cx-segment" data-segmentid="3">This is a test.</span></p>
                </section>
            </body>

        </html>
    """)


def test_process_html_sections():
    """Test HTML processing with a specific fixture file number."""
    input_html = """
        <body>
            <h2 id="History">History</h2>
            <p id="mwUA">content</p>
            <p id="mwUB">content</p>
            <h3 id="History-16">16th century</h3>
            <p id="mwUC">content</p>
            <p id="mwUD">content</p>
        </body>
    """
    expected_text = """
    <body id="0">
        <section rel="cx:Section" id="cxSourceSection0" data-mw-section-number="1">
        <h2 id="0e769600933790607b2a13b33ddfad">
            <span class="cx-segment" data-segmentid="1">History</span>
        </h2>
        </section>
        <section rel="cx:Section" id="cxSourceSection1" data-mw-section-number="1"><p id="mwUA"><span class="cx-segment" data-segmentid="2">content</span></p>
        </section>
        <section rel="cx:Section" id="cxSourceSection2" data-mw-section-number="1"><p id="mwUB"><span class="cx-segment" data-segmentid="3">content</span></p>
        </section>
        <section rel="cx:Section" id="cxSourceSection3" data-mw-section-number="1"><h3 id="0311fc66ff8b0cf80103792799fe14"><span class="cx-segment" data-segmentid="4">16th century</span></h3>
        </section>
        <section rel="cx:Section" id="cxSourceSection4" data-mw-section-number="1"><p id="mwUC"><span class="cx-segment" data-segmentid="5">content</span></p>
        </section>
        <section rel="cx:Section" id="cxSourceSection5" data-mw-section-number="1"><p id="mwUD"><span class="cx-segment" data-segmentid="6">content</span></p>
        </section>
    </body>
    """
    # Process the input
    result = process_html(input_html)

    is_start = result.strip().startswith("<html")
    assert not is_start, "Result should not startswith <html tag"

    assert normalize_test(result) == normalize_test(expected_text), "Result should match expected output"
