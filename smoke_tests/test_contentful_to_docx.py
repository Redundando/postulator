"""Smoke test: read a DE Contentful article and write it to DOCX."""

import asyncio
import os

ENTRY_ID = "7o06g0WBcE5BRv9pg5m3YQ"
LOCALE = "de-DE"
OUTPUT_PATH = os.path.join("test_output", "de_7o06g0_export.docx")


def test_contentful_to_docx():
    from dotenv import load_dotenv
    load_dotenv()

    space_id = os.environ.get("CONTENTFUL_SPACE_ID")
    token = os.environ.get("CONTENTFUL_TOKEN")
    if not space_id or not token:
        print("  SKIPPED (no credentials)")
        return

    from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter
    from postulator.adapters.docx import DocxAdapter
    from postulator.events import BaseEvent

    events: list[BaseEvent] = []

    async def _run():
        async with ContentfulClient(
            space_id=space_id, environment="master", token=token,
            on_progress=events.append,
        ) as client:
            cf = ContentfulAdapter(client)
            post = await cf.read(ENTRY_ID, locale=LOCALE)

        assert post.title, "Post title should not be empty"
        assert post.locale == LOCALE
        assert len(post.body) > 0, "Post body should not be empty"

        print(f"  Read: {post.title!r}")
        print(f"  Body: {len(post.body)} nodes")
        print(f"  Authors: {[a.name for a in post.authors]}")
        print(f"  Tags: {[t.name for t in post.tags]}")
        print(f"  SEO: {post.seo.meta_title!r}" if post.seo else "  SEO: None")
        print(f"  Events: {len(events)} ({[type(e).__name__ for e in events]})")

        # Verify events are typed
        for e in events:
            assert isinstance(e, BaseEvent), f"Expected BaseEvent, got {type(e)}"

        docx = DocxAdapter()
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        docx.write(post, OUTPUT_PATH)
        print(f"  Wrote: {OUTPUT_PATH}")

        # Round-trip: read back and verify
        post2 = docx.read(OUTPUT_PATH)
        assert post2.title == post.title
        assert post2.locale == LOCALE
        assert len(post2.body) > 0
        print(f"  Round-trip: {len(post.body)} -> {len(post2.body)} nodes")

    asyncio.run(_run())
    print("  OK")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    print(f"Contentful -> DOCX ({ENTRY_ID}):")
    test_contentful_to_docx()
