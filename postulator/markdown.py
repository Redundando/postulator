from __future__ import annotations

import logging
from markdown_it import MarkdownIt
from markdown_it.token import Token

from .nodes import (
    DocumentNode,
    InlineNode,
    TextNode,
    HyperlinkNode,
    ParagraphNode,
    HeadingNode,
    ListNode,
    ListItemNode,
    BlockquoteNode,
    HrNode,
    TableNode,
    TableRowNode,
    TableCellNode,
)

logger = logging.getLogger(__name__)

_md = MarkdownIt().enable("table")

MARK_MAP = {"strong": "bold", "em": "italic", "s": "underline"}


def convert_inline(children: list[Token]) -> list[InlineNode]:
    nodes: list[InlineNode] = []
    marks: list[str] = []
    link_url: str | None = None
    link_children: list[TextNode] = []

    for tok in children:
        if tok.type == "code_inline":
            text = TextNode(value=tok.content, marks=list(marks) + ["code"])
            if link_url is not None:
                link_children.append(text)
            else:
                nodes.append(text)
        elif tok.type == "text":
            text = TextNode(value=tok.content, marks=list(marks)) if marks else TextNode(value=tok.content)
            if link_url is not None:
                link_children.append(text)
            elif tok.content:
                nodes.append(text)
        elif tok.type in ("softbreak", "hardbreak"):
            t = TextNode(value="\n")
            if link_url is not None:
                link_children.append(t)
            else:
                nodes.append(t)
        elif tok.type == "html_inline":
            t = TextNode(value=tok.content, marks=list(marks)) if marks else TextNode(value=tok.content)
            if link_url is not None:
                link_children.append(t)
            else:
                nodes.append(t)
        elif tok.nesting == 1 and tok.tag == "a":
            link_url = tok.attrGet("href") or ""
            link_children = []
        elif tok.nesting == -1 and tok.tag == "a":
            nodes.append(HyperlinkNode(url=link_url or "", children=[c for c in link_children if c.value]))
            link_url = None
            link_children = []
        elif tok.nesting == 1 and tok.tag in MARK_MAP:
            marks.append(MARK_MAP[tok.tag])
        elif tok.nesting == -1 and tok.tag in MARK_MAP:
            mark = MARK_MAP[tok.tag]
            if mark in marks:
                marks.remove(mark)
        elif tok.type == "image":
            logger.warning("Markdown images are not supported — skipping")

    return nodes


def _find_close(tokens: list[Token], start: int, open_type: str, close_type: str) -> int:
    depth = 1
    i = start
    while i < len(tokens):
        if tokens[i].type == open_type:
            depth += 1
        elif tokens[i].type == close_type:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(tokens) - 1


def _process_table_tokens(tokens: list[Token]) -> TableNode:
    rows: list[TableRowNode] = []
    cells: list[TableCellNode] = []
    is_header = False
    in_thead = False

    for tok in tokens:
        if tok.type == "thead_open":
            in_thead = True
        elif tok.type == "thead_close":
            in_thead = False
        elif tok.type == "tr_open":
            cells = []
            is_header = in_thead
        elif tok.type == "tr_close":
            rows.append(TableRowNode(children=cells))
        elif tok.type in ("th_open", "td_open"):
            pass
        elif tok.type == "inline":
            inline_nodes = convert_inline(tok.children or [])
            cells.append(TableCellNode(
                is_header=is_header,
                children=[ParagraphNode(children=inline_nodes)] if inline_nodes else [],
            ))

    return TableNode(children=rows)


def _convert_blocks(tokens: list[Token]) -> DocumentNode:
    nodes: DocumentNode = []
    i = 0

    while i < len(tokens):
        tok = tokens[i]

        if tok.type == "paragraph_open":
            close = _find_close(tokens, i + 1, "paragraph_open", "paragraph_close")
            inline = next((t for t in tokens[i + 1:close] if t.type == "inline"), None)
            children = convert_inline(inline.children or []) if inline else []
            if children:
                nodes.append(ParagraphNode(children=children))
            i = close + 1

        elif tok.type == "heading_open":
            level = int(tok.tag[1])
            close = _find_close(tokens, i + 1, "heading_open", "heading_close")
            inline = next((t for t in tokens[i + 1:close] if t.type == "inline"), None)
            children = convert_inline(inline.children or []) if inline else []
            nodes.append(HeadingNode(level=level, children=children))
            i = close + 1

        elif tok.type in ("bullet_list_open", "ordered_list_open"):
            ordered = tok.type == "ordered_list_open"
            close_type = "ordered_list_close" if ordered else "bullet_list_close"
            close = _find_close(tokens, i + 1, tok.type, close_type)
            items = _convert_list_items(tokens[i + 1:close])
            nodes.append(ListNode(ordered=ordered, children=items))
            i = close + 1

        elif tok.type == "blockquote_open":
            close = _find_close(tokens, i + 1, "blockquote_open", "blockquote_close")
            inner = _convert_blocks(tokens[i + 1:close])
            nodes.append(BlockquoteNode(children=inner))
            i = close + 1

        elif tok.type == "hr":
            nodes.append(HrNode())
            i += 1

        elif tok.type in ("fence", "code_block"):
            content = tok.content.rstrip("\n")
            nodes.append(ParagraphNode(children=[TextNode(value=content, marks=["code"])]))
            i += 1

        elif tok.type == "table_open":
            close = _find_close(tokens, i + 1, "table_open", "table_close")
            nodes.append(_process_table_tokens(tokens[i + 1:close]))
            i = close + 1

        elif tok.type == "html_block":
            content = tok.content.rstrip("\n")
            if content:
                nodes.append(ParagraphNode(children=[TextNode(value=content)]))
            i += 1

        elif tok.type == "inline" and tok.children:
            for child in tok.children:
                if child.type == "image":
                    logger.warning("Markdown images are not supported — skipping")
                    break
            else:
                children = convert_inline(tok.children)
                if children:
                    nodes.append(ParagraphNode(children=children))
            i += 1

        else:
            i += 1

    return nodes


def _convert_list_items(tokens: list[Token]) -> list[ListItemNode]:
    items: list[ListItemNode] = []
    i = 0

    while i < len(tokens):
        if tokens[i].type == "list_item_open":
            close = _find_close(tokens, i + 1, "list_item_open", "list_item_close")
            children = _convert_blocks(tokens[i + 1:close])
            items.append(ListItemNode(children=children))
            i = close + 1
        else:
            i += 1

    return items


def from_markdown(text: str) -> DocumentNode:
    """Parse a markdown string into postulator body nodes."""
    if not text or not text.strip():
        return []
    tokens = _md.parse(text)
    return _convert_blocks(tokens)
