"""
"""

from python.lib.mw.mw_page_loader import MWPageLoader
from tests.unit.html_normalizer import normalize_test

def test_cx_segmenter_2():
    source_text = """
    <p>
        Tewodros <a rel="mw:WikiLink" href="/wiki/January_6" title="January 6">January 6</a> date <a href="/w/index.php?title=1811" class="new" title="1811 (page not yet written)">1811</a><a rel="mw:WikiLink" href="/w/index.php?title=Haylu_Wolde_Georgis" class="new" title="Haylu Wolde Giorgis">Haylu Wolde Giorgis</a> was the ruler of Qara. After receiving a priestly education as a child, Emperor Tewodros became the minister of his uncle and later, for a short time, of <a rel="mw:WikiLink" href="/w/index.php?title=1839" class="new cx-link" title="1839">1839</a> AD. in Weizero
    </p>
    """
    # <a rel="mw:WikiLink" href="/w/index.php?title=1839" class="new" title="1839">1839</a>

    sort_attrs = True
    doc = MWPageLoader().get_page(
        source_html=source_text,
        lang="en",
        sort_attrs=sort_attrs,
        wrap_sections=False,
    )
    result = doc.get_html()

    # assert 2 == 0
    has_bad_link = result.count('"/w/index.php"')

    # `split href before ?` in def set_link_ids_in_place()

    assert has_bad_link == 0, 'Result contain ("/w/index.php")'

    normalized_result = normalize_test(result, sort_attrs=sort_attrs)

    expected_text = """
        <p id="0">
            <span class="cx-segment" data-segmentid="1"> Tewodros <a class="cx-link" data-linkid="2" href="/wiki/January_6"
                    rel="mw:WikiLink" title="January 6">January 6</a> date <a class="new" href="/w/index.php?title=1811"
                    title="1811 (page not yet written)">1811</a>
                <a class="cx-link" data-linkid="3" href="/w/index.php?title=Haylu_Wolde_Georgis" rel="mw:WikiLink"
                    title="Haylu Wolde Giorgis">Haylu Wolde Giorgis</a> was the ruler of Qara. </span>
            <span class="cx-segment" data-segmentid="4">After receiving a priestly education as a child, Emperor Tewodros became
                the minister of his uncle and later, for a short time, of <a class="cx-link" data-linkid="5"
                    href="/w/index.php?title=1839" rel="mw:WikiLink" title="1839">1839</a> AD. </span>
            <span class="cx-segment" data-segmentid="6">in Weizero </span>
        </p>
    """
    expected_result_data = normalize_test(expected_text, sort_attrs=sort_attrs)

    assert normalized_result == expected_result_data
