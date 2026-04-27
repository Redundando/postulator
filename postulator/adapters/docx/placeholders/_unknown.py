from __future__ import annotations

import json
from typing import Any

from ._base import BasePlaceholder, ml_flat
from ....models import UnknownNode


class UnknownPlaceholder(BasePlaceholder):
    keywords = ["unknown"]

    @classmethod
    def format(cls, node: UnknownNode, **ctx) -> str:
        return ml_flat("UNKNOWN", json.dumps(node.raw, ensure_ascii=False))

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        try:
            raw = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            raw = {"_raw_text": content}
        return {"type": "unknown", "raw": raw}
