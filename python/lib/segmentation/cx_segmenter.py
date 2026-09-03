"""
CXSegmenter - Sentence segmentation for Content Translation.
"""

from __future__ import annotations

import pysbd
from pysbd.languages import LANGUAGE_CODES


class CXSegmenter:
    """Segmenter for CX documents."""

    def segment(self, parsed_doc, language: str):
        """
        Segment the given parsed linear document object.

        Args:
            parsed_doc: Parsed Doc object
            language: Language code

        Returns:
            Segmented Doc object
        """
        return parsed_doc.segment(self.get_segmenter(language))

    def get_segmenter(self, language: str):
        """
        Get the segmenter for the given language.

        Args:
            language: Language code

        Returns:
            Function that returns sentence boundary offsets
        """

        def segmenter(text):
            """Segment text into sentences."""

            seg = pysbd.Segmenter(language=language, clean=False)
            sentences = seg.segment(text)
            boundaries = []

            # Track position to avoid finding duplicate sentences
            current_pos = 0
            for sentence in sentences:
                if sentence.strip():
                    # Find from current position onward
                    idx = text.find(sentence, current_pos)
                    if idx != -1:
                        boundaries.append(idx)
                        current_pos = idx + len(sentence)

            return boundaries

        return segmenter

    def is_language_supported(self, language: str) -> bool:
        return language in LANGUAGE_CODES


__all__ = [
    "CXSegmenter",
]
