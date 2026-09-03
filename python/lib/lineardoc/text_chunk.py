# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

"""
text_chunk - A chunk of uniformly-annotated inline text

The annotations consist of a list of inline tags (<a>, <i> etc), and an
optional "inline element" (br/img tag, or a sub-document e.g. for a
reference span). The tags and/or reference apply to the whole text;
therefore text with varying markup must be split into multiple chunks.
"""


class TextChunk:
    """A chunk of uniformly-annotated inline text."""

    def __init__(self, text, tags, inline_content=None):
        """
        Initialize a text_chunk.

        Args:
            text: Plaintext in the chunk (can be '')
            tags: Array of SAX open tag objects, for the applicable tags
            inline_content: Tag or sub-doc (optional)
        """
        self.text = text
        self.tags = tags
        self.inline_content = inline_content

    def __str__(self):
        return self.text

    def __repr__(self):
        return self.text
