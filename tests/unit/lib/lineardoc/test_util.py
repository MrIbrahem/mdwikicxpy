"""
Unit tests for lineardoc/util.py module.
"""

from python.lib.lineardoc.util import get_prop


class TestGetProp:
    """Test get_prop utility function."""

    def test_get_prop_simple_dict(self):
        """Test getting property from simple dict."""
        obj = {"a": "value"}
        assert get_prop(["a"], obj) == "value"

    def test_get_prop_nested_dict(self):
        """Test getting property from nested dict."""
        obj = {"a": {"b": {"c": "value"}}}
        assert get_prop(["a", "b", "c"], obj) == "value"

    def test_get_prop_list_access(self):
        """Test accessing list elements."""
        obj = {"a": [1, 2, 3]}
        assert get_prop(["a", 0], obj) == 1
        assert get_prop(["a", 1], obj) == 2
        assert get_prop(["a", 2], obj) == 3

    def test_get_prop_mixed_access(self):
        """Test mixed dict and list access."""
        obj = {"a": {"b": [{"c": "value1"}, {"c": "value2"}]}}
        assert get_prop(["a", "b", 0, "c"], obj) == "value1"
        assert get_prop(["a", "b", 1, "c"], obj) == "value2"

    def test_get_prop_missing_key(self):
        """Test getting non-existent property."""
        obj = {"a": "value"}
        assert get_prop(["b"], obj) is None
        assert get_prop(["a", "b"], obj) is None

    def test_get_prop_out_of_bounds(self):
        """Test accessing list out of bounds."""
        obj = {"a": [1, 2, 3]}
        assert get_prop(["a", 5], obj) is None
        assert get_prop(["a", -10], obj) is None

    def test_get_prop_empty_path(self):
        """Test with empty path."""
        obj = {"a": "value"}
        assert get_prop([], obj) == obj

    def test_get_prop_none_object(self):
        """Test with None object."""
        assert get_prop(["a"], None) is None

    def test_get_prop_none_in_path(self):
        """Test when intermediate value is None."""
        obj = {"a": None}
        assert get_prop(["a", "b"], obj) is None

    def test_get_prop_string_on_list(self):
        """Test using string key on list (should return None)."""
        obj = {"a": [1, 2, 3]}
        assert get_prop(["a", "key"], obj) is None

    def test_get_prop_int_on_dict(self):
        """Test using int key on dict (should return None)."""
        obj = {"a": {"b": "value"}}
        assert get_prop(["a", 0], obj) is None

    def test_get_prop_complex_structure(self):
        """Test with complex nested structure."""
        obj = {"parts": [{"template": {"target": {"wt": "Template:Test"}}}]}
        assert get_prop(["parts", 0, "template", "target", "wt"], obj) == "Template:Test"

    def test_get_prop_boolean_values(self):
        """Test retrieving boolean values."""
        obj = {"a": True, "b": False}
        assert get_prop(["a"], obj) is True
        assert get_prop(["b"], obj) is False

    def test_get_prop_numeric_values(self):
        """Test retrieving numeric values."""
        obj = {"int": 42, "float": 3.14, "zero": 0}
        assert get_prop(["int"], obj) == 42
        assert get_prop(["float"], obj) == 3.14
        assert get_prop(["zero"], obj) == 0
