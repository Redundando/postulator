"""Contentful TableNode handler."""

from __future__ import annotations

from ....models import TableNode, TableRowNode, TableCellNode
from .base import ContentfulNodeHandler


class TableHandler(ContentfulNodeHandler):
    node_type = "table"

    def to_contentful(self, node: TableNode) -> dict:
        from . import block_to_contentful
        return {
            "nodeType": "table",
            "data": {},
            "content": [
                {
                    "nodeType": "table-row",
                    "data": {},
                    "content": [
                        {
                            "nodeType": "table-header-cell" if cell.is_header else "table-cell",
                            "data": {},
                            "content": [block_to_contentful(child) for child in cell.children],
                        }
                        for cell in row.children
                    ],
                }
                for row in node.children
            ],
        }

    def from_contentful(self, raw: dict, **context) -> TableNode:
        from . import parse_block
        raw_entries = context.get("raw_entries", {})
        raw_assets = context.get("raw_assets", {})
        locale = context.get("locale", "en-US")
        rows = [
            TableRowNode(children=[
                TableCellNode(
                    is_header=(cell.get("nodeType") == "table-header-cell"),
                    children=[parse_block(child, raw_entries, raw_assets, locale) for child in cell.get("content", [])],
                )
                for cell in row.get("content", [])
            ])
            for row in raw.get("content", [])
        ]
        return TableNode(children=rows)
