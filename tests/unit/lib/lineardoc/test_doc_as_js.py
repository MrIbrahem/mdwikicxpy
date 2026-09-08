import json
import re
from pathlib import Path

from python.lib.lineardoc import (
    MwContextualizer,
    Normalizer,
    Parser,
    TextBlock,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "data"

trans_tests_path = FIXTURES_DIR / "translate.test.json"

with open(trans_tests_path, "r", encoding="utf-8") as f:
    trans_tests = json.load(f)


def deep_equal(result, expected, desc):
    assert result == expected, desc


def normalize(html: str) -> str:
    normalizer = Normalizer()
    normalizer.init()
    # Replace \r\n, \n, \t, or \r globally
    cleaned_html = re.sub(r"(\r\n|\n|\t|\r)", "", html)
    normalizer.write(cleaned_html)
    return normalizer.get_html()


class TestLinearDoc:

    def test_should_be_possible_to_linearise_all_kind_of_html_inputs(self):
        num_tests = 8
        for i in range(1, num_tests + 1):
            test_xhtml_file = FIXTURES_DIR / f"/test{i}.xhtml"
            result_xml_file = FIXTURES_DIR / f"/test{i}-result.xml"
            result_xhtml_file = FIXTURES_DIR / f"/test{i}-result.xhtml"

            with open(test_xhtml_file, "r", encoding="utf-8") as f:
                test_xhtml = re.sub(r"^\s+|\s+$", "", f.read())

            with open(result_xml_file, "r", encoding="utf-8") as f:
                expected_xml = re.sub(r"^\s+|\s+$", "", f.read())

            with open(result_xhtml_file, "r", encoding="utf-8") as f:
                expected_xhtml = re.sub(r"^\s+|\s+$", "", f.read())

            parser = Parser(MwContextualizer())
            parser.init()
            parser.write(test_xhtml)

            assert not parser.builder.doc.is_ignorable_block(), "Not a section with block template"

            deep_equal(normalize(parser.builder.doc.dump_xml()), normalize(expected_xml), "Linearised structure")
            deep_equal(normalize(parser.builder.doc.get_html()), normalize(expected_xhtml), "Reconstructed XHTML")

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

    def test_should_be_possible_to_reduce_and_expand_a_document(self):
        test_xhtml_file = FIXTURES_DIR / "test-figure-inline.html"
        with open(test_xhtml_file, "r", encoding="utf-8") as f:
            content_for_reduce = re.sub(r"^\s+|\s+$", "", f.read())

        parser = Parser(MwContextualizer())
        parser.init()
        parser.write(content_for_reduce)

        data = parser.builder.doc.reduce()
        reduced_doc, extracted_data = data["reduced_doc"], data["extracted_data"]

        deep_equal(len(extracted_data.keys()), 16, "Attributes for 16 tags extracted.")

        expanded_doc = reduced_doc.expand(extracted_data)
        deep_equal(
            normalize(expanded_doc.get_html()),
            normalize(content_for_reduce),
            "Restored the original html after reduce and expand.",
        )

    def test_html_compaction_roundtrip_with_inline_chunks(self):
        test_xhtml_file = FIXTURES_DIR / "test-chunks-inline.html"
        with open(test_xhtml_file, "r", encoding="utf-8") as f:
            content_for_reduce = re.sub(r"^\s+|\s+$", "", f.read())

        parser = Parser(MwContextualizer())
        parser.init()
        parser.write(content_for_reduce)

        data = parser.builder.doc.reduce()
        reduced_doc, extracted_data = data["reduced_doc"], data["extracted_data"]

        deep_equal(len(extracted_data.keys()), 22, "Attributes for 22 tags extracted.")

        expanded_doc = reduced_doc.expand(extracted_data)
        deep_equal(
            normalize(expanded_doc.get_html()),
            normalize(content_for_reduce),
            "Restored the original html after reduce and expand.",
        )

    def test_html_expand_with_external_attributes_inserted(self):
        corrupted_doc = """<p id="1">
            <b id="2" onclick="doSomething();">Externally inserted attribute.</b>
            <a href="navigateThere();">Externally inserted tag</a>
            <span id="mwEz">Element with only id attribute is fine.</span>
            </p>"""

        sanitized_expanded_doc = """<p class="paragraph" id="mwEq">
            <b class="bold" id="mwEs">Externally inserted attribute.</b>
            <a>Externally inserted tag</a>
            <span id="mwEz">Element with only id attribute is fine.</span>
            </p>"""

        extracted_data = {
            "1": {"attributes": {"id": "mwEq", "class": "paragraph"}},
            "2": {"attributes": {"id": "mwEs", "class": "bold"}},
        }

        parser = Parser(MwContextualizer())
        parser.init()
        parser.write(corrupted_doc)

        expanded_doc = parser.builder.doc.expand(extracted_data)
        deep_equal(
            normalize(expanded_doc.get_html()),
            normalize(sanitized_expanded_doc),
            "Expanded the corrupted document by removing all externally inserted attributes.",
        )

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
                content_for_test = re.sub(r"^\s+|\s+$", "", f.read())

            parser = Parser(MwContextualizer())
            parser.init()
            parser.write(content_for_test)

            assert parser.builder.doc.is_ignorable_block(), f"File {file_path_rel} is section with block template"

    def test_should_not_ignore_a_section_that_begins_with_an_inline_template_but_has_translatable_prose(self):
        filepath = FIXTURES_DIR / "test-inline-template-section.html"
        with open(filepath, "r", encoding="utf-8") as f:
            content_for_test = re.sub(r"^\s+|\s+$", "", f.read())

        parser = Parser(MwContextualizer())
        parser.init()
        parser.write(content_for_test)

        assert (
            not parser.builder.doc.is_ignorable_block()
        ), "Section starting with an inline transclusion followed by prose is translatable"

    def test_html_compaction_roundtrip_with_inline_style_content(self):
        source_doc = """<section><p>
        <a href="Our title">ABC</a>
        <style> a { background: url(https://en.wikipedia.org/css-background); } </style>
        <script>original script</script>
        <script type="module" src="main.js"></script>
        <span id="mwKJ" typeof="mw:Entity">&ndash;</span>
        </p>
        </section>"""

        expected_reduced_doc = """<section><p>
        <a id="1">ABC</a>
        <style id="2"></style>
        <script id="3"></script>
        <script id="4"></script>
        <span id="5">&ndash;</span>
        </p>
        </section>"""

        # MT result from external MT service. Assuming that it altered the style and script content.
        corrupted_mt_input = """<section><p>
        <a id="1" href="Their title">abc</a>
        <style id="2"> a { background: url(https://leaking.via/css-background); } </style>
        <script id="3">Corrupted script</script>
        <script id="4" src="https://bad.via/main.js"></script>
        <span id="5">©</span>
        </p>
        </section>"""

        # Expected final output after fixing all external modification
        sanitized_expanded_doc = """<section><p>
        <a href="Our title">abc</a>
        <style> a { background: url(https://en.wikipedia.org/css-background); } </style>
        <script>original script</script>
        <script type="module" src="main.js"></script>
        <span id="mwKJ" typeof="mw:Entity">&ndash;</span>
        </p>
        </section>"""

        parser = Parser(MwContextualizer())
        parser.init()
        parser.write(source_doc)

        data = parser.builder.doc.reduce()
        reduced_doc, extracted_data = data["reduced_doc"], data["extracted_data"]

        deep_equal(
            normalize(reduced_doc.get_html()),
            normalize(expected_reduced_doc),
            "Expanded the corrupted document by removing all externally inserted attributes.",
        )
        deep_equal(len(extracted_data.keys()), 5, "Attributes for 2 tags extracted.")
        deep_equal(not not extracted_data["2"].get("content"), True, "Content extracted for style tag")
        deep_equal(not not extracted_data["3"].get("content"), True, "Content extracted for script tag")
        deep_equal(not not extracted_data["5"].get("content"), True, "Content extracted for tag with mw:Entity")

        parser = Parser(MwContextualizer())
        parser.init()
        parser.write(corrupted_mt_input)

        expanded_doc = parser.builder.doc.expand(extracted_data)
        deep_equal(
            normalize(expanded_doc.get_html()),
            normalize(sanitized_expanded_doc),
            "Expanded the corrupted document by ignoring modified style and script content",
        )

    def test_html_compaction_roundtrip_with_template_with_empty_content(self):
        test_xhtml_file = FIXTURES_DIR / "text-inline-template-empty-content.html"
        with open(test_xhtml_file, "r", encoding="utf-8") as f:
            content_for_reduce = re.sub(r"^\s+|\s+$", "", f.read())

        parser = Parser(MwContextualizer())
        parser.init()
        parser.write(content_for_reduce)

        data = parser.builder.doc.reduce()
        reduced_doc, extracted_data = data["reduced_doc"], data["extracted_data"]

        reduced_parser = Parser(MwContextualizer())
        reduced_parser.init()
        reduced_parser.write(reduced_doc.get_html())

        deep_equal(len(extracted_data.keys()), 6, "Attributes for 6 tags extracted.")

        expanded_doc = reduced_parser.builder.doc.expand(extracted_data)
        deep_equal(
            normalize(expanded_doc.get_html()),
            normalize(content_for_reduce),
            "Restored the original html after reduce and expand.",
        )

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
