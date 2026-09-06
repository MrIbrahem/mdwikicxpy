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
from .normalizer import Normalizer, normalize
from .parser import Parser
from .text_block import TextBlock
from .text_chunk import TextChunk
from .util import get_prop
from .utils import Utils

__all__ = [
    "normalize",
    "TextChunk",
    "TextBlock",
    "Doc",
    "Normalizer",
    "Contextualizer",
    "MwContextualizer",
    "Builder",
    "Parser",
    "get_prop",
    "Utils",
]
