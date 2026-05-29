"""Shared output formatters — CSV, JSON, markdown rendering for posts, authors, tags."""

from __future__ import annotations

import csv
import io
import json


# ---------------------------------------------------------------------------
# List formatters (generic dict lists)
# ---------------------------------------------------------------------------

def format_list_csv(items: list[dict], fieldnames: list[str] | None = None) -> str:
    """Format a list of dicts as CSV."""
    if not items:
        return ""
    fieldnames = fieldnames or list(items[0].keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        writer.writerow(item)
    return output.getvalue()


def format_list_json(items: list[dict]) -> str:
    """Format a list of dicts as JSON."""
    return json.dumps(items, indent=2, ensure_ascii=False, default=str)


def format_list_markdown(items: list[dict], fieldnames: list[str] | None = None) -> str:
    """Format a list of dicts as a markdown table."""
    if not items:
        return ""
    fieldnames = fieldnames or list(items[0].keys())
    headers = [_title_case(f) for f in fieldnames]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for item in items:
        row = [str(item.get(f, "")) for f in fieldnames]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Post markdown renderer
# ---------------------------------------------------------------------------

def format_post_markdown(post) -> str:
    """Format a full Post model as readable markdown."""
    lines = []
    lines.append(f"# {post.title}")
    lines.append("")
    lines.append(f"- **Entry ID:** {post.source_id}")
    lines.append(f"- **Slug:** {post.slug}")
    lines.append(f"- **Locale:** {post.locale}")
    lines.append(f"- **Date:** {post.date.strftime('%Y-%m-%d') if post.date else 'N/A'}")
    if post.authors:
        author_names = ", ".join(a.name or a.slug for a in post.authors)
        lines.append(f"- **Authors:** {author_names}")
    if post.tags:
        tag_names = ", ".join(t.name or t.slug for t in post.tags)
        lines.append(f"- **Tags:** {tag_names}")
    lines.append("")

    if post.introduction:
        lines.append("## Introduction")
        lines.append("")
        lines.append(post.introduction)
        lines.append("")

    lines.append("## Body")
    lines.append("")
    lines.append(_render_body(post.body))

    return "\n".join(lines)


def format_post_json(post) -> str:
    """Format a full Post model as JSON."""
    return post.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Author markdown renderer
# ---------------------------------------------------------------------------

def format_author_markdown(author) -> str:
    """Format a full Author model as readable markdown."""
    lines = []
    lines.append(f"# {author.name}")
    lines.append("")
    lines.append(f"- **Entry ID:** {author.source_id}")
    lines.append(f"- **Slug:** {author.slug}")
    if author.country_code:
        lines.append(f"- **Country:** {author.country_code}")
    if author.title:
        lines.append(f"- **Title:** {author.title}")
    lines.append("")

    if author.bio:
        lines.append("## Bio")
        lines.append("")
        lines.append(author.bio)
        lines.append("")

    return "\n".join(lines)


def format_author_json(author) -> str:
    """Format a full Author model as JSON."""
    return author.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Body node rendering
# ---------------------------------------------------------------------------

def _render_body(nodes: list) -> str:
    """Render body nodes as markdown."""
    parts = []
    for node in nodes:
        parts.append(_render_node(node))
    return "\n\n".join(parts)


def _render_node(node) -> str:
    """Render a single body node as markdown."""
    node_type = getattr(node, "type", None)

    if node_type == "heading":
        prefix = "#" * node.level
        text = _render_inline(node.children)
        return f"{prefix} {text}"

    elif node_type == "paragraph":
        return _render_inline(node.children)

    elif node_type == "list":
        items = []
        for i, item in enumerate(node.children):
            prefix = f"{i + 1}." if node.ordered else "-"
            item_text = _render_list_item(item)
            items.append(f"{prefix} {item_text}")
        return "\n".join(items)

    elif node_type == "blockquote":
        inner = "\n".join(f"> {_render_inline(p.children)}" for p in node.children)
        return inner

    elif node_type == "hr":
        return "---"

    elif node_type == "audiobook":
        title = node.title or node.asin
        return f"📖 **[{title}]** (ASIN: {node.asin}, Market: {node.marketplace})"

    elif node_type == "audiobook-list":
        asins = ", ".join(node.asins) if node.asins else "none"
        title = node.title or "Audiobook List"
        return f"📚 **{title}** — ASINs: {asins}"

    elif node_type == "audiobook-carousel":
        asins = ", ".join(node.asins) if node.asins else "none"
        title = node.title or "Audiobook Carousel"
        return f"🎠 **{title}** — ASINs: {asins}"

    elif node_type == "content-image":
        return f"🖼️ [Image: {node.image.title if node.image else 'untitled'}]"

    elif node_type == "embedded-asset":
        return f"🖼️ [Embedded Asset: {node.image.title if node.image else 'untitled'}]"

    elif node_type == "table":
        return _render_table(node)

    else:
        return f"[{node_type or 'unknown'} node]"


def _render_inline(children: list) -> str:
    """Render inline nodes as markdown."""
    parts = []
    for child in children:
        child_type = getattr(child, "type", None)
        if child_type == "text":
            text = child.value
            marks = getattr(child, "marks", [])
            if "bold" in marks:
                text = f"**{text}**"
            if "italic" in marks:
                text = f"*{text}*"
            if "code" in marks:
                text = f"`{text}`"
            parts.append(text)
        elif child_type == "hyperlink":
            link_text = _render_inline(child.children)
            parts.append(f"[{link_text}]({child.url})")
        else:
            parts.append(getattr(child, "value", ""))
    return "".join(parts)


def _render_list_item(item) -> str:
    """Render a list item's children."""
    parts = []
    for child in item.children:
        if getattr(child, "type", None) == "paragraph":
            parts.append(_render_inline(child.children))
        else:
            parts.append(_render_node(child))
    return " ".join(parts)


def _render_table(node) -> str:
    """Render a table node as markdown."""
    if not node.children:
        return "[empty table]"

    rows = []
    for row in node.children:
        cells = []
        for cell in row.children:
            cell_text = " ".join(
                _render_inline(block.children)
                for block in cell.children
                if hasattr(block, "children")
            )
            cells.append(cell_text)
        rows.append(cells)

    if not rows:
        return "[empty table]"

    lines = []
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _title_case(field_name: str) -> str:
    """Convert snake_case or kebab-case field name to Title Case."""
    return field_name.replace("_", " ").replace("-", " ").title()
