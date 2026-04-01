from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, Field


# --- Asset ---

class AssetRef(BaseModel):
    source_id: str | None = None
    url: str | None = None
    title: str | None = None
    alt: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    width: int | None = None
    height: int | None = None
    size: int | None = None


class LocalAsset(BaseModel):
    local_path: str
    title: str
    alt: str | None = None
    file_name: str | None = None
    content_type: str | None = None


# --- Inline nodes ---

class TextNode(BaseModel):
    type: Literal["text"] = "text"
    value: str
    marks: list[Literal["bold", "italic", "underline", "code", "superscript", "subscript"]] = []


class HyperlinkNode(BaseModel):
    type: Literal["hyperlink"] = "hyperlink"
    url: str
    children: list[TextNode] = []


InlineNode = TextNode | HyperlinkNode


# --- Standard block nodes ---

class ParagraphNode(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    children: list[InlineNode] = []


class HeadingNode(BaseModel):
    type: Literal["heading"] = "heading"
    level: int  # 1–6
    children: list[InlineNode] = []


class ListItemNode(BaseModel):
    type: Literal["list-item"] = "list-item"
    children: list["BlockNode"] = []


class ListNode(BaseModel):
    type: Literal["list"] = "list"
    ordered: bool = False
    children: list[ListItemNode] = []


class BlockquoteNode(BaseModel):
    type: Literal["blockquote"] = "blockquote"
    children: list[ParagraphNode] = []


class HrNode(BaseModel):
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


class AudiobookNode(BaseModel):
    """Represents an Audible product embed in a post body.

    Fields required for frontend rendering:
        - title: linked title text
        - pdp: URL for title link, cover link, and CTA button
        - cover_url: cover image source
        - authors[].name + authors[].pdp: author link text and href

    All other fields (summary, releaseDate, narrators, series, etc.) are used
    by other block types (asinsList, asinsCarousel) or for SEO/schema only.
    When creating entries via write_asin, populate at minimum the four fields
    above to ensure the block renders correctly.
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


class AudiobookListNode(BaseModel):
    type: Literal["audiobook-list"] = "audiobook-list"
    source_id: str | None = None
    asins: list[str] = []
    asin_entry_ids: list[str] = []  # raw Contentful entry IDs, preserves unresolved links
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


class AudiobookCarouselNode(BaseModel):
    type: Literal["audiobook-carousel"] = "audiobook-carousel"
    source_id: str | None = None
    asins: list[str]
    asin_entry_ids: list[str] = []  # raw Contentful entry IDs, preserves unresolved links
    children: list[AudiobookNode] = []
    items_per_slide: int | None = None
    title: str | None = None
    subtitle: str | None = None
    body_copy: str | None = None
    cta_text: str | None = None
    cta_url: str | None = None
    options: list[str] = []


class ContentImageNode(BaseModel):
    type: Literal["content-image"] = "content-image"
    source_id: str | None = None
    image: AssetRef | LocalAsset | None = None
    href: str | None = None
    alignment: str | None = None
    size: str | None = None


class TableCellNode(BaseModel):
    type: Literal["table-cell"] = "table-cell"
    is_header: bool = False
    children: list["BlockNode"] = []


class TableRowNode(BaseModel):
    type: Literal["table-row"] = "table-row"
    children: list[TableCellNode] = []


class TableNode(BaseModel):
    type: Literal["table"] = "table"
    children: list[TableRowNode] = []


class UnknownNode(BaseModel):
    type: Literal["unknown"] = "unknown"
    raw: dict


# --- Type aliases ---

BlockNode = Annotated[
    ParagraphNode | HeadingNode | ListNode | BlockquoteNode | HrNode
    | AudiobookNode | AudiobookListNode | AudiobookCarouselNode
    | ContentImageNode | TableNode | UnknownNode,
    Field(discriminator="type"),
]

DocumentNode = list[BlockNode]

ListItemNode.model_rebuild()
TableCellNode.model_rebuild()
TableRowNode.model_rebuild()
