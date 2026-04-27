from __future__ import annotations
from typing import Any

from ._base import (
    BasePlaceholder, ml, split_lines, parse_kv_segments,
    resolve_aliases, split_asins,
)
from ....models import AudiobookCarouselNode


_ALIASES: dict[str, str] = {
    "title": "title",
    "subtitle": "subtitle",
    "body_copy": "body_copy",
    "copy": "body_copy",
    "description": "body_copy",
    "cta_text": "cta_text",
    "cta": "cta_text",
    "cta_url": "cta_url",
    "items_per_slide": "items_per_slide",
    "per_slide": "items_per_slide",
    "market": "market",
    "source_id": "source_id",
    "id": "source_id",
}


class CarouselPlaceholder(BasePlaceholder):
    keywords = ["carousel", "audiobook_carousel", "audiobook carousel", "asin_carousel", "asin carousel"]

    @classmethod
    def format(cls, node: AudiobookCarouselNode, **ctx) -> str:
        post_market = ctx.get("post_market")
        mp = node.children[0].marketplace if node.children else ""
        asins = ", ".join(node.asins)
        lines = [asins]
        if mp and (not post_market or mp.upper() != post_market.upper()):
            lines.append(f"market = {mp}")
        if node.title:
            lines.append(f"title = {node.title}")
        if node.subtitle:
            lines.append(f"subtitle = {node.subtitle}")
        if node.body_copy:
            lines.append(f"body-copy = {node.body_copy}")
        if node.cta_text:
            lines.append(f"cta-text = {node.cta_text}")
        if node.cta_url:
            lines.append(f"cta-url = {node.cta_url}")
        if node.items_per_slide:
            lines.append(f"items-per-slide = {node.items_per_slide}")
        if node.source_id:
            lines.append(f"id = {node.source_id}")
        return ml("Carousel", lines)

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        lines = split_lines(content)
        kv_lines = [l for l in lines if "=" in l]
        kv = parse_kv_segments(kv_lines)
        kv = resolve_aliases(kv, _ALIASES)
        asins = []
        for line in lines:
            if "=" not in line:
                asins = split_asins(line)
                break
        return {
            "type": "carousel",
            "asins": asins,
            "marketplace": kv.get("market", ""),
            "title": kv.get("title"),
            "subtitle": kv.get("subtitle"),
            "body_copy": kv.get("body_copy"),
            "cta_text": kv.get("cta_text"),
            "cta_url": kv.get("cta_url"),
            "items_per_slide": int(kv["items_per_slide"]) if kv.get("items_per_slide") else None,
            "source_id": kv.get("source_id"),
        }
