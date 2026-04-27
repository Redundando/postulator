"""Contentful HeadingNode handler."""

from ....models import HeadingNode
from .._inline import _inline_to_cf, _parse_inline
from .base import ContentfulNodeHandler


class HeadingHandler(ContentfulNodeHandler):
    node_type = "heading"

    def to_contentful(self, node: HeadingNode) -> dict:
        return {"nodeType": f"heading-{node.level}", "data": {}, "content": [_inline_to_cf(c) for c in node.children]}

    def from_contentful(self, raw: dict, **context) -> HeadingNode:
        level = context.get("level", 1)
        return HeadingNode(level=level, children=[_parse_inline(c) for c in raw.get("content", [])])
