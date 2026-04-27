"""Phase 0 smoke tests: models, node registry, events, serialization, adapter imports."""

from datetime import datetime, timezone
from typing import Literal


def test_post_construction():
    from postulator import (
        Post, ParagraphNode, TextNode, HeadingNode, AudiobookNode,
        ListNode, ListItemNode, HrNode, AuthorRef, SeoMeta,
    )
    post = Post(
        slug="test", locale="fr-FR", title="Test",
        date=datetime.now(timezone.utc),
        body=[
            HeadingNode(level=2, children=[TextNode(value="Hello")]),
            ParagraphNode(children=[TextNode(value="World", marks=["bold"])]),
            AudiobookNode(asin="B0D53WYQ3S", marketplace="FR"),
            ListNode(ordered=True, children=[
                ListItemNode(children=[ParagraphNode(children=[TextNode(value="Item 1")])])
            ]),
            HrNode(),
        ],
        authors=[AuthorRef(slug="a", locale="fr-FR", name="A")],
        seo=SeoMeta(meta_title="Test SEO"),
    )
    assert len(post.body) == 5
    assert post.body[0].type == "heading"
    assert post.body[2].type == "audiobook"
    print("  post_construction OK")


def test_round_trip():
    from postulator import Post, ParagraphNode, TextNode, HeadingNode, AudiobookNode, HrNode
    post = Post(
        slug="rt", locale="en-US", title="RT",
        date=datetime.now(timezone.utc),
        body=[
            HeadingNode(level=1, children=[TextNode(value="Title")]),
            ParagraphNode(children=[TextNode(value="Body")]),
            AudiobookNode(asin="X123", marketplace="US"),
            HrNode(),
        ],
    )
    data = post.model_dump()
    post2 = Post.model_validate(data)
    assert len(post2.body) == 4
    assert [n.type for n in post2.body] == ["heading", "paragraph", "audiobook", "hr"]
    print("  round_trip OK")


def test_registry_builtins():
    from postulator.models.nodes import get_node_class, _NODE_REGISTRY, ParagraphNode, HeadingNode
    assert get_node_class("paragraph") is ParagraphNode
    assert get_node_class("heading") is HeadingNode
    assert get_node_class("nonexistent") is None
    assert len(_NODE_REGISTRY) >= 17
    print(f"  registry_builtins OK ({len(_NODE_REGISTRY)} types)")


def test_registry_custom_node():
    from postulator.models.nodes import BaseNode, register_node, get_node_class
    class PodcastNode(BaseNode):
        type: Literal["podcast"] = "podcast"
        url: str
    register_node("podcast", PodcastNode)
    assert get_node_class("podcast") is PodcastNode
    print("  registry_custom_node OK")


def test_events():
    from postulator.events import (
        BaseEvent, WritingAsinEvent, RequestFailedEvent,
        UploadingAssetEvent, CreatingPostEvent,
    )
    e = WritingAsinEvent(asin="B0D53WYQ3S", marketplace="FR")
    assert isinstance(e, BaseEvent)
    assert e.asin == "B0D53WYQ3S"
    assert e.ts > 0
    print("  events OK")


def test_adapter_imports():
    from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter
    from postulator.adapters.docx import DocxAdapter
    from postulator.enrichers import enrich, enrich_batch
    print("  adapter_imports OK")


def test_table_and_markdown():
    from postulator import table, from_markdown
    t = table("| A | B |\n|---|---|\n| 1 | 2 |")
    assert t.type == "table"
    nodes = from_markdown("## Hello\n\nWorld")
    assert len(nodes) == 2
    print("  table_and_markdown OK")


def test_cli_models():
    from postulator.cli import _collect_models
    schemas = _collect_models()
    assert len(schemas) >= 20
    print(f"  cli_models OK ({len(schemas)} schemas)")


def test_canonical_imports():
    from postulator.models import Post, AuthorRef, TagRef, SeoMeta
    from postulator.models.nodes import ParagraphNode, AudiobookNode, BlockNode, DocumentNode
    from postulator.models.assets import AssetRef, LocalAsset
    print("  canonical_imports OK")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    print("Phase 0 smoke tests:")
    test_post_construction()
    test_round_trip()
    test_registry_builtins()
    test_registry_custom_node()
    test_events()
    test_adapter_imports()
    test_table_and_markdown()
    test_cli_models()
    test_canonical_imports()
    print("ALL PASSED")
