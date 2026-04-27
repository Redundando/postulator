"""Contentful BlockquoteNode handler."""

from ....models import BlockquoteNode
from .base import ContentfulNodeHandler
from .paragraph import ParagraphHandler

_paragraph = ParagraphHandler()


class BlockquoteHandler(ContentfulNodeHandler):
    node_type = "blockquote"

    def to_contentful(self, node: BlockquoteNode) -> dict:
        return {"nodeType": "blockquote", "data": {}, "content": [_paragraph.to_contentful(p) for p in node.children]}

    def from_contentful(self, raw: dict, **context) -> BlockquoteNode:
        return BlockquoteNode(children=[
            _paragraph.from_contentful(c)
            for c in raw.get("content", [])
            if c.get("nodeType") == "paragraph"
        ])
