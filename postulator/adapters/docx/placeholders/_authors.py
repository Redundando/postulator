from __future__ import annotations
from typing import Any

from ._base import BasePlaceholder, ml, ml_flat, split_lines, parse_item_line
from ....models import AuthorRef


class AuthorsPlaceholder(BasePlaceholder):
    keywords = ["author", "authors"]

    @classmethod
    def format(cls, authors: list[AuthorRef], **ctx) -> str:
        if len(authors) == 1:
            a = authors[0]
            content = a.name
            if a.source_id:
                content += f", id={a.source_id}"
            return ml_flat("Authors", content)
        lines = []
        for a in authors:
            line = a.name
            if a.source_id:
                line += f", id={a.source_id}"
            lines.append(line)
        return ml("Authors", lines)

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        authors = []
        for line in split_lines(content):
            parsed = parse_item_line(line)
            name = parsed.get("_value", "").strip()
            if name:
                authors.append({"name": name, "source_id": parsed.get("id")})
        return {"type": "authors", "authors": authors}
