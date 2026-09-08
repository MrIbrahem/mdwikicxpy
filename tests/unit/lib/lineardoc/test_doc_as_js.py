import json
from pathlib import Path

import pytest

from python.lib.lineardoc import (
    MwContextualizer,
    Parser,
    TextBlock,
)
from tests.unit.html_normalizer import normalize_test

FIXTURES_DIR = Path(__file__).resolve().parent / "data"

trans_tests_path = FIXTURES_DIR / "translate.test.json"

with open(trans_tests_path, "r", encoding="utf-8") as f:
    trans_tests = json.load(f)


def deep_equal(result, expected, desc):
    assert result == expected, desc

class TestLinearDoc:
    @pytest.mark.skip(reason="No such file or directory: 'I:\\test1.xhtml'")
    def test_should_be_possible_to_linearise_all_kind_of_html_inputs(self):
        num_tests = 8
        for i in range(1, num_tests + 1):
            test_xhtml_file = FIXTURES_DIR / f"/test{i}.xhtml"
            result_xml_file = FIXTURES_DIR / f"/test{i}-result.xml"
            result_xhtml_file = FIXTURES_DIR / f"/test{i}-result.xhtml"

            with open(test_xhtml_file, "r", encoding="utf-8") as f:
                test_xhtml = f.read()

            with open(result_xml_file, "r", encoding="utf-8") as f:
                expected_xml = f.read()

            with open(result_xhtml_file, "r", encoding="utf-8") as f:
                expected_xhtml = f.read()

            parser = Parser(MwContextualizer())
            parser.init()
            parser.write(test_xhtml)

            assert not parser.builder.doc.is_ignorable_block(), "Not a section with block template"

            deep_equal(normalize_test(parser.builder.doc.dump_xml()), normalize_test(expected_xml), "Linearised structure")
            deep_equal(normalize_test(parser.builder.doc.get_html()), normalize_test(expected_xhtml), "Reconstructed XHTML")

    def test_should_be_possible_to_reconstruct_the_html_from_lineardoc(self):
        for test in trans_tests:
            parser = Parser(MwContextualizer())
            parser.init()
            parser.write("<div>" + test["source"] + "</div>")

            text_block1 = parser.builder.doc.items[1].item
            assert isinstance(text_block1, TextBlock)

            deep_equal(text_block1.get_html(), test["source"], "Reconstructed source HTML")

            # text_block2 = text_block1.translate_tags(test["targetText"], test["rangeMappings"])
            # deep_equal(text_block2.get_html(), test["expect"], "Translated HTML")

    def test_if_the_content_is_block_level_template(self):
        test_files = [
            "test-block-template-section-1.html",
            "test-block-template-section-2.html",
            "test-block-template-section-3.html",
            "test-block-template-section-4.html",
        ]

        for file_path_rel in test_files:
            filepath = FIXTURES_DIR / file_path_rel
            with open(filepath, "r", encoding="utf-8") as f:
                content_for_test = f.read()

            parser = Parser(MwContextualizer())
            parser.init()
            parser.write(content_for_test)

            assert parser.builder.doc.is_ignorable_block(), f"File {file_path_rel} is section with block template"

    def test_get_root_item_for_ignoring_blockspaces(self):
        source_doc = """<section data-mw-section-id="25" id="mwArE">
        <p id="mwArI">Sestak voted for the <a rel="mw:WikiLink" href="./Improving_Head_Start_Act"
                title="Improving Head Start Act" id="mwArM" class="new">Improving Head Start Act</a> and the <a
                rel="mw:WikiLink" href="./College_Cost_Reduction_and_Access_Act"
                title="College Cost Reduction and Access Act" id="mwArQ"
                class="new">College Cost Reduction and Access Act</a>.
            </p>
        </section>"""

        parser = Parser(MwContextualizer(), {"isolateSegments": True})
        parser.init()
        parser.write(source_doc)

        root_item = parser.builder.doc.get_root_item()
        assert root_item is not None

        deep_equal(
            root_item["name"], "p", "get_root_item should ignore the blockspaces in the beginning of the document"
        )

    def test_get_root_item_for_not_ignoring_non_whitespace_content_in_textblock(self):
        source_doc = """<p id="mwFg">The tensor product of <span about="#mwt10" class="texhtml "
        data-mw="{}" id="mwFw" typeof="mw:Transclusion"><i>V</i></span> and.
        </p>"""

        parser = Parser(MwContextualizer(), {"isolateSegments": True})
        parser.init()
        parser.write(source_doc)

        parsed_doc = parser.builder.doc

        textblock = next(item for item in parsed_doc.items if getattr(item, "item_type", None) == "textblock")

        assert isinstance(textblock.item, TextBlock)
        root_item = textblock.item.get_root_item()

        deep_equal(
            root_item, None, "get_root_item of textblock should consider non-whitespace content inside its textchunks"
        )

    def test_get_root_item_for_ignoring_whitespace_content_in_textblock(self):
        source_doc = """<p id="mwFg">
         <span about="#mwt10" class="texhtml "
        data-mw="{}" id="mwFw" typeof="mw:Transclusion"><i>V</i></span> and.
        </p>"""

        parser = Parser(MwContextualizer(), {"isolateSegments": True})
        parser.init()
        parser.write(source_doc)

        parsed_doc = parser.builder.doc
        textblock = next(item for item in parsed_doc.items if getattr(item, "item_type", None) == "textblock")

        assert isinstance(textblock.item, TextBlock)
        root_item = textblock.item.get_root_item()

        assert root_item is not None

        deep_equal(
            root_item["name"],
            "span",
            "get_root_item of textblock should ignore whitespace content inside its textchunks",
        )
