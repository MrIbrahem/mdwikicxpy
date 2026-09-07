""" """

from __future__ import annotations

import html
import logging
from html.parser import HTMLParser

from .elements import VOID_ELEMENTS

logger = logging.getLogger(__name__)


class SaxHTMLParser(HTMLParser):
    """HTML SAX Parser that dispatches events directly to a Parser instance."""

    def __init__(self, target_parser, html_src: str) -> None:
        super().__init__(convert_charrefs=False)
        self.target = target_parser
        html_lower = html_src.lower()
        self.has_explicit_html = "<html" in html_lower
        self.has_explicit_body = "<body" in html_lower

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower() if self.target.lowercase else tag
        if tag_name == "html" and not self.has_explicit_html:
            return
        if tag_name == "body" and not self.has_explicit_body:
            return

        attr_dict = {k: (v if v is not None else "") for k, v in attrs}
        tag_dict = {
            "name": tag_name,
            "attributes": attr_dict,
            "isSelfClosing": tag_name in VOID_ELEMENTS,
        }
        self.target.on_open_tag(tag_dict)
        if tag_dict["isSelfClosing"]:
            self.target.on_close_tag(tag_name)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower() if self.target.lowercase else tag
        if tag_name == "html" and not self.has_explicit_html:
            return
        if tag_name == "body" and not self.has_explicit_body:
            return

        attr_dict = {k: (v if v is not None else "") for k, v in attrs}
        tag_dict = {
            "name": tag_name,
            "attributes": attr_dict,
            "isSelfClosing": True,
        }
        self.target.on_open_tag(tag_dict)
        self.target.on_close_tag(tag_name)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower() if self.target.lowercase else tag
        if tag_name == "html" and not self.has_explicit_html:
            return
        if tag_name == "body" and not self.has_explicit_body:
            return

        if tag_name not in VOID_ELEMENTS:
            self.target.on_close_tag(tag_name)

    def handle_data(self, data: str) -> None:
        self.target.on_text(data)

    def handle_entityref(self, name: str) -> None:
        """
        entity_map = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}
        if name in entity_map:
            self.target.on_text(entity_map[name])
        else:
            self.target.on_text(f"&{name};")
        """
        unescaped = html.unescape(f"&{name};")
        self.target.on_text(unescaped)

    def handle_charref(self, name: str) -> None:
        try:
            if name.startswith(("x", "X")):
                char = chr(int(name[1:], 16))
            else:
                char = chr(int(name))
            self.target.on_text(char)
        except Exception:
            self.target.on_text(f"&#{name};")


__all__ = [
    "SaxHTMLParser",
]
