""" """

from python.lib.lineardoc.elements import BLOCK_TAGS


class TestParserBlockTags:
    """Test block tag constants."""

    def test_block_tags_list(self):
        """Test that BLOCK_TAGS is defined."""

        assert isinstance(BLOCK_TAGS, list)
        assert "div" in BLOCK_TAGS
        assert "p" in BLOCK_TAGS
        assert "h1" in BLOCK_TAGS
        assert "table" in BLOCK_TAGS

    def test_inline_tags_not_in_block_tags(self):
        """Test that inline tags are not in BLOCK_TAGS."""

        assert "span" not in BLOCK_TAGS
        assert "a" not in BLOCK_TAGS
        assert "b" not in BLOCK_TAGS
        assert "i" not in BLOCK_TAGS
