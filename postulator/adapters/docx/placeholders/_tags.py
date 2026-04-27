from __future__ import annotations
from typing import Any

from ._base import BasePlaceholder, ml, ml_flat, split_lines, parse_item_line
from ....models import TagRef


class TagsPlaceholder(BasePlaceholder):
    keywords = ["tag", "tags"]

    @classmethod
    def format(cls, tags: list[TagRef], **ctx) -> str:
        if len(tags) == 1:
            t = tags[0]
            content = t.name
            if t.source_id:
                content += f", id={t.source_id}"
            return ml_flat("Tags", content)
        lines = []
        for t in tags:
            line = t.name
            if t.source_id:
                line += f", id={t.source_id}"
            lines.append(line)
        return ml("Tags", lines)

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        tags = []
        for line in split_lines(content):
            parsed = parse_item_line(line)
            name = parsed.get("_value", "").strip()
            if name:
                tags.append({"name": name, "source_id": parsed.get("id")})
        return {"type": "tags", "tags": tags}
