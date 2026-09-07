"""
Main processing module for HTML transformation.
"""

from __future__ import annotations

from .mw.mw_page_loader import MWPageLoader


def process_html(
    source_html: str,
    lang: str | None = None,
    sort_attrs: bool = True,
    wrap_sections: bool = True,
) -> str:
    """
    Process source HTML through the CX pipeline.

    This function:
    1. Parses HTML via SAX parser into a linear document structure
    2. Applies MediaWiki contextualization (removes unwanted sections based on YAML config)
    3. Wraps sections with metadata
    4. Segments text for translation (sentence boundaries)
    5. Adds tracking IDs (segments, links)

    Args:
        source_html: Source HTML string

    Returns:
        Processed HTML string
    """
    doc = MWPageLoader().get_page(
        source_html=source_html,
        lang=lang,
        sort_attrs=sort_attrs,
        wrap_sections=wrap_sections,
    )
    return doc.get_html()


__all__ = [
    "process_html",
]
