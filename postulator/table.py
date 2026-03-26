from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .nodes import (
    InlineNode,
    TextNode,
    HyperlinkNode,
    ParagraphNode,
    TableCellNode,
    TableRowNode,
    TableNode,
)

_md = MarkdownIt().enable("table")

_MARK_MAP = {"strong": "bold", "em": "italic", "s": "underline"}


def _convert_inline(children: list[Token]) -> list[InlineNode]:
    nodes: list[InlineNode] = []
    marks: list[str] = []
    link_url: str | None = None
    link_children: list[TextNode] = []

    for tok in children:
        if tok.type == "text":
            text = TextNode(value=tok.content, marks=list(marks)) if marks else TextNode(value=tok.content)
            if link_url is not None:
                link_children.append(text)
            elif tok.content:
                nodes.append(text)
        elif tok.nesting == 1 and tok.tag == "a":
            link_url = tok.attrGet("href") or ""
            link_children = []
        elif tok.nesting == -1 and tok.tag == "a":
            nodes.append(HyperlinkNode(url=link_url or "", children=link_children))
            link_url = None
            link_children = []
        elif tok.nesting == 1 and tok.tag in _MARK_MAP:
            marks.append(_MARK_MAP[tok.tag])
        elif tok.nesting == -1 and tok.tag in _MARK_MAP:
            mark = _MARK_MAP[tok.tag]
            if mark in marks:
                marks.remove(mark)
        elif tok.type == "softbreak":
            nodes.append(TextNode(value="\n"))

    return nodes


def _process_tokens(tokens: list[Token]) -> list[TableRowNode]:
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
            inline_nodes = _convert_inline(tok.children or [])
            cells.append(TableCellNode(
                is_header=is_header,
                children=[ParagraphNode(children=inline_nodes)] if inline_nodes else [],
            ))

    return rows


def table(md: str) -> TableNode:
    tokens = _md.parse(md.strip())
    table_tokens = [t for t in tokens if t.type not in ("table_open", "table_close")]
    return TableNode(children=_process_tokens(table_tokens))
