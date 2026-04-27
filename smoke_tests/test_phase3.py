"""Phase 3 smoke tests: ContentfulAdapter, pure client, handler I/O, live round-trip."""

import asyncio


def test_client_is_pure_http():
    from postulator.adapters.contentful import ContentfulClient
    public = [m for m in dir(ContentfulClient) if not m.startswith("_")]
    # Should only have low-level HTTP methods
    for method in ["get_entry", "create_entry", "update_entry", "publish_entry",
                    "delete_entry", "find_entries", "get_entries",
                    "get_asset", "get_assets", "create_asset", "process_asset",
                    "publish_asset", "upload_file", "get_content_type",
                    "create_entry_with_id"]:
        assert method in public, f"Missing: {method}"
    # Should NOT have pipeline methods
    for method in ["write_post", "create_post", "read_post", "write_asin",
                    "write_seo", "upload_local_asset"]:
        assert method not in public, f"Should not have: {method}"
    print(f"  client_is_pure_http OK ({len(public)} methods)")


def test_adapter_has_orchestration():
    from postulator.adapters.contentful import ContentfulAdapter
    for method in ["write", "update", "read", "create_author", "update_author",
                    "read_author", "list_authors", "list_tags", "find_entry_by_slug",
                    "upload_asset"]:
        assert hasattr(ContentfulAdapter, method), f"Missing: {method}"
    print("  adapter_has_orchestration OK")


def test_pipeline_deleted():
    import os
    pipeline_path = os.path.join(os.path.dirname(__file__), "..",
                                  "postulator", "adapters", "contentful", "_pipeline.py")
    assert not os.path.exists(pipeline_path), "_pipeline.py should be deleted"
    print("  pipeline_deleted OK")


def test_old_nodes_dir_deleted():
    import os
    nodes_path = os.path.join(os.path.dirname(__file__), "..",
                               "postulator", "adapters", "contentful", "nodes")
    assert not os.path.exists(nodes_path), "nodes/ directory should be deleted"
    print("  old_nodes_dir_deleted OK")


def test_handlers_have_write():
    from postulator.adapters.contentful.handlers.audiobook import AudiobookHandler
    from postulator.adapters.contentful.handlers.audiobook_list import AudiobookListHandler
    from postulator.adapters.contentful.handlers.audiobook_carousel import AudiobookCarouselHandler
    from postulator.adapters.contentful.handlers.seo import SeoHandler
    assert asyncio.iscoroutinefunction(AudiobookHandler.write)
    assert asyncio.iscoroutinefunction(AudiobookListHandler.write)
    assert asyncio.iscoroutinefunction(AudiobookCarouselHandler.write)
    assert asyncio.iscoroutinefunction(SeoHandler.write)
    assert asyncio.iscoroutinefunction(AudiobookHandler.resolve_batch)
    print("  handlers_have_write OK")


def test_assets_module():
    from postulator.adapters.contentful.assets import upload_local_asset
    assert asyncio.iscoroutinefunction(upload_local_asset)
    print("  assets_module OK")


def test_live_read():
    """Live test: read an existing post. Requires CONTENTFUL_* env vars."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    space_id = os.environ.get("CONTENTFUL_SPACE_ID")
    token = os.environ.get("CONTENTFUL_TOKEN")
    if not space_id or not token:
        print("  live_read SKIPPED (no credentials)")
        return

    from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter

    async def _run():
        async with ContentfulClient(space_id=space_id, environment="master", token=token) as client:
            adapter = ContentfulAdapter(client)
            # Read a known DE post
            post = await adapter.read("3736021139-de-post", locale="de-DE")
            assert post.source_id == "3736021139-de-post"
            assert post.title, "Expected a title"
            assert len(post.body) > 0, "Expected body nodes"
            print(f"    title: {post.title}")
            print(f"    body: {len(post.body)} nodes, types: {[n.type for n in post.body[:5]]}...")
            print(f"    authors: {[a.name for a in post.authors]}")
            print(f"    tags: {[t.name for t in post.tags]}")

    asyncio.run(_run())
    print("  live_read OK")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    print("Phase 3 smoke tests:")
    test_client_is_pure_http()
    test_adapter_has_orchestration()
    test_pipeline_deleted()
    test_old_nodes_dir_deleted()
    test_handlers_have_write()
    test_assets_module()

    if "--live" in sys.argv:
        test_live_read()
    else:
        print("  (skipping live tests — run with --live to enable)")

    print("ALL PASSED")
