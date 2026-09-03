"""
Unit tests for lineardoc/contextualizer.py and lineardoc/mw_contextualizer.py modules.
"""


from python.lib.lineardoc.contextualizer import Contextualizer
from python.lib.lineardoc.mw_contextualizer import MwContextualizer


class TestContextualizer:
    """Test Contextualizer class."""

    def test_contextualizer_creation(self):
        """Test creating a contextualizer."""
        ctx = Contextualizer()
        assert ctx.contexts == []
        assert ctx.config == {}

    def test_contextualizer_with_config(self):
        """Test creating contextualizer with config."""
        config = {"key": "value"}
        ctx = Contextualizer(config)
        assert ctx.config == config

    def test_get_context_empty(self):
        """Test getting context when empty."""
        ctx = Contextualizer()
        assert ctx.get_context() is None

    def test_on_open_tag_simple(self):
        """Test opening a tag."""
        ctx = Contextualizer()
        tag = {"name": "div", "attributes": {}}
        ctx.on_open_tag(tag)
        assert len(ctx.contexts) == 1

    def test_on_close_tag_simple(self):
        """Test closing a tag."""
        ctx = Contextualizer()
        tag = {"name": "div", "attributes": {}}
        ctx.on_open_tag(tag)
        ctx.on_close_tag()
        assert len(ctx.contexts) == 0

    def test_can_segment_default(self):
        """Test can_segment when context is None."""
        ctx = Contextualizer()
        assert ctx.can_segment() is True

    def test_get_child_context_figure(self):
        """Test child context for figure tag."""
        ctx = Contextualizer()
        tag = {"name": "figure", "attributes": {}}
        child_ctx = ctx.get_child_context(tag)
        assert child_ctx == "media"

    def test_get_child_context_figcaption(self):
        """Test child context for figcaption tag."""
        ctx = Contextualizer()
        # Set a context first
        ctx.contexts.append("media")
        tag = {"name": "figcaption", "attributes": {}}
        child_ctx = ctx.get_child_context(tag)
        assert child_ctx is None

    def test_context_stack(self):
        """Test context stack behavior."""
        ctx = Contextualizer()
        ctx.on_open_tag({"name": "div", "attributes": {}})
        ctx.on_open_tag({"name": "p", "attributes": {}})
        assert len(ctx.contexts) == 2
        ctx.on_close_tag()
        assert len(ctx.contexts) == 1
        ctx.on_close_tag()
        assert len(ctx.contexts) == 0


class Testmw_contextualizer:
    """Test mw_contextualizer class."""

    def test_mw_contextualizer_creation(self):
        """Test creating MW contextualizer."""
        ctx = MwContextualizer()
        assert ctx.removable_transclusion_fragments == []

    def test_can_segment_content_branch(self):
        """Test can_segment in contentBranch context."""
        ctx = MwContextualizer()
        ctx.contexts.append("contentBranch")
        assert ctx.can_segment() is True

    def test_can_segment_other_context(self):
        """Test can_segment in other contexts."""
        ctx = MwContextualizer()
        ctx.contexts.append("media")
        assert ctx.can_segment() is False

    def test_get_child_context_removable(self):
        """Test removable context propagates."""
        ctx = MwContextualizer()
        ctx.contexts.append("removable")
        tag = {"name": "div", "attributes": {}}
        assert ctx.get_child_context(tag) == "removable"

    def test_get_child_context_transclusion(self):
        """Test transclusion creates verbatim context."""
        ctx = MwContextualizer()
        tag = {"name": "div", "attributes": {"typeof": "mw:Transclusion"}}
        assert ctx.get_child_context(tag) == "verbatim"

    def test_get_child_context_placeholder(self):
        """Test placeholder creates verbatim context."""
        ctx = MwContextualizer()
        tag = {"name": "div", "attributes": {"typeof": "mw:Placeholder"}}
        assert ctx.get_child_context(tag) == "verbatim"

    def test_get_child_context_figure(self):
        """Test figure creates media context."""
        ctx = MwContextualizer()
        tag = {"name": "figure", "attributes": {}}
        assert ctx.get_child_context(tag) == "media"

    def test_get_child_context_media_inline(self):
        """Test media-inline context."""
        ctx = MwContextualizer()
        tag = {"name": "span", "attributes": {"typeof": "mw:Image"}}
        assert ctx.get_child_context(tag) == "media-inline"

    def test_get_child_context_body_to_section(self):
        """Test body creates section context."""
        ctx = MwContextualizer()
        tag = {"name": "body", "attributes": {}}
        assert ctx.get_child_context(tag) == "section"

    def test_get_child_context_figcaption_in_media(self):
        """Test figcaption in media context."""
        ctx = MwContextualizer()
        ctx.contexts.append("media")
        tag = {"name": "figcaption", "attributes": {}}
        assert ctx.get_child_context(tag) == "contentBranch"

    def test_get_child_context_content_branch_nodes(self):
        """Test content branch nodes."""
        ctx = MwContextualizer()
        ctx.contexts.append("section")
        for tag_name in ["p", "h1", "h2", "div", "blockquote"]:
            tag = {"name": tag_name, "attributes": {}}
            assert ctx.get_child_context(tag) == "contentBranch", f"{tag_name} should create contentBranch"

    def test_is_removable_by_class(self):
        """Test removing elements by class."""
        config = {"removableSections": {"classes": ["navbox", "noprint"]}}
        ctx = MwContextualizer(config)
        tag = {"name": "div", "attributes": {"class": "navbox sidebar"}}
        assert ctx.is_removable(tag) is True

    def test_is_removable_by_rdfa(self):
        """Test removing elements by RDFa."""
        config = {"removableSections": {"rdfa": ["mw:PageProp/toc"]}}
        ctx = MwContextualizer(config)
        tag = {"name": "div", "attributes": {"typeof": "mw:PageProp/toc"}}
        assert ctx.is_removable(tag) is True

    def test_is_removable_not_removable(self):
        """Test non-removable elements."""
        config = {"removableSections": {"classes": ["navbox"]}}
        ctx = MwContextualizer(config)
        tag = {"name": "div", "attributes": {"class": "content"}}
        assert ctx.is_removable(tag) is False

    def test_is_removable_transclusion_fragments(self):
        """Test that transclusion fragments are tracked."""
        config = {"removableSections": {"classes": ["navbox"]}}
        ctx = MwContextualizer(config)
        tag = {"name": "div", "attributes": {"class": "navbox", "about": "#mwt1"}}
        assert ctx.is_removable(tag) is True
        assert "#mwt1" in ctx.removable_transclusion_fragments

    def test_is_removable_fragment_continuation(self):
        """Test that fragments of removed transclusions are also removed."""
        config = {"removableSections": {"classes": ["navbox"]}}
        ctx = MwContextualizer(config)
        # First tag is removable
        tag1 = {"name": "div", "attributes": {"class": "navbox", "about": "#mwt1"}}
        ctx.is_removable(tag1)

        # Second tag with same about should also be removable
        tag2 = {"name": "span", "attributes": {"about": "#mwt1"}}
        assert ctx.is_removable(tag2) is True

    def test_is_removable_by_template(self):
        """Test removing elements by template name."""
        config = {"removableSections": {"templates": ["Infobox"]}}
        ctx = MwContextualizer(config)
        tag = {
            "name": "div",
            "attributes": {
                "typeof": "mw:Transclusion",
                "data-mw": '{"parts":[{"template":{"target":{"wt":"Infobox"}}}]}',
            },
        }
        assert ctx.is_removable(tag) is True

    def test_is_removable_by_template_regex(self):
        """Test removing elements by template regex."""
        config = {"removableSections": {"templates": ["/^Template:Info/"]}}
        ctx = MwContextualizer(config)
        tag = {
            "name": "div",
            "attributes": {
                "typeof": "mw:Transclusion",
                "data-mw": '{"parts":[{"template":{"target":{"wt":"Template:Infobox"}}}]}',
            },
        }
        assert ctx.is_removable(tag) is True

    def test_is_removable_invalid_data_mw(self):
        """Test handling invalid data-mw JSON."""
        config = {"removableSections": {"templates": ["Test"]}}
        ctx = MwContextualizer(config)
        tag = {"name": "div", "attributes": {"typeof": "mw:Transclusion", "data-mw": "invalid json"}}
        assert ctx.is_removable(tag) is False
