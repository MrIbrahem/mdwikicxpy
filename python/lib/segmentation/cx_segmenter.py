"""
CXSegmenter - Sentence segmentation for Content Translation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import sentencex

from ..lineardoc.doc import Doc


class CXSegmenter:
    """Segmenter for CX documents."""

    def segment(self, parsed_doc: Doc, language: str) -> Doc:
        """
        Segment the given parsed linear document object.

        Args:
            parsed_doc: Parsed Doc object
            language: Language code

        Returns:
            Segmented Doc object
        """
        return parsed_doc.segment(self.get_segmenter(language))

    def get_segmenter(self, language: str) -> Callable[..., list[Any]]:
        """
        Get the segmenter for the given language.

        Args:
            language: Language code

        Returns:
            Function that returns sentence boundary offsets
        """

        def segmenter(text: str) -> list[int]:
            """Segment text into sentences."""
            sentences = sentencex.segment(language, text)
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

        def get_sentence_boundaries(text: str) -> list[int]:
            """Segment text into sentences."""
            sentences = sentencex.get_sentence_boundaries(language, text)
            boundaries = []

            for sentence in sentences:
                if sentence["text"].strip():
                    boundaries.append(sentence["start_index"])

            return boundaries

        return get_sentence_boundaries

    def get_segmenter_obj(self, language: str) -> Callable[..., list[Any]]:
        """
        Get the segmenter for the given language.

        Args:
            language: Language code

        Returns:
            Function that returns sentence boundary offsets
        """

        def get_sentence_boundaries(text: str) -> list[sentencex.Boundary]:
            """Segment text into sentences."""
            sentences = sentencex.get_sentence_boundaries(language, text)
            boundaries = []

            for sentence in sentences:
                if sentence["text"].strip():
                    boundaries.append(sentence)

            return boundaries

        return get_sentence_boundaries

    def is_language_supported(self, language: str) -> bool:
        return True


__all__ = [
    "CXSegmenter",
]
