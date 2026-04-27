from __future__ import annotations
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field, model_validator, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .assets import AssetRef, LocalAsset


# --- Node registry ---

_NODE_REGISTRY: dict[str, type["BaseNode"]] = {}


def register_node(type_key: str, node_class: type["BaseNode"]):
    """Register a node type. The class must have a 'type' field matching type_key."""
    _NODE_REGISTRY[type_key] = node_class


def get_node_class(type_key: str) -> type["BaseNode"] | None:
    return _NODE_REGISTRY.get(type_key)


# --- Base node ---

class BaseNode(BaseModel):
    type: str


# --- Inline nodes ---

class TextNode(BaseNode):
    type: Literal["text"] = "text"
    value: str
    marks: list[Literal["bold", "italic", "underline", "code", "superscript", "subscript"]] = []


class HyperlinkNode(BaseNode):
    type: Literal["hyperlink"] = "hyperlink"
    url: str
    children: list[TextNode] = []


InlineNode = TextNode | HyperlinkNode


# --- Standard block nodes ---

class ParagraphNode(BaseNode):
    type: Literal["paragraph"] = "paragraph"
    children: list[InlineNode] = []


class HeadingNode(BaseNode):
    type: Literal["heading"] = "heading"
    level: int  # 1–6
    children: list[InlineNode] = []


class ListItemNode(BaseNode):
    type: Literal["list-item"] = "list-item"
    children: list["BlockNode"] = []


class ListNode(BaseNode):
    type: Literal["list"] = "list"
    ordered: bool = False
    children: list[ListItemNode] = []


class BlockquoteNode(BaseNode):
    type: Literal["blockquote"] = "blockquote"
    children: list[ParagraphNode] = []


class HrNode(BaseNode):
    type: Literal["hr"] = "hr"


# --- Embed block nodes ---

class AudiobookAuthor(BaseModel):
    name: str
    asin: str | None = None
    pdp: str | None = None


class AudiobookNarrator(BaseModel):
    name: str


class AudiobookSeries(BaseModel):
    title: str
    asin: str | None = None
    sequence: str | None = None
    pdp: str | None = None
    url: str | None = None


class AudiobookNode(BaseNode):
    """Represents an Audible product embed in a post body.

    Fields required for frontend rendering:
        - title: linked title text
        - pdp: URL for title link, cover link, and CTA button
        - cover_url: cover image source
        - authors[].name + authors[].pdp: author link text and href

    All other fields (summary, releaseDate, narrators, series, etc.) are used
    by other block types (asinsList, asinsCarousel) or for SEO/schema only.
    """
    type: Literal["audiobook"] = "audiobook"
    asin: str
    marketplace: str
    source_id: str | None = None
    title: str | None = None
    cover_url: str | None = None
    summary: str | None = None
    label: str | None = None
    pdp: str | None = None
    release_date: str | None = None
    authors: list[AudiobookAuthor] = []
    narrators: list[AudiobookNarrator] = []
    series: list[AudiobookSeries] = []


class AudiobookListItem(BaseModel):
    """An annotated ASIN entry within an asinDescriptions list."""
    key: str
    asin: str
    marketplace: str
    title: str | None = None
    cover_url: str | None = None
    summary: str | None = None
    editor_badge: dict | None = None


class AudiobookListNode(BaseNode):
    type: Literal["audiobook-list"] = "audiobook-list"
    source_id: str | None = None
    asins: list[str] = []
    asin_entry_ids: list[str] = []
    asin_items: list[AudiobookListItem] = []
    children: list[AudiobookNode] = []
    title: str | None = None
    label: str | None = None
    body_copy: str | None = None
    player_type: str = "Cover"
    asins_per_row: int = 1
    descriptions: str = "Full"
    filters: list[str] | None = None
    options: list[str] = []


class AudiobookCarouselNode(BaseNode):
    type: Literal["audiobook-carousel"] = "audiobook-carousel"
    source_id: str | None = None
    asins: list[str]
    asin_entry_ids: list[str] = []
    children: list[AudiobookNode] = []
    items_per_slide: int | None = None
    title: str | None = None
    subtitle: str | None = None
    body_copy: str | None = None
    cta_text: str | None = None
    cta_url: str | None = None
    options: list[str] = []


class ContentImageNode(BaseNode):
    type: Literal["content-image"] = "content-image"
    source_id: str | None = None
    image: AssetRef | LocalAsset | None = None
    href: str | None = None
    alignment: str | None = None
    size: str | None = None


class TableCellNode(BaseNode):
    type: Literal["table-cell"] = "table-cell"
    is_header: bool = False
    children: list["BlockNode"] = []

    @model_validator(mode="after")
    def _ensure_non_empty(self) -> TableCellNode:
        if not self.children:
            self.children = [ParagraphNode(children=[TextNode(value="")])]
        return self


class TableRowNode(BaseNode):
    type: Literal["table-row"] = "table-row"
    children: list[TableCellNode] = []


class TableNode(BaseNode):
    type: Literal["table"] = "table"
    children: list[TableRowNode] = []


class EmbeddedAssetNode(BaseNode):
    type: Literal["embedded-asset"] = "embedded-asset"
    image: AssetRef | LocalAsset


class UnknownNode(BaseNode):
    type: Literal["unknown"] = "unknown"
    raw: dict


# --- Block-level node type keys (for BlockNode union) ---

_BLOCK_NODE_TYPES = {
    "paragraph", "heading", "list", "blockquote", "hr",
    "audiobook", "audiobook-list", "audiobook-carousel",
    "content-image", "table", "embedded-asset", "unknown",
}

# --- Register built-in nodes ---

_BUILTIN_NODES = {
    "text": TextNode,
    "hyperlink": HyperlinkNode,
    "paragraph": ParagraphNode,
    "heading": HeadingNode,
    "list-item": ListItemNode,
    "list": ListNode,
    "blockquote": BlockquoteNode,
    "hr": HrNode,
    "audiobook": AudiobookNode,
    "audiobook-list": AudiobookListNode,
    "audiobook-carousel": AudiobookCarouselNode,
    "content-image": ContentImageNode,
    "table-cell": TableCellNode,
    "table-row": TableRowNode,
    "table": TableNode,
    "embedded-asset": EmbeddedAssetNode,
    "unknown": UnknownNode,
}

for _key, _cls in _BUILTIN_NODES.items():
    register_node(_key, _cls)


# --- BlockNode: registry-based deserialization ---

def _deserialize_block_node(data: Any) -> BaseNode:
    """Deserialize a block node using the registry. Falls back to UnknownNode."""
    if isinstance(data, BaseNode):
        return data
    if isinstance(data, dict):
        type_key = data.get("type", "")
        cls = get_node_class(type_key)
        if cls:
            return cls.model_validate(data)
        return UnknownNode(raw=data)
    raise ValueError(f"Cannot deserialize block node from {type(data)}")


class _BlockNodeAnnotation:
    """Custom Pydantic type that uses the node registry for deserialization."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            _deserialize_block_node,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.model_dump() if isinstance(v, BaseModel) else v,
                info_arg=False,
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            "type": "object",
            "required": ["type"],
            "properties": {"type": {"type": "string", "enum": sorted(_BLOCK_NODE_TYPES)}},
            "description": "A block node discriminated by the 'type' field.",
        }


BlockNode = Annotated[BaseNode, _BlockNodeAnnotation]

DocumentNode = list[BlockNode]


# --- Rebuild forward refs ---

ListItemNode.model_rebuild()
TableCellNode.model_rebuild()
TableRowNode.model_rebuild()
