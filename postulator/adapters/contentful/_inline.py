"""Contentful inline node serialization and deserialization."""

from __future__ import annotations

from ...models import InlineNode, TextNode, HyperlinkNode


# ---------------------------------------------------------------------------
# Write: InlineNode → Contentful rich-text
# ---------------------------------------------------------------------------

def _inline_to_cf(node: InlineNode) -> dict:
    if isinstance(node, HyperlinkNode):
        return {
            "nodeType": "hyperlink",
            "data": {"uri": node.url},
            "content": [_inline_to_cf(c) for c in node.children],
        }
    return {
        "nodeType": "text",
        "value": node.value,
        "marks": [{"type": m} for m in node.marks],
        "data": {},
    }


# ---------------------------------------------------------------------------
# Read: Contentful rich-text → InlineNode
# ---------------------------------------------------------------------------

def _parse_inline(node: dict) -> InlineNode:
    nt = node.get("nodeType", "")
    if nt == "hyperlink":
        url = node.get("data", {}).get("uri", "")
        children = [_parse_inline(c) for c in node.get("content", []) if c.get("nodeType") == "text"]
        return HyperlinkNode(url=url, children=children)
    value = node.get("value", "")
    marks = [m["type"] for m in node.get("marks", []) if m.get("type") in ("bold", "italic", "underline", "code", "superscript", "subscript")]
    return TextNode(value=value, marks=marks)
