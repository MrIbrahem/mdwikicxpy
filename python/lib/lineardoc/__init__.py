"""
Lineardoc module - Linear document representation for HTML.

converted from the LinearDoc javascript library of the Wikimedia Content translation project

https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lib/lineardoc/index.js
"""

from __future__ import annotations

from .builder import Builder
from .contextualizer import Contextualizer
from .doc import Doc
from .mw_contextualizer import MwContextualizer
from .normalizer import Normalizer
from .parser import Parser
from .text_block import TextBlock
from .text_chunk import TextChunk
from .util import get_prop
from .utils import (
    add_common_tag,
    clone_open_tag,
    dump_tags,
    esc,
    esc_attr,
    find_all,
    get_chunk_boundary_groups,
    get_close_tag_html,
    get_open_tag_html,
    is_external_link,
    is_gallery,
    is_ignorable_block,
    is_inline_empty_tag,
    is_math,
    is_non_translatable,
    is_reference,
    is_reference_list,
    is_segment,
    is_transclusion,
    is_transclusion_fragment,
    set_link_ids_in_place,
)

__all__ = [
    "TextChunk",
    "TextBlock",
    "Doc",
    "Normalizer",
    "Contextualizer",
    "MwContextualizer",
    "Builder",
    "Parser",
    "get_prop",
    "find_all",
    "esc",
    "esc_attr",
    "get_open_tag_html",
    "get_close_tag_html",
    "clone_open_tag",
    "dump_tags",
    "is_reference",
    "is_math",
    "is_gallery",
    "is_reference_list",
    "is_external_link",
    "is_segment",
    "is_transclusion",
    "is_transclusion_fragment",
    "is_non_translatable",
    "is_inline_empty_tag",
    "get_chunk_boundary_groups",
    "add_common_tag",
    "set_link_ids_in_place",
    "is_ignorable_block",
]
