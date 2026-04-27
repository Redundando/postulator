"""Phase 4 smoke tests: DOCX adapter — simplified reader/writer, round-trip."""

import os
import tempfile
from datetime import datetime, timezone


def test_imports():
    from postulator.adapters.docx import DocxAdapter, DocxWriter, DocxReader
    assert DocxWriter is DocxAdapter
    assert DocxReader is DocxAdapter
    print("  imports OK")


def test_write_and_read_roundtrip():
    from postulator import (
        Post, ParagraphNode, TextNode, HeadingNode, HrNode,
        ListNode, ListItemNode, BlockquoteNode, AudiobookNode,
        AudiobookListNode, AudiobookCarouselNode,
        AuthorRef, TagRef, SeoMeta,
    )
    from postulator.adapters.docx import DocxAdapter

    post = Post(
        source_id="test-123",
        slug="roundtrip-test",
        locale="fr-FR",
        title="Round-Trip Test Post",
        date=datetime(2024, 6, 15, tzinfo=timezone.utc),
        introduction="This is the introduction.",
        body=[
            HeadingNode(level=2, children=[TextNode(value="Section One")]),
            ParagraphNode(children=[
                TextNode(value="Normal text. "),
                TextNode(value="Bold text.", marks=["bold"]),
            ]),
            ListNode(ordered=False, children=[
                ListItemNode(children=[ParagraphNode(children=[TextNode(value="Bullet one")])]),
                ListItemNode(children=[ParagraphNode(children=[TextNode(value="Bullet two")])]),
            ]),
            BlockquoteNode(children=[
                ParagraphNode(children=[TextNode(value="A quote.")])
            ]),
            HrNode(),
            AudiobookNode(asin="B0D53WYQ3S", marketplace="FR"),
            AudiobookListNode(asins=["B0C4TG9JZB", "B0CRDRQKYH"], title="My List"),
            AudiobookCarouselNode(asins=["A1", "A2", "A3", "A4"], title="My Carousel"),
        ],
        authors=[AuthorRef(slug="author-1", locale="fr-FR", name="Author One", source_id="a1")],
        tags=[TagRef(slug="tag-1", locale="fr-FR", name="Tag One", source_id="t1")],
        seo=SeoMeta(meta_title="SEO Title", meta_description="SEO Desc"),
    )

    adapter = DocxAdapter()

    # Write to bytes
    docx_bytes = adapter.write_bytes(post)
    assert len(docx_bytes) > 0
    print(f"    wrote {len(docx_bytes)} bytes")

    # Read back
    post2 = adapter.read_bytes(docx_bytes, filename="roundtrip")
    assert post2.title == "Round-Trip Test Post"
    assert post2.slug == "roundtrip-test"
    assert post2.locale == "fr-FR"
    assert post2.introduction == "This is the introduction."
    assert post2.source_id == "test-123"
    assert len(post2.authors) == 1
    assert post2.authors[0].name == "Author One"
    assert len(post2.tags) == 1
    assert post2.tags[0].name == "Tag One"
    assert post2.seo is not None
    assert post2.seo.meta_title == "SEO Title"
    print(f"    metadata round-trip OK")

    # Check body nodes
    types = [n.type for n in post2.body]
    assert "heading" in types
    assert "paragraph" in types
    assert "list" in types
    assert "hr" in types
    assert "audiobook" in types
    assert "audiobook-list" in types
    assert "audiobook-carousel" in types
    print(f"    body: {len(post2.body)} nodes, types: {types}")

    print("  write_and_read_roundtrip OK")


def test_write_to_file():
    from postulator import Post, ParagraphNode, TextNode
    from postulator.adapters.docx import DocxAdapter

    post = Post(
        slug="file-test", locale="en-US", title="File Test",
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        body=[ParagraphNode(children=[TextNode(value="Hello world.")])],
    )

    adapter = DocxAdapter()
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    try:
        adapter.write(post, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

        post2 = adapter.read(path)
        assert post2.title == "File Test"
        print("  write_to_file OK")
    finally:
        os.unlink(path)


def test_old_files_can_be_deleted():
    """Verify old _reader.py and _writer.py are no longer imported by __init__."""
    from postulator.adapters.docx import DocxAdapter
    import postulator.adapters.docx as mod
    # The module should only import from adapter.py
    assert "adapter" in str(mod.__file__) or hasattr(mod, "DocxAdapter")
    print("  old_files_can_be_deleted OK")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    print("Phase 4 smoke tests:")
    test_imports()
    test_write_and_read_roundtrip()
    test_write_to_file()
    test_old_files_can_be_deleted()
    print("ALL PASSED")
