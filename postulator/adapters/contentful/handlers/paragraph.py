"""Contentful ParagraphNode handler."""

from ....models import ParagraphNode
from .._inline import _inline_to_cf, _parse_inline
from .base import ContentfulNodeHandler


class ParagraphHandler(ContentfulNodeHandler):
    node_type = "paragraph"

    def to_contentful(self, node: ParagraphNode) -> dict:
        return {"nodeType": "paragraph", "data": {}, "content": [_inline_to_cf(c) for c in node.children]}

    def from_contentful(self, raw: dict, **context) -> ParagraphNode:
        return ParagraphNode(children=[_parse_inline(c) for c in raw.get("content", [])])
