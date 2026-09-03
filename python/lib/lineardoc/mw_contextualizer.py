"""
Contextualizer for MediaWiki DOM HTML.

See https://www.mediawiki.org/wiki/Specs/HTML
"""

import json
import re

from . import util as cxutil
from .contextualizer import Contextualizer

CONTENT_BRANCH_NODE_NAMES = [
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "pre",
    "div",
    "table",
    "ol",
    "ul",
    "dl",
    "figure",
    "center",
    "section",
]


class MwContextualizer(Contextualizer):
    """Contextualizer for MediaWiki DOM HTML."""

    def __init__(self, config=None):
        """
        Initialize the MW contextualizer.

        Args:
            config: Config dict with removableSections containing array of classes and rdfa values
        """
        super().__init__(config)
        # Array holding transclusion fragment ids (about attribute values)
        self.removable_transclusion_fragments = []

    def get_child_context(self, tag):
        """Get the context for a new tag being opened."""
        context = self.get_context()
        tag_type = tag.get("attributes", {}).get("typeof", "") or tag.get("attributes", {}).get("rel", "")

        if context == "removable" or self.is_removable(tag):
            return "removable"

        # Any descendent of Transclusion/Placeholder is verbatim
        if context == "verbatim" or re.search(r"(^|\s)(mw:Transclusion|mw:Placeholder)\b", tag_type):
            return "verbatim"

        # Otherwise, figure is media
        if tag["name"] == "figure":
            return "media"

        if tag["name"] == "span" and re.search(r"(^|\s)(mw:File|mw:Image|mw:Video|mw:Audio)\b", tag_type):
            return "media-inline"

        # Immediate children of body are sections
        if context is None and tag["name"] == "body":
            return "section"

        # And figure//figcaption is contentBranch
        if (context in ("media", "media-inline")) and tag["name"] == "figcaption":
            return "contentBranch"

        # And ContentBranchNodes are contentBranch
        if (context in ("section", None)) and tag["name"] in CONTENT_BRANCH_NODE_NAMES:
            return "contentBranch"

        # Else same as parent context
        return context

    def can_segment(self):
        """Determine whether sentences can be segmented."""
        return self.get_context() == "contentBranch"

    def is_removable(self, tag):
        """
        Check if the tag need to be ignored while parsing and hence removed.

        Args:
            tag: Tag dict

        Returns:
            Whether the tag is removable
        """
        removable_sections = self.config.get("removableSections")
        if not removable_sections:
            return False

        about = tag.get("attributes", {}).get("about")
        if about in self.removable_transclusion_fragments:
            # Once a transclusion is removed, make sure their fragments also removed
            return True

        # Check classes
        class_list = tag.get("attributes", {}).get("class", "").split()
        for removable_class in removable_sections.get("classes", []):
            if removable_class in class_list:
                if about:
                    self.removable_transclusion_fragments.append(about)
                return True

        # Check RDFa
        types = tag.get("attributes", {}).get("typeof", "").split()
        rels = tag.get("attributes", {}).get("rel", "").split()
        rdfa = types + rels
        for removable_rdfa in removable_sections.get("rdfa", []):
            # Make sure that the rdfa value matches
            if removable_rdfa in rdfa and len(rdfa) == 1:
                if about:
                    self.removable_transclusion_fragments.append(about)
                return True

        # Check templates
        data_mw = tag.get("attributes", {}).get("data-mw")
        if not data_mw:
            return False

        try:
            mw_data = json.loads(data_mw)
        except (json.JSONDecodeError, ValueError):
            return False

        template_name = cxutil.get_prop(["parts", 0, "template", "target", "wt"], mw_data)
        if not template_name:
            return False

        for removable_template in removable_sections.get("templates", []):
            if removable_template.startswith("/") and removable_template.endswith("/"):
                # A regular expression is given
                removable_template_regexp = re.compile(removable_template[1:-1], re.IGNORECASE)
                match = removable_template_regexp.search(template_name)
            else:
                match = template_name.lower() == removable_template.lower()

            if match:
                if about:
                    self.removable_transclusion_fragments.append(about)
                return True

        return False
