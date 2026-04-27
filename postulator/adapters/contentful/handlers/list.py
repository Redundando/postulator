"""Contentful ListNode handler."""

from __future__ import annotations

from ....models import ListNode, ListItemNode
from .base import ContentfulNodeHandler


class ListHandler(ContentfulNodeHandler):
    node_type = "list"

    def to_contentful(self, node: ListNode) -> dict:
        from . import block_to_contentful
        nt = "ordered-list" if node.ordered else "unordered-list"
        return {
            "nodeType": nt,
            "data": {},
            "content": [
                {"nodeType": "list-item", "data": {}, "content": [block_to_contentful(child) for child in item.children]}
                for item in node.children
            ],
        }

    def from_contentful(self, raw: dict, **context) -> ListNode:
        from . import parse_block
        raw_entries = context.get("raw_entries", {})
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        nt = raw.get("nodeType", "")
        items = [
            ListItemNode(children=[parse_block(child, raw_entries, raw_assets, locale) for child in item.get("content", [])])
            for item in raw.get("content", [])
        ]
        return ListNode(ordered=(nt == "ordered-list"), children=items)
