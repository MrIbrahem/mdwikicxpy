""" """

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

BLOCK_TAGS = [
    "html",
    "head",
    "body",
    "script",
    # head tags
    # In HTML5+RDFa, link/meta are actually allowed anywhere in the body, and are to be
    # treated as void flow content (like <br> and <img>).
    "title",
    "style",
    "meta",
    "link",
    "noscript",
    "base",
    # non-visual content
    "audio",
    "data",
    "datagrid",
    "datalist",
    "dialog",
    "eventsource",
    "form",
    "iframe",
    "main",
    "menu",
    "menuitem",
    "optgroup",
    "option",
    # paragraph
    "div",
    "p",
    # tables
    "table",
    "tbody",
    "thead",
    "tfoot",
    "caption",
    "th",
    "tr",
    "td",
    # lists
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    # HTML5 heading content
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hgroup",
    # HTML5 sectioning content
    "article",
    "aside",
    "body",
    "nav",
    "section",
    "footer",
    "header",
    "figure",
    "figcaption",
    "fieldset",
    "details",
    "blockquote",
    "address",  # added by Giovanni Toffoli
    # other
    "hr",
    "button",
    "canvas",
    "center",
    "col",
    "colgroup",
    "embed",
    "map",
    "object",
    "pre",
    "progress",
    "video",
    # non-annotation inline tags
    "img",
    "br",
    "wiki-chart",
]

# HTML void elements that cannot have content and should be self-closing
VOID_ELEMENTS = [
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
]

__all__ = [
    "VOID_ELEMENTS",
    "BLOCK_TAGS",
]
