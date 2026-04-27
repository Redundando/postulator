from __future__ import annotations
from typing import Any

from ._base import (
    BasePlaceholder, ml, ml_flat, split_lines, parse_kv_segments, resolve_aliases,
)
from ....models import ContentImageNode


_ALIASES: dict[str, str] = {
    "href": "href",
    "link": "href",
    "url": "href",
    "alignment": "alignment",
    "align": "alignment",
    "size": "size",
    "title": "title",
    "alt": "alt",
    "source_id": "source_id",
    "id": "source_id",
}


class ContentImagePlaceholder(BasePlaceholder):
    keywords = ["content_image", "content image", "image"]

    @classmethod
    def format(cls, node: ContentImageNode, **ctx) -> str:
        lines = []
        if node.source_id:
            lines.append(f"id = {node.source_id}")
        if node.href:
            lines.append(f"href = {node.href}")
        if node.alignment:
            lines.append(f"alignment = {node.alignment}")
        if node.size:
            lines.append(f"size = {node.size}")
        if lines:
            return ml("Image", lines)
        return ml_flat("Image", "")

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        lines = split_lines(content)
        kv = parse_kv_segments(lines)
        kv = resolve_aliases(kv, _ALIASES)
        return {
            "type": "content_image",
            "source_id": kv.get("source_id"),
            "href": kv.get("href"),
            "alignment": kv.get("alignment"),
            "size": kv.get("size"),
            "title": kv.get("title"),
            "alt": kv.get("alt"),
        }
