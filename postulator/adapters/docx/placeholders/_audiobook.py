from __future__ import annotations
from typing import Any

from ._base import BasePlaceholder, ml_flat, parse_item_line
from ....models import AudiobookNode


class AudiobookPlaceholder(BasePlaceholder):
    keywords = ["audiobook", "asin"]

    @classmethod
    def format(cls, node: AudiobookNode, **ctx) -> str:
        post_market = ctx.get("post_market")
        if post_market and node.marketplace.upper() == post_market.upper():
            return ml_flat("ASIN", node.asin)
        return ml_flat("ASIN", f"{node.asin}, market={node.marketplace}")

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        parsed = parse_item_line(content.strip())
        asin = parsed.get("_value", "").strip()
        marketplace = parsed.get("market", "")
        return {
            "type": "audiobook",
            "asin": asin,
            "marketplace": marketplace,
        }
