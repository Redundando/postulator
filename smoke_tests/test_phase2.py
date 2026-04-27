"""Phase 2 smoke tests: adapter base, handler interface, dispatch."""


def test_base_classes():
    from postulator.adapters.base import NodeHandler
    from postulator.adapters.contentful.handlers.base import ContentfulNodeHandler
    h = ContentfulNodeHandler()
    assert isinstance(h, NodeHandler)
    print("  base_classes OK")


def test_handler_instances():
    from postulator.adapters.contentful.handlers import BLOCK_HANDLERS, EMBED_HANDLERS
    from postulator.adapters.contentful.handlers.base import ContentfulNodeHandler
    assert len(BLOCK_HANDLERS) == 12
    assert len(EMBED_HANDLERS) == 4
    for name, handler in BLOCK_HANDLERS.items():
        assert isinstance(handler, ContentfulNodeHandler), f"{name} not a ContentfulNodeHandler"
        assert handler.node_type == name, f"{handler} node_type mismatch: {handler.node_type} != {name}"
    print(f"  handler_instances OK ({len(BLOCK_HANDLERS)} block, {len(EMBED_HANDLERS)} embed)")


def test_handler_str():
    from postulator.adapters.contentful.handlers import _paragraph, _audiobook
    assert str(_paragraph) == "ParagraphHandler(paragraph)"
    assert str(_audiobook) == "AudiobookHandler(audiobook)"
    print("  handler_str OK")


def test_write_dispatch():
    from postulator import ParagraphNode, TextNode, HeadingNode, HrNode, AudiobookNode
    from postulator.adapters.contentful.handlers import block_to_contentful, body_to_contentful

    p = ParagraphNode(children=[TextNode(value="hello", marks=["bold"])])
    cf = block_to_contentful(p)
    assert cf["nodeType"] == "paragraph"
    assert cf["content"][0]["value"] == "hello"
    assert cf["content"][0]["marks"] == [{"type": "bold"}]

    h = HeadingNode(level=3, children=[TextNode(value="title")])
    cf = block_to_contentful(h)
    assert cf["nodeType"] == "heading-3"

    hr = HrNode()
    cf = block_to_contentful(hr)
    assert cf["nodeType"] == "hr"

    body = body_to_contentful([p, h, hr])
    assert body["nodeType"] == "document"
    assert len(body["content"]) == 3

    print("  write_dispatch OK")


def test_read_dispatch():
    from postulator.adapters.contentful.handlers import parse_block, parse_body

    p_raw = {"nodeType": "paragraph", "data": {}, "content": [
        {"nodeType": "text", "value": "test", "marks": [{"type": "italic"}], "data": {}}
    ]}
    p = parse_block(p_raw, {}, {}, "en-US")
    assert p.type == "paragraph"
    assert p.children[0].value == "test"
    assert "italic" in p.children[0].marks

    h_raw = {"nodeType": "heading-2", "data": {}, "content": [
        {"nodeType": "text", "value": "title", "marks": [], "data": {}}
    ]}
    h = parse_block(h_raw, {}, {}, "en-US")
    assert h.type == "heading"
    assert h.level == 2

    hr_raw = {"nodeType": "hr", "data": {}, "content": []}
    hr = parse_block(hr_raw, {}, {}, "en-US")
    assert hr.type == "hr"

    unknown_raw = {"nodeType": "something-new", "data": {}, "content": []}
    u = parse_block(unknown_raw, {}, {}, "en-US")
    assert u.type == "unknown"

    doc = {"nodeType": "document", "data": {}, "content": [p_raw, h_raw, hr_raw]}
    body = parse_body(doc, {}, {}, "en-US")
    assert len(body) == 3

    print("  read_dispatch OK")


def test_audiobook_handler():
    from postulator import AudiobookNode, AudiobookAuthor
    from postulator.adapters.contentful.handlers import _audiobook

    node = AudiobookNode(
        asin="B123", marketplace="FR",
        title="Test Book", pdp="https://example.com", cover_url="https://img.com/cover.jpg",
        authors=[AudiobookAuthor(name="Author", pdp="https://example.com/author")],
    )
    cf = _audiobook.to_contentful(node)
    assert cf["nodeType"] == "embedded-entry-block"

    fields = _audiobook.to_fields(node)
    assert fields["asin"]["en-US"] == "B123"
    assert fields["title"]["en-US"] == "Test Book"

    entry = {"sys": {"id": "e1"}, "fields": {
        "asin": {"en-US": "B456"}, "marketplace": {"en-US": "US"},
        "title": {"en-US": "Another"}, "cover": {"en-US": "https://img.com/c.jpg"},
    }}
    parsed = _audiobook.from_entry(entry, "en-US")
    assert parsed.asin == "B456"
    assert parsed.source_id == "e1"

    print("  audiobook_handler OK")


def test_post_handler():
    from datetime import datetime, timezone
    from postulator import Post, ParagraphNode, TextNode
    from postulator.adapters.contentful.handlers import _post

    post = Post(
        slug="test", locale="fr-FR", title="Test",
        date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        body=[ParagraphNode(children=[TextNode(value="hello")])],
    )
    fields = _post.to_fields(post)
    assert fields["slug"]["en-US"] == "test"
    assert fields["countryCode"]["en-US"] == "FR"
    assert fields["content"]["en-US"]["nodeType"] == "document"

    print("  post_handler OK")


def test_pipeline_imports():
    from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter
    # Client is now pure HTTP — no pipeline mixin
    assert not any("_PipelineMixin" in str(b) for b in ContentfulClient.__mro__)
    # Adapter is the orchestrator
    assert hasattr(ContentfulAdapter, "write")
    assert hasattr(ContentfulAdapter, "read")
    print("  pipeline_imports OK")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    print("Phase 2 smoke tests:")
    test_base_classes()
    test_handler_instances()
    test_handler_str()
    test_write_dispatch()
    test_read_dispatch()
    test_audiobook_handler()
    test_post_handler()
    test_pipeline_imports()
    print("ALL PASSED")
