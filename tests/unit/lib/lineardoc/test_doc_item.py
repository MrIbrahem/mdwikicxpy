"""
Unit tests for src/main_app/public/routes/html_to_segments/lib/lineardoc/doc_item.py module.

"""

from python.lib.lineardoc.doc_item import DictTag, DocDict


class TestDictTag:
    """
    Unit tests for the DictTag class.
    """

    def test_doc_dict(self):
        """
        Unit test for the DictTag class.

        """

        doc_dict = DictTag("open", {})
        # attributes = doc_dict.attributes
        attributes = doc_dict["attributes"]

        attributes["id"] = 0  # pyright: ignore[reportIndexIssue]
        assert attributes["id"] == 0  # type: ignore


class TestDocDict:
    """
    Unit tests for the DocDict class.
    """

    def test_doc_dict(self):
        """
        Unit test for the DocDict class.

        """

        doc_dict = DocDict("open", {})
        assert doc_dict is not None
