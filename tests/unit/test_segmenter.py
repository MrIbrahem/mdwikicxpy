"""
Unit tests for segmentation/cx_segmenter.py module.
"""

import os
import sys

import pytest
from python.lib.lineardoc import Doc, TextBlock, TextChunk
from python.lib.segmentation.cx_segmenter import CXSegmenter


class TestCXSegmenter:
    """Test CXSegmenter class."""

    def test_segmenter_creation(self):
        """Test creating a segmenter."""
        segmenter = CXSegmenter()
        assert segmenter is not None

    def test_get_segmenter_function(self):
        """Test getting segmenter function."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        assert callable(seg_func)

    def test_segment_simple_sentence(self):
        """Test segmenting simple sentence."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        boundaries = seg_func("Hello world.")
        assert len(boundaries) >= 1
        assert 0 in boundaries

    def test_segment_multiple_sentences(self):
        """Test segmenting multiple sentences."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        text = "First sentence. Second sentence. Third sentence."
        boundaries = seg_func(text)
        # Should have boundaries for each sentence
        assert len(boundaries) >= 2

    def test_segment_empty_text(self):
        """Test segmenting empty text."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        boundaries = seg_func("")
        assert boundaries == []

    def test_segment_whitespace_only(self):
        """Test segmenting whitespace-only text."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        boundaries = seg_func("   \n\n  ")
        # Should handle whitespace gracefully
        assert isinstance(boundaries, list)

    def test_segment_no_punctuation(self):
        """Test segmenting text without punctuation."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        boundaries = seg_func("Hello world")
        # Should still return at least the start
        assert isinstance(boundaries, list)

    def test_segment_question_mark(self):
        """Test segmenting with question marks."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        text = "How are you? I am fine."
        boundaries = seg_func(text)
        assert len(boundaries) >= 2

    def test_segment_exclamation(self):
        """Test segmenting with exclamation marks."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        text = "Hello! How are you?"
        boundaries = seg_func(text)
        assert len(boundaries) >= 2

    def test_segment_abbreviations(self):
        """Test segmenting with abbreviations."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("en")
        text = "Dr. Smith is here. He is a doctor."
        boundaries = seg_func(text)
        # pysbd should handle abbreviations correctly
        assert isinstance(boundaries, list)

    def test_segment_different_language(self):
        """Test segmenting different languages."""
        segmenter = CXSegmenter()
        # Try Spanish
        seg_func_es = segmenter.get_segmenter("es")
        text = "Hola mundo. ¿Cómo estás?"
        boundaries = seg_func_es(text)
        assert len(boundaries) >= 1

    def test_segment_doc(self):
        """Test segmenting a Doc object."""
        segmenter = CXSegmenter()
        doc = Doc()
        # Add a simple text block
        chunks = [TextChunk("Hello. World.", [])]
        text_block = text_block(chunks, can_segment=True)
        doc.add_item("textblock", text_block)

        segmented = segmenter.segment(doc, "en")
        assert segmented is not None
        assert isinstance(segmented, Doc)

    def test_segment_preserves_non_segmentable(self):
        """Test that non-segmentable blocks are preserved."""
        segmenter = CXSegmenter()
        doc = Doc()
        # Add a non-segmentable text block
        chunks = [TextChunk("Do not segment.", [])]
        text_block = text_block(chunks, can_segment=False)
        doc.add_item("textblock", text_block)

        segmented = segmenter.segment(doc, "en")
        assert segmented is not None
        # Should preserve the block as-is
        assert len(segmented.items) > 0

    def test_segment_unicode_text(self):
        """Test segmenting Unicode text."""
        segmenter = CXSegmenter()
        seg_func = segmenter.get_segmenter("ar")
        text = "مرحبا. كيف حالك؟"
        boundaries = seg_func(text)
        # Should handle Arabic text
        assert isinstance(boundaries, list)
