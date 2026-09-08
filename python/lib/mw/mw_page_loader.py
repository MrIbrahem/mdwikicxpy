"""
Main processing module for HTML transformation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..lineardoc import Doc, MwContextualizer, Parser
from ..segmentation import CXSegmenter

# Load configuration
config_path = Path(__file__).parent.parent.parent / "config" / "MWPageLoader.yaml"

with open(config_path, "r", encoding="utf-8") as f:
    pageloader_config = yaml.safe_load(f)

removable_sections = pageloader_config.get("removableSections", {})
if not removable_sections:
    raise ValueError("removableSections must be defined in config")


class MWPageLoader:

    def get_parsed_doc(self, source_html: str, options: dict[str, Any]) -> Doc:
        parser = Parser(
            contextualizer=MwContextualizer(
                config={"removableSections": removable_sections},
            ),
            options=options,
        )

        parser.init()
        parser.write(source_html)
        return parser.builder.doc

    def get_page(
        self,
        source_html: str,
        lang: str | None = None,
        sort_attrs: bool = True,
        wrap_sections: bool = True,
    ) -> Doc:
        """
        Process source HTML through the CX pipeline.

        This function:
        1. Parses HTML via SAX parser into a linear document structure
        2. Applies MediaWiki contextualization (removes unwanted sections based on YAML config)
        3. Wraps sections with metadata
        4. Segments text for translation (sentence boundaries)
        5. Adds tracking IDs (segments, links)

        Args:
            source_html: Source HTML string

        Returns:
            Processed document
        """
        if lang is None:
            lang = "en"

        options = {
            "wrapSections": wrap_sections,
            "isolateSegments": False,
            "sort_attrs": sort_attrs,
        }
        parsed_doc = self.get_parsed_doc(source_html, options=options)

        if wrap_sections:
            parsed_doc = parsed_doc.wrap_sections()

        # Extract category tags from source document.
        segmented_doc = CXSegmenter().segment(parsed_doc, lang)

        return segmented_doc


__all__ = [
    "MWPageLoader",
]
