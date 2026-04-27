from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .markdown import convert_inline
from .models.nodes import (
    ParagraphNode,
    TableCellNode,
    TableRowNode,
    TableNode,
)

_md = MarkdownIt().enable("table")


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
            inline_nodes = convert_inline(tok.children or [])
            cells.append(TableCellNode(
                is_header=is_header,
                children=[ParagraphNode(children=inline_nodes)] if inline_nodes else [],
            ))

    return rows


def table(md: str) -> TableNode:
    tokens = _md.parse(md.strip())
    table_tokens = [t for t in tokens if t.type not in ("table_open", "table_close")]
    return TableNode(children=_process_tokens(table_tokens))
