"""Read mock_article_de.docx and upload to Contentful as a draft (no publish)."""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

DOCX_PATH = os.path.join("test_output", "mock_article_de.docx")


async def main():
    space_id = os.environ.get("CONTENTFUL_SPACE_ID")
    token = os.environ.get("CONTENTFUL_TOKEN")
    if not space_id or not token:
        print("ERROR: CONTENTFUL_SPACE_ID and CONTENTFUL_TOKEN must be set")
        sys.exit(1)

    from postulator.adapters.docx import DocxAdapter
    from postulator.adapters.contentful import ContentfulClient, ContentfulAdapter
    from postulator.events import BaseEvent

    # Step 1: Read DOCX
    print(f"Reading {DOCX_PATH}...")
    docx = DocxAdapter()
    post = docx.read(DOCX_PATH)

    print(f"  Title: {post.title!r}")
    print(f"  Locale: {post.locale}")
    print(f"  Slug: {post.slug}")
    print(f"  Intro: {post.introduction[:80]!r}..." if post.introduction else "  Intro: None")
    print(f"  Authors: {[a.name for a in post.authors]}")
    print(f"  Tags: {[t.name for t in post.tags]}")
    print(f"  SEO: {post.seo.meta_title!r}" if post.seo else "  SEO: None")
    print(f"  Featured image: {type(post.featured_image).__name__}")
    print(f"  Body: {len(post.body)} nodes")
    print(f"  Types: {[n.type for n in post.body]}")

    # Step 2: Check slug availability
    events: list[BaseEvent] = []

    def on_progress(event: BaseEvent):
        events.append(event)
        print(f"  [{type(event).__name__}]")

    async with ContentfulClient(
        space_id=space_id, environment="master", token=token,
        on_progress=on_progress,
    ) as client:
        cf = ContentfulAdapter(client)

        existing = await cf.find_entry_by_slug(post.slug, post.locale)
        if existing:
            print(f"\n  WARNING: Slug {post.slug!r} already exists: {existing['sys']['id']}")
            print("  Aborting to avoid duplicates.")
            return

        # Step 3: Upload as draft (publish=False)
        print(f"\nUploading as draft...")
        created = await cf.write(post, publish=False)

        print(f"\n  Created entry: {created.source_id}")
        print(f"  Title: {created.title!r}")
        print(f"  Slug: {created.slug}")
        print(f"  Body: {len(created.body)} nodes")
        print(f"  Authors: {[a.name for a in created.authors]}")
        print(f"  Tags: {[t.name for t in created.tags]}")
        print(f"  Events: {len(events)}")

    print("\nDone! Entry created as draft.")


if __name__ == "__main__":
    asyncio.run(main())
