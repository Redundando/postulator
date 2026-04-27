"""Phase 1 smoke tests: enricher extraction."""

import asyncio
import inspect


def test_enricher_imports():
    from postulator.enrichers import enrich, enrich_batch, configure
    from postulator.enrichers.audible import enrich, enrich_batch, configure
    assert asyncio.iscoroutinefunction(enrich)
    assert asyncio.iscoroutinefunction(enrich_batch)
    print("  enricher_imports OK")


def test_no_model_coupling():
    """Verify enrichers/audible.py imports zero model/node classes."""
    import postulator.enrichers.audible as mod
    source = inspect.getsource(mod)
    for forbidden in ("from ..nodes", "from ..models", "AudiobookNode", "BaseNode", "BaseModel"):
        assert forbidden not in source, f"Found forbidden import: {forbidden}"
    print("  no_model_coupling OK")


def test_shim_deleted():
    import os
    shim_path = os.path.join(os.path.dirname(__file__), "..",
                              "postulator", "adapters", "scraperator.py")
    assert not os.path.exists(shim_path), "scraperator.py shim should be deleted"
    print("  shim_deleted OK")


def test_contentful_adapter_imports():
    from postulator.adapters.contentful import ContentfulClient
    print("  contentful_adapter_imports OK")


def test_live_enrich():
    """Live test: scrape a known ASIN. Requires network access."""
    from postulator.enrichers.audible import enrich

    async def _run():
        result = await enrich("B0D53WYQ3S", "FR")
        assert isinstance(result, dict)
        assert result.get("title"), "Expected title"
        assert result.get("pdp"), "Expected pdp"
        assert result.get("cover_url"), "Expected cover_url"
        assert isinstance(result.get("authors"), list)
        assert len(result["authors"]) > 0
        assert result["authors"][0].get("name"), "Expected author name"
        print(f"    title: {result['title']}")
        print(f"    authors: {[a['name'] for a in result['authors']]}")

    asyncio.run(_run())
    print("  live_enrich OK")


def test_live_enrich_batch():
    """Live test: batch-scrape 3 ASINs. Requires network access."""
    from postulator.enrichers.audible import enrich_batch

    async def _run():
        items = [
            {"asin": "B0D53WYQ3S", "marketplace": "FR"},
            {"asin": "B0C4TG9JZB", "marketplace": "FR"},
            {"asin": "B0CRDRQKYH", "marketplace": "FR"},
        ]
        results = await enrich_batch(items)
        assert len(results) == 3
        for i, r in enumerate(results):
            assert isinstance(r, dict)
            assert r.get("title"), f"Item {i} missing title"
            print(f"    [{i}] {r['title']}")

    asyncio.run(_run())
    print("  live_enrich_batch OK")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    print("Phase 1 smoke tests:")
    test_enricher_imports()
    test_no_model_coupling()
    test_shim_deleted()
    test_contentful_adapter_imports()

    if "--live" in sys.argv:
        test_live_enrich()
        test_live_enrich_batch()
    else:
        print("  (skipping live tests — run with --live to enable)")

    print("ALL PASSED")
