"""
Main processing module for HTML transformation.
"""

import os
import re

import yaml

from .lineardoc import Normalizer, Parser, MwContextualizer
from .segmentation import CXSegmenter

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "..", "config", "MWPageLoader.yaml")
with open(config_path, "r") as f:
    pageloader_config = yaml.safe_load(f)

removable_sections = pageloader_config.get("removableSections", {})


def normalize(html):
    """
    Normalize HTML by parsing and re-serializing.

    Args:
        html: HTML string to normalize

    Returns:
        Normalized HTML string
    """
    normalizer = Normalizer()
    normalizer.init()
    # Remove tabs, carriage returns, and newlines
    html = re.sub(r"[\t\r\n]+", "", html)
    normalizer.write(html)
    return normalizer.get_html()


def process_html(source_html):
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
        Processed HTML string
    """
    parser = Parser(MwContextualizer({"removableSections": removable_sections}), {"wrapSections": True})

    parser.init()
    parser.write(source_html)
    parsed_doc = parser.builder.doc
    parsed_doc = parsed_doc.wrap_sections()

    segmented_doc = CXSegmenter().segment(parsed_doc, "en")

    result = segmented_doc.get_html()

    return result
