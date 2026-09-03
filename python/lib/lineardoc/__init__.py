"""
Lineardoc module - Linear document representation for HTML.
"""

from .builder import Builder
from .contextualizer import Contextualizer
from .doc import Doc
from .mw_contextualizer import MwContextualizer
from .normalizer import Normalizer
from .parser import Parser
from .text_block import TextBlock
from .text_chunk import TextChunk
from .util import get_prop
from .utils import *

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
]
