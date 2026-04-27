from __future__ import annotations
from typing import Any

from ._base import BasePlaceholder, ml, split_lines, parse_kv_segments, resolve_aliases
from ....models import AssetRef


_ALIASES: dict[str, str] = {
    "title": "title",
    "alt": "alt",
    "source_id": "source_id",
    "id": "source_id",
}


class FeaturedImagePlaceholder(BasePlaceholder):
    keywords = ["featured_image", "featured image", "hero_image", "hero image", "hero"]

    @classmethod
    def format(cls, asset: AssetRef | None, **ctx) -> str:
        lines = []
        if asset and asset.source_id:
            lines.append(f"source-id = {asset.source_id}")
        if asset and asset.title:
            lines.append(f"title = {asset.title}")
        if asset and asset.alt:
            lines.append(f"alt = {asset.alt}")
        return ml("Featured Image", lines) if lines else ml("Featured Image", [])

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        lines = split_lines(content)
        kv = parse_kv_segments(lines)
        kv = resolve_aliases(kv, _ALIASES)
        return {
            "type": "featured_image",
            "source_id": kv.get("source_id"),
            "title": kv.get("title"),
            "alt": kv.get("alt"),
        }
