"""
"""

import re
from python.lib.lineardoc import normalize
from python.lib.mw.mw_page_loader import MWPageLoader

def normalize_test(html: str, sort_attrs: bool = True) -> str:
    """Normalize HTML using normalizer module."""
    cleaned = re.sub(r"<span[^>]*class=\"Z3988\"[^>]*>.*?</span>", "", html, flags=re.DOTALL)
    cleaned = cleaned.strip()

    cleaned = re.sub(r">\s+<", "><", cleaned)
    cleaned = cleaned.replace("&nbsp;", "\u00a0")
    cleaned = cleaned.strip()
    cleaned = normalize(cleaned, sort_attrs=sort_attrs)
    return cleaned

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
    """
    expected_result_data = normalize_test(expected_text, sort_attrs=sort_attrs)

    assert normalized_result == expected_result_data
