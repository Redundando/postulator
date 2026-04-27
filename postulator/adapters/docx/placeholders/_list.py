from __future__ import annotations
from typing import Any

from ._base import (
    BasePlaceholder, ml, split_lines, parse_kv_segments,
    resolve_aliases, split_asins,
)
from ....models import AudiobookListNode


_ALIASES: dict[str, str] = {
    "title": "title",
    "label": "label",
    "per_row": "per_row",
    "columns": "per_row",
    "body_copy": "body_copy",
    "copy": "body_copy",
    "description": "body_copy",
    "market": "market",
    "descriptions": "descriptions",
    "player_type": "player_type",
    "source_id": "source_id",
    "id": "source_id",
}


class ListPlaceholder(BasePlaceholder):
    keywords = ["list", "audiobook_list", "audiobook list", "asin_list", "asin list"]

    @classmethod
    def format(cls, node: AudiobookListNode, **ctx) -> str:
        post_market = ctx.get("post_market")
        mp = node.children[0].marketplace if node.children else ""
        asins = ", ".join(node.asins)
        lines = [asins]
        if mp and (not post_market or mp.upper() != post_market.upper()):
            lines.append(f"market = {mp}")
        if node.title:
            lines.append(f"title = {node.title}")
        if node.label:
            lines.append(f"label = {node.label}")
        if node.body_copy:
            lines.append(f"body-copy = {node.body_copy}")
        if node.asins_per_row != 1:
            lines.append(f"per-row = {node.asins_per_row}")
        if node.descriptions != "Full":
            lines.append(f"descriptions = {node.descriptions}")
        if node.player_type != "Cover":
            lines.append(f"player-type = {node.player_type}")
        if node.source_id:
            lines.append(f"id = {node.source_id}")
        return ml("List", lines)

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
            "type": "list",
            "asins": asins,
            "marketplace": kv.get("market", ""),
            "title": kv.get("title"),
            "label": kv.get("label"),
            "body_copy": kv.get("body_copy"),
            "per_row": int(kv["per_row"]) if kv.get("per_row") else 1,
            "descriptions": kv.get("descriptions", "Full"),
            "player_type": kv.get("player_type", "Cover"),
            "source_id": kv.get("source_id"),
        }
