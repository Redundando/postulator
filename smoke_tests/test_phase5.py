"""Phase 5 smoke tests: cross-adapter flows."""

import asyncio
import os
from datetime import datetime, timezone


def test_docx_roundtrip_preserves_all_types():
    """Write a Post with every node type to DOCX, read back, verify."""
    from postulator import (
        Post, ParagraphNode, TextNode, HyperlinkNode, HeadingNode, HrNode,
        ListNode, ListItemNode, BlockquoteNode, AudiobookNode,
        AudiobookListNode, AudiobookCarouselNode, TableNode, TableRowNode,
        TableCellNode, AuthorRef, TagRef, SeoMeta,
    )
    from postulator.adapters.docx import DocxAdapter

    post = Post(
        source_id="cross-test-1",
        slug="cross-adapter-test",
        locale="de-DE",
        title="Cross-Adapter Test",
        date=datetime(2024, 3, 15, tzinfo=timezone.utc),
        introduction="Test introduction text.",
        body=[
            HeadingNode(level=2, children=[TextNode(value="Section")]),
            ParagraphNode(children=[
                TextNode(value="Normal. "),
                TextNode(value="Bold.", marks=["bold"]),
                TextNode(value=" "),
                TextNode(value="Italic.", marks=["italic"]),
            ]),
            ParagraphNode(children=[
                HyperlinkNode(url="https://example.com", children=[TextNode(value="A link")])
            ]),
            ListNode(ordered=False, children=[
                ListItemNode(children=[ParagraphNode(children=[TextNode(value="Bullet")])]),
            ]),
            ListNode(ordered=True, children=[
                ListItemNode(children=[ParagraphNode(children=[TextNode(value="Numbered")])]),
            ]),
            BlockquoteNode(children=[ParagraphNode(children=[TextNode(value="Quote")])]),
            HrNode(),
            TableNode(children=[
                TableRowNode(children=[
                    TableCellNode(is_header=True, children=[ParagraphNode(children=[TextNode(value="H1")])]),
                    TableCellNode(is_header=True, children=[ParagraphNode(children=[TextNode(value="H2")])]),
                ]),
                TableRowNode(children=[
                    TableCellNode(children=[ParagraphNode(children=[TextNode(value="A")])]),
                    TableCellNode(children=[ParagraphNode(children=[TextNode(value="B")])]),
                ]),
            ]),
            AudiobookNode(asin="B0D53WYQ3S", marketplace="DE"),
            AudiobookListNode(asins=["A1", "A2"], title="List Title"),
            AudiobookCarouselNode(asins=["C1", "C2", "C3", "C4"], title="Carousel"),
        ],
        authors=[AuthorRef(slug="author", locale="de-DE", name="Test Author", source_id="a1")],
        tags=[TagRef(slug="tag", locale="de-DE", name="Test Tag", source_id="t1")],
        seo=SeoMeta(meta_title="SEO Title", meta_description="SEO Desc"),
    )

    adapter = DocxAdapter()
    data = adapter.write_bytes(post)
    post2 = adapter.read_bytes(data)

    assert post2.title == "Cross-Adapter Test"
    assert post2.locale == "de-DE"
    assert post2.introduction == "Test introduction text."
    assert post2.slug == "cross-adapter-test"
    assert len(post2.authors) == 1
    assert len(post2.tags) == 1
    assert post2.seo.meta_title == "SEO Title"

    types = [n.type for n in post2.body]
    assert "heading" in types
    assert "paragraph" in types
    assert "list" in types
    assert "blockquote" in types
    assert "hr" in types
    assert "table" in types
    assert "audiobook" in types
    assert "audiobook-list" in types
    assert "audiobook-carousel" in types
    print(f"  docx_roundtrip OK ({len(post2.body)} nodes: {types})")


def test_markdown_to_post():
    """Parse markdown into generic nodes, verify structure."""
    from postulator import from_markdown

    md = """## Introduction

This is **bold** and *italic* text with a [link](https://example.com).

### Sub-section

- Bullet one
- Bullet two

1. Numbered one
2. Numbered two

> A blockquote

---

| Name | Age |
|------|-----|
| Alice | 30 |
"""
    nodes = from_markdown(md)
    types = [n.type for n in nodes]
    assert "heading" in types
    assert "paragraph" in types
    assert "list" in types
    assert "blockquote" in types
    assert "hr" in types
    assert "table" in types

    # Verify inline marks survived
    para = [n for n in nodes if n.type == "paragraph"][0]
    marks_found = set()
    for child in para.children:
        if hasattr(child, "marks"):
            marks_found.update(child.marks)
        if hasattr(child, "url"):
            marks_found.add("hyperlink")
    assert "bold" in marks_found
    assert "italic" in marks_found
    assert "hyperlink" in marks_found
    print(f"  markdown_to_post OK ({len(nodes)} nodes: {types})")


def test_markdown_to_docx():
    """Parse markdown, write to DOCX, read back."""
    from postulator import Post, from_markdown
    from postulator.adapters.docx import DocxAdapter

    nodes = from_markdown("## Hello\n\nA **bold** paragraph.\n\n- Item one\n- Item two\n\n---")
    post = Post(
        slug="md-test", locale="en-US", title="Markdown Test",
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        body=nodes,
    )

    adapter = DocxAdapter()
    data = adapter.write_bytes(post)
    post2 = adapter.read_bytes(data)

    assert post2.title == "Markdown Test"
    types = [n.type for n in post2.body]
    assert "heading" in types
    assert "paragraph" in types
    assert "list" in types
    assert "hr" in types
    print(f"  markdown_to_docx OK ({len(post2.body)} nodes)")


def test_live_contentful_read_to_docx():
    """Live: read from Contentful, write to DOCX, read back."""
    from dotenv import load_dotenv
    load_dotenv()

    space_id = os.environ.get("CONTENTFUL_SPACE_ID")
    token = os.environ.get("CONTENTFUL_TOKEN")
    if not space_id or not token:
        print("  live_contentful_read_to_docx SKIPPED (no credentials)")
        return

    from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter
    from postulator.adapters.docx import DocxAdapter

    async def _run():
        async with ContentfulClient(space_id=space_id, environment="master", token=token) as client:
            cf = ContentfulAdapter(client)
            post = await cf.read("3736021139-de-post", locale="de-DE")

        docx = DocxAdapter()
        data = docx.write_bytes(post)
        post2 = docx.read_bytes(data)

        assert post2.title == post.title
        assert post2.locale == "de-DE"
        assert len(post2.body) > 0
        print(f"    Contentful -> DOCX -> Post: {post2.title}")
        print(f"    body: {len(post.body)} -> {len(post2.body)} nodes")
        print(f"    authors: {[a.name for a in post2.authors]}")

    asyncio.run(_run())
    print("  live_contentful_read_to_docx OK")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    print("Phase 5 smoke tests:")
    test_docx_roundtrip_preserves_all_types()
    test_markdown_to_post()
    test_markdown_to_docx()

    if "--live" in sys.argv:
        test_live_contentful_read_to_docx()
    else:
        print("  (skipping live tests — run with --live to enable)")

    print("ALL PASSED")
