"""Contentful handler dispatch.

Provides top-level dispatch functions for serialization and deserialization.
Handlers import block_to_contentful / parse_block from here for recursive calls.
"""

from __future__ import annotations
from typing import Any

from ....models import BlockNode, UnknownNode, EmbeddedAssetNode
from .._helpers import _parse_asset

from .paragraph import ParagraphHandler
from .heading import HeadingHandler
from .list import ListHandler
from .table import TableHandler
from .blockquote import BlockquoteHandler
from .hr import HrHandler
from .audiobook import AudiobookHandler
from .audiobook_list import AudiobookListHandler
from .audiobook_carousel import AudiobookCarouselHandler
from .content_image import ContentImageHandler
from .embedded_asset import EmbeddedAssetHandler
from .unknown import UnknownHandler
from .seo import SeoHandler
from .author import AuthorHandler
from .tag import TagHandler
from .post import PostHandler

# Handler instances
_paragraph = ParagraphHandler()
_heading = HeadingHandler()
_list = ListHandler()
_table = TableHandler()
_blockquote = BlockquoteHandler()
_hr = HrHandler()
_audiobook = AudiobookHandler()
_audiobook_list = AudiobookListHandler()
_audiobook_carousel = AudiobookCarouselHandler()
_content_image = ContentImageHandler()
_embedded_asset = EmbeddedAssetHandler()
_unknown = UnknownHandler()
_seo = SeoHandler()
_author = AuthorHandler()
_tag = TagHandler()
_post = PostHandler()

# Write dispatch: node.type → handler instance
BLOCK_HANDLERS = {
    "paragraph": _paragraph,
    "heading": _heading,
    "list": _list,
    "blockquote": _blockquote,
    "hr": _hr,
    "table": _table,
    "audiobook": _audiobook,
    "audiobook-list": _audiobook_list,
    "audiobook-carousel": _audiobook_carousel,
    "content-image": _content_image,
    "embedded-asset": _embedded_asset,
    "unknown": _unknown,
}

# Read dispatch: Contentful content type → handler instance (for embedded-entry-block)
EMBED_HANDLERS = {
    "asin": _audiobook,
    "asinsList": _audiobook_list,
    "asinsCarousel": _audiobook_carousel,
    "contentImage": _content_image,
}


def block_to_contentful(node: BlockNode) -> dict:
    """Serialize a block node to Contentful rich-text JSON."""
    handler = BLOCK_HANDLERS.get(node.type)
    if handler:
        return handler.to_contentful(node)
    raise ValueError(f"Unhandled node type: {node.type}")


def body_to_contentful(body: list[BlockNode]) -> dict:
    """Wrap body nodes in a Contentful rich-text document envelope."""
    return {"nodeType": "document", "data": {}, "content": [block_to_contentful(n) for n in body]}


def parse_block(node: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> BlockNode:
    """Deserialize a Contentful rich-text node to a generic block node."""
    nt = node.get("nodeType", "")

    if nt == "paragraph":
        return _paragraph.from_contentful(node)

    if nt.startswith("heading-"):
        level = int(nt.split("-")[1])
        return _heading.from_contentful(node, level=level)

    if nt in ("unordered-list", "ordered-list"):
        return _list.from_contentful(node, raw_entries=raw_entries, raw_assets=raw_assets, locale=locale)

    if nt == "blockquote":
        return _blockquote.from_contentful(node)

    if nt == "hr":
        return _hr.from_contentful(node)

    if nt == "table":
        return _table.from_contentful(node, raw_entries=raw_entries, raw_assets=raw_assets, locale=locale)

    if nt == "embedded-entry-block":
        entry_id = node.get("data", {}).get("target", {}).get("sys", {}).get("id")
        if entry_id and entry_id in raw_entries:
            return _parse_embed(raw_entries[entry_id], raw_entries, raw_assets, locale)
        return UnknownNode(raw=node)

    if nt == "embedded-asset-block":
        asset_id = node.get("data", {}).get("target", {}).get("sys", {}).get("id")
        result = _embedded_asset.from_contentful(node, raw_assets=raw_assets, locale=locale, asset_id=asset_id)
        return result if result else UnknownNode(raw=node)

    return UnknownNode(raw=node)


def _parse_embed(entry: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> BlockNode:
    """Dispatch embedded entry by content type."""
    sys = entry.get("sys", {})
    ct = sys.get("contentType", {}).get("sys", {}).get("id", "")

    handler = EMBED_HANDLERS.get(ct)
    if handler:
        return handler.from_contentful(entry, raw_entries=raw_entries, raw_assets=raw_assets, locale=locale)

    return UnknownNode(raw=entry)


def parse_body(richtext: dict, raw_entries: dict[str, dict], raw_assets: dict[str, dict], locale: str) -> list[BlockNode]:
    """Parse a Contentful rich-text document into body nodes."""
    return [parse_block(node, raw_entries, raw_assets, locale) for node in richtext.get("content", [])]
