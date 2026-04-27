"""DOCX writing — build a python-docx Document from a Post model."""

from __future__ import annotations

import io
import logging

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from ...models import Post
from ...models import (
    BlockNode, InlineNode, TextNode, HyperlinkNode,
    ParagraphNode, HeadingNode, ListNode, ListItemNode,
    BlockquoteNode, HrNode, AudiobookNode, AudiobookListNode,
    AudiobookCarouselNode, ContentImageNode, EmbeddedAssetNode,
    TableNode, UnknownNode, AssetRef,
)
from .placeholders import (
    format_post_block, format_authors_block, format_tags_block,
    format_seo_block, format_audiobook, format_carousel,
    format_list_node, format_content_image, format_unknown,
    format_featured_image, locale_to_market,
)
from .placeholders._intro import IntroPlaceholder
from .assets import get_image_bytes

logger = logging.getLogger(__name__)

_PLACEHOLDER_COLOR = RGBColor(0x66, 0x66, 0x66)
_HR_TEXT = "\u2500" * 40
_CODE_FONT_NAME = "Courier New"


def build_document(post: Post, on_image_event=None) -> Document:
    """Build a python-docx Document from a Post model."""
    doc = Document()
    market = locale_to_market(post.locale)
    _write_metadata(doc, post, on_image_event)
    for node in post.body:
        _write_block(doc, node, market)
    return doc


# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------

def _write_metadata(doc: Document, post: Post, on_image_event=None) -> None:
    _add_placeholder(doc, format_post_block(post))
    if post.introduction:
        _add_placeholder(doc, IntroPlaceholder.format(post.introduction))
    if post.authors:
        _add_placeholder(doc, format_authors_block(post.authors))
    if post.tags:
        _add_placeholder(doc, format_tags_block(post.tags))
    if post.seo:
        _add_placeholder(doc, format_seo_block(post.seo))
    if post.featured_image:
        asset = post.featured_image if isinstance(post.featured_image, AssetRef) else None
        _add_placeholder(doc, format_featured_image(asset))
        image_bytes = get_image_bytes(post.featured_image)
        if image_bytes:
            if on_image_event:
                on_image_event(post.featured_image)
            _add_image(doc, image_bytes)


# ------------------------------------------------------------------
# Body nodes
# ------------------------------------------------------------------

def _write_block(doc: Document, node: BlockNode, market: str) -> None:
    if isinstance(node, ParagraphNode):
        p = doc.add_paragraph()
        _write_inlines(p, node.children)
    elif isinstance(node, HeadingNode):
        p = doc.add_heading(level=node.level)
        _write_inlines(p, node.children)
    elif isinstance(node, ListNode):
        _write_list(doc, node, market)
    elif isinstance(node, BlockquoteNode):
        for child in node.children:
            p = doc.add_paragraph()
            run = p.add_run("> ")
            run.font.color.rgb = _PLACEHOLDER_COLOR
            _write_inlines(p, child.children)
    elif isinstance(node, HrNode):
        run = doc.add_paragraph().add_run(_HR_TEXT)
        run.font.color.rgb = _PLACEHOLDER_COLOR
    elif isinstance(node, TableNode):
        _write_table(doc, node)
    elif isinstance(node, AudiobookNode):
        _add_placeholder(doc, format_audiobook(node, post_market=market))
    elif isinstance(node, AudiobookCarouselNode):
        _add_placeholder(doc, format_carousel(node, post_market=market))
    elif isinstance(node, AudiobookListNode):
        _add_placeholder(doc, format_list_node(node, post_market=market))
    elif isinstance(node, ContentImageNode):
        _add_placeholder(doc, format_content_image(node))
    elif isinstance(node, EmbeddedAssetNode):
        image_bytes = get_image_bytes(node.image)
        if image_bytes:
            _add_image(doc, image_bytes)
    elif isinstance(node, UnknownNode):
        _add_placeholder(doc, format_unknown(node))


def _write_list(doc: Document, node: ListNode, market: str, indent: int = 0) -> None:
    for item in node.children:
        for child in item.children:
            if isinstance(child, ListNode):
                _write_list(doc, child, market, indent + 1)
            elif isinstance(child, ParagraphNode):
                style = "List Number" if node.ordered else "List Bullet"
                if indent > 0:
                    style += f" {min(indent + 1, 3)}"
                p = doc.add_paragraph(style=style)
                _write_inlines(p, child.children)
            else:
                _write_block(doc, child, market)


def _write_table(doc: Document, node: TableNode) -> None:
    if not node.children:
        return
    n_cols = max(len(row.children) for row in node.children)
    table = doc.add_table(rows=0, cols=n_cols)
    table.style = "Table Grid"
    for row_node in node.children:
        row = table.add_row()
        for i, cell_node in enumerate(row_node.children):
            if i >= n_cols:
                break
            cell = row.cells[i]
            cell.paragraphs[0].clear()
            for j, block in enumerate(cell_node.children):
                if isinstance(block, ParagraphNode):
                    p = cell.paragraphs[0] if j == 0 else cell.add_paragraph()
                    _write_inlines(p, block.children)
                    if cell_node.is_header:
                        for run in p.runs:
                            run.bold = True


# ------------------------------------------------------------------
# Inlines
# ------------------------------------------------------------------

def _write_inlines(paragraph, nodes: list[InlineNode]) -> None:
    for node in nodes:
        if isinstance(node, HyperlinkNode):
            _add_hyperlink(paragraph, node)
        elif isinstance(node, TextNode):
            run = paragraph.add_run(node.value)
            if "bold" in node.marks:
                run.bold = True
            if "italic" in node.marks:
                run.italic = True
            if "underline" in node.marks:
                run.underline = True
            if "code" in node.marks:
                run.font.name = _CODE_FONT_NAME
                run.font.size = Pt(9)
            if "superscript" in node.marks:
                run.font.superscript = True
            if "subscript" in node.marks:
                run.font.subscript = True


def _add_hyperlink(paragraph, node: HyperlinkNode) -> None:
    part = paragraph.part
    r_id = part.relate_to(
        node.url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    for child in node.children:
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0563C1")
        rPr.append(color)
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)
        if "bold" in child.marks:
            rPr.append(OxmlElement("w:b"))
        if "italic" in child.marks:
            rPr.append(OxmlElement("w:i"))
        r.append(rPr)
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = child.value
        r.append(t)
        hyperlink.append(r)
    paragraph._p.append(hyperlink)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _add_placeholder(doc: Document, text: str) -> None:
    run = doc.add_paragraph().add_run(text)
    run.font.color.rgb = _PLACEHOLDER_COLOR
    run.font.size = Pt(9)


def _add_image(doc: Document, image_bytes: bytes) -> None:
    try:
        doc.add_paragraph().add_run().add_picture(io.BytesIO(image_bytes), width=Inches(5))
    except Exception as e:
        logger.warning("Failed to embed image: %s", e)
