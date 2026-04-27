"""DOCX reading — parse a python-docx Document into metadata, body nodes, and featured image."""

from __future__ import annotations

import re
from typing import Any

from docx.oxml.ns import qn

from ...models import (
    BlockNode, InlineNode, TextNode, HyperlinkNode,
    ParagraphNode, HeadingNode, ListNode, ListItemNode,
    BlockquoteNode, HrNode, AudiobookNode, AudiobookListNode,
    AudiobookCarouselNode, ContentImageNode, EmbeddedAssetNode,
    TableNode, TableRowNode, TableCellNode, UnknownNode,
    AssetRef, LocalAsset,
)
from .placeholders import parse_placeholder, parse_asset_meta
from .assets import extract_image_from_paragraph

_HR_RE = re.compile(r"^[\u2500\-_=~]{3,}\s*$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?")
_CODE_FONTS = {"courier new", "consolas", "courier", "monospace"}

_METADATA_TYPES = {"post", "authors", "tags", "seo", "featured_image", "intro"}


class _ListItemMarker:
    def __init__(self, ordered: bool, indent: int, children: list[BlockNode]):
        self.ordered = ordered
        self.indent = indent
        self.children = children


# ------------------------------------------------------------------
# Top-level entry point
# ------------------------------------------------------------------

def parse_document(
    doc, image_dir: str | None = None,
) -> tuple[dict[str, Any], list[BlockNode], AssetRef | LocalAsset | None]:
    """Parse a python-docx Document into (metadata, body_nodes, featured_image).

    metadata keys: post, authors, tags, seo, intro, featured_image
    """
    image_index = 0
    items = _build_item_list(doc)

    metadata: dict[str, Any] = {}
    featured_image: AssetRef | LocalAsset | None = None
    body_items: list[tuple[str, Any]] = []
    featured_image_pending = False

    i = 0
    while i < len(items):
        kind, obj = items[i]

        if kind == "paragraph":
            text = obj.text.strip()

            if text.startswith("["):
                full_text, end_i = _collect_multiline(items, i)
                parsed = parse_placeholder(full_text)
                if parsed and parsed["type"] in _METADATA_TYPES:
                    ptype = parsed["type"]
                    metadata[ptype] = parsed
                    if ptype == "featured_image":
                        featured_image_pending = True
                    i = end_i + 1
                    continue
                elif parsed:
                    body_items.append(("placeholder", parsed))
                    i = end_i + 1
                    continue
                if parse_asset_meta(full_text):
                    i = end_i + 1
                    continue

            if featured_image_pending:
                img, image_index = extract_image_from_paragraph(obj, image_dir, image_index)
                if img:
                    featured_image = img
                    featured_image_pending = False
                    i += 1
                    continue
                if not text:
                    i += 1
                    continue
                featured_image_pending = False

            body_items.append(("paragraph", obj))
        elif kind == "table":
            body_items.append(("table", obj))

        i += 1

    body_nodes = _parse_body(body_items, image_dir, image_index)
    return metadata, body_nodes, featured_image


# ------------------------------------------------------------------
# Body parsing
# ------------------------------------------------------------------

def _parse_body(items: list[tuple[str, Any]], image_dir: str | None, image_index: int) -> list[BlockNode]:
    raw_nodes: list[BlockNode] = []
    post_market = ""

    for kind, obj in items:
        if kind == "placeholder":
            node = _placeholder_to_node(obj, post_market)
            if node:
                raw_nodes.append(node)
        elif kind == "table":
            raw_nodes.append(_parse_table(obj))
        elif kind == "paragraph":
            node = _parse_paragraph_node(obj, image_dir, image_index)
            if isinstance(node, tuple):
                node, image_index = node
            if node:
                raw_nodes.append(node)

    return _consolidate_lists(raw_nodes)


def _placeholder_to_node(parsed: dict, post_market: str) -> BlockNode | None:
    ptype = parsed["type"]
    if ptype == "audiobook":
        mp = parsed.get("marketplace") or post_market
        return AudiobookNode(asin=parsed["asin"], marketplace=mp)
    if ptype == "carousel":
        return AudiobookCarouselNode(
            asins=parsed["asins"], source_id=parsed.get("source_id"),
            title=parsed.get("title"), subtitle=parsed.get("subtitle"),
            body_copy=parsed.get("body_copy"), cta_text=parsed.get("cta_text"),
            cta_url=parsed.get("cta_url"), items_per_slide=parsed.get("items_per_slide"),
        )
    if ptype == "list":
        return AudiobookListNode(
            asins=parsed["asins"], source_id=parsed.get("source_id"),
            title=parsed.get("title"), label=parsed.get("label"),
            body_copy=parsed.get("body_copy"), asins_per_row=parsed.get("per_row", 1),
            descriptions=parsed.get("descriptions", "Full"),
            player_type=parsed.get("player_type", "Cover"),
        )
    if ptype == "content_image":
        return ContentImageNode(
            source_id=parsed.get("source_id"), href=parsed.get("href"),
            alignment=parsed.get("alignment"), size=parsed.get("size"),
        )
    if ptype == "unknown":
        return UnknownNode(raw=parsed.get("raw", {}))
    return None


# ------------------------------------------------------------------
# Paragraph → node
# ------------------------------------------------------------------

def _parse_paragraph_node(p, image_dir, image_index) -> BlockNode | tuple[BlockNode, int] | None:
    text = p.text.strip()
    style = p.style.name if p.style else ""

    if style.startswith("Heading"):
        level = int(style.split()[-1]) if style.split()[-1].isdigit() else 1
        return HeadingNode(level=level, children=_parse_inlines(p))

    if _HR_RE.match(text):
        return HrNode()

    if _BLOCKQUOTE_RE.match(text):
        return BlockquoteNode(children=[
            ParagraphNode(children=[TextNode(value=_BLOCKQUOTE_RE.sub("", text))])
        ])

    if "List Bullet" in style or "List Number" in style:
        ordered = "Number" in style
        indent = 0
        for suffix in ("2", "3"):
            if style.endswith(suffix):
                indent = int(suffix) - 1
        return _ListItemMarker(ordered=ordered, indent=indent,
                               children=[ParagraphNode(children=_parse_inlines(p))])

    img, image_index = extract_image_from_paragraph(p, image_dir, image_index)
    if img and not text:
        return EmbeddedAssetNode(image=img), image_index

    if not text and not _has_content(p):
        return None

    children = _parse_inlines(p)
    return ParagraphNode(children=children) if children else None


# ------------------------------------------------------------------
# Inline parsing
# ------------------------------------------------------------------

def _parse_inlines(p) -> list[InlineNode]:
    nodes: list[InlineNode] = []
    for child in p._p:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "hyperlink":
            nodes.extend(_parse_hyperlink(child, p))
        elif tag == "r":
            node = _parse_run(child)
            if node:
                nodes.append(node)
    return nodes


def _parse_run(r_elem) -> TextNode | None:
    t_elems = r_elem.findall(qn("w:t"))
    text = "".join(t.text or "" for t in t_elems)
    if not text:
        return None
    return TextNode(value=text, marks=_extract_marks(r_elem))


def _parse_hyperlink(h_elem, p) -> list[InlineNode]:
    r_id = h_elem.get(qn("r:id"))
    url = ""
    if r_id:
        try:
            url = p.part.rels[r_id].target_ref
        except (KeyError, AttributeError):
            pass
    children = [_parse_run(r) for r in h_elem.findall(qn("w:r"))]
    children = [c for c in children if c]
    if url and children:
        return [HyperlinkNode(url=url, children=children)]
    return children


def _extract_marks(r_elem) -> list[str]:
    marks = []
    rPr = r_elem.find(qn("w:rPr"))
    if rPr is None:
        return marks
    for tag, mark in [("w:b", "bold"), ("w:i", "italic")]:
        el = rPr.find(qn(tag))
        if el is not None and el.get(qn("w:val"), "true") != "0":
            marks.append(mark)
    u = rPr.find(qn("w:u"))
    if u is not None and u.get(qn("w:val"), "single") != "none":
        marks.append("underline")
    va = rPr.find(qn("w:vertAlign"))
    if va is not None:
        val = va.get(qn("w:val"), "")
        if val == "superscript":
            marks.append("superscript")
        elif val == "subscript":
            marks.append("subscript")
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is not None:
        for attr in (qn("w:ascii"), qn("w:hAnsi"), qn("w:cs")):
            if (rFonts.get(attr) or "").lower() in _CODE_FONTS:
                marks.append("code")
                break
    return marks


# ------------------------------------------------------------------
# Table parsing
# ------------------------------------------------------------------

def _parse_table(table) -> TableNode:
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            children = []
            for p in cell.paragraphs:
                inlines = _parse_inlines(p)
                if inlines:
                    children.append(ParagraphNode(children=inlines))
            is_header = any(r.bold for p in cell.paragraphs for r in p.runs if r.bold is True)
            cells.append(TableCellNode(is_header=is_header, children=children))
        rows.append(TableRowNode(children=cells))
    return TableNode(children=rows)


# ------------------------------------------------------------------
# List consolidation
# ------------------------------------------------------------------

def _consolidate_lists(nodes: list) -> list[BlockNode]:
    result: list[BlockNode] = []
    i = 0
    while i < len(nodes):
        if isinstance(nodes[i], _ListItemMarker):
            marker = nodes[i]
            ordered = marker.ordered
            items = [ListItemNode(children=marker.children)]
            i += 1
            while i < len(nodes) and isinstance(nodes[i], _ListItemMarker) and nodes[i].ordered == ordered:
                items.append(ListItemNode(children=nodes[i].children))
                i += 1
            result.append(ListNode(ordered=ordered, children=items))
        else:
            result.append(nodes[i])
            i += 1
    return result


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_item_list(doc) -> list[tuple[str, Any]]:
    items = []
    para_idx = 0
    table_idx = 0
    paragraphs = list(doc.paragraphs)
    tables = list(doc.tables)
    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        if tag == "p" and para_idx < len(paragraphs):
            items.append(("paragraph", paragraphs[para_idx]))
            para_idx += 1
        elif tag == "tbl" and table_idx < len(tables):
            items.append(("table", tables[table_idx]))
            table_idx += 1
    return items


def _collect_multiline(items: list, start: int) -> tuple[str, int]:
    text = items[start][1].text
    if "[" in text and "]" in text:
        return text, start
    for i in range(start + 1, len(items)):
        if items[i][0] != "paragraph":
            break
        line = items[i][1].text
        text += "\n" + line
        if line.strip() == "]":
            return text, i
    return text, start


def _has_content(p) -> bool:
    if p.runs:
        return True
    for child in p._p:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "hyperlink":
            return True
    return False
