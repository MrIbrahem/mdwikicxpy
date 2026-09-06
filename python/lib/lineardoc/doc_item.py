""" """

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .elements import VOID_ELEMENTS
from .text_block import TextBlock
from .utils import Utils

ITEM_TYPES_STR = Literal["open", "close"]


@dataclass
class ItemBase:
    item: Any
    item_type: Any

    def to_json(self) -> dict[str, Any]:
        # return {"item_type": self.item_type, "item": self.item}
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        # connect keys to object properties
        if key == "item_type":
            return self.item_type
        elif key == "item":
            return self.item
        else:
            raise KeyError(f"key '{key}' not found in Item")

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class DocTextBlock(ItemBase):
    item: TextBlock
    item_type: str = "textblock"

    @classmethod
    def load(cls, item_type: str, obj: TextBlock):
        return cls(item_type=item_type, item=obj)

    def generate_textblock_xml(self, pad: str = "") -> list[str]:
        dump = [f"{pad}<cxtextblock>"]
        dump.extend(self.item.dump_xml_array(pad + "  "))
        dump.append(f"{pad}</cxtextblock>")

        return dump

    def get_html(self) -> str:
        return self.item.get_html()


@dataclass
class DictTag:
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def isSelfClosing(self) -> bool:  # noqa: N802
        # Mark HTML void elements as self-closing
        return self.name in VOID_ELEMENTS

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key: str) -> str | bool | dict[str, Any]:
        # connect keys to object properties
        if key == "name":
            return self.name
        elif key == "attributes":
            return self.attributes
        else:
            raise KeyError(f"key '{key}' not found in dict tag")

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "name":
            self.name = value
        elif key == "attributes":
            self.attributes = value
        else:
            raise KeyError(f"Cannot set key '{key}': not a valid tag property")

    def clone(self) -> DictTag:
        """
        Clone a SAX open tag.
        """
        return DictTag(
            name=self.name,
            attributes=self.attributes.copy(),
        )

    def to_json(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "attributes": self.attributes,
        }
        if self.isSelfClosing:
            data["isSelfClosing"] = True
        return data

    def opening_tag(self, pad: str = "") -> str:
        return f"{pad}<{self.name}>"

    def closing_tag(self, pad: str = "") -> str:
        return f"{pad}</{self.name}>"

    def get_open_tag_html(self, sort_attrs: bool = True) -> str:
        """
        Render a SAX open tag into an HTML string.

        Args:
            sort_attrs: Sort attributes alphabetically

        Returns:
            HTML representation of open tag
        """
        html = ["<" + Utils.esc(self.name)]
        attributes = self.attributes.keys()

        # sort attributes
        if sort_attrs:
            attributes = sorted(attributes)

        for attr in attributes:
            html.append(" " + Utils.esc(attr) + '="' + Utils.esc_attr(self.attributes[attr]) + '"')

        if self.isSelfClosing:
            html.append(" /")

        html.append(">")
        return "".join(html)

    def get_close_tag_html(self) -> str:
        """
        Render a SAX close tag into an HTML string.

        Returns:
            HTML representation of close tag
        """
        if self.isSelfClosing:
            return ""
        return "</" + Utils.esc(self.name) + ">"

    def get_tag_id(self) -> str:
        """
        Get something that can identify the tag.

        For a given tag, get something that can be used to identify the tag.
        `about` attribute has more preference in our context since it connects
        template fragments. If `about` is not present, use id attribute.
        If no attributes, then it is tag name. In real wiki content, the case
        of no attributes is not found.
        """
        tag_id = None
        if self.attributes:
            tag_id = self.attributes.get("about") or self.attributes.get("id")

        return str(tag_id) if tag_id else str(self.name)


class DocDict(ItemBase):
    item_type: ITEM_TYPES_STR
    item: DictTag

    @classmethod
    def load(cls, item_type: ITEM_TYPES_STR, obj: DictTag | dict[str, Any]) -> DocDict:
        """
        Args:
            item_type: Literal["open", "close"]
            obj: Tag dict with 'name' and 'attributes'
        """
        # if isinstance(obj, DictTag): obj = obj.to_json()

        item_obj = DictTag(
            name=obj.get("name") or "",
            attributes=obj.get("attributes") or {},
        )
        return cls(item_type=item_type, item=item_obj)

    def get_html(self, sort_attrs: bool = True) -> str:
        if self.item_type == "close":
            return self.item.get_close_tag_html()

        if self.item_type == "open":
            return self.item.get_open_tag_html(sort_attrs)

        raise ValueError(f"Invalid item type: {self.item_type}")


@dataclass
class DocStr(ItemBase):
    item: str
    item_type: Literal["blockspace"] = "blockspace"

    @classmethod
    def load(cls, obj: str):
        return cls(item=obj)

    def get_html(self) -> str:
        return self.item


__all__ = [
    "DocStr",
    "DocDict",
    "DocTextBlock",
]
