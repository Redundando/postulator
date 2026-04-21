"""Test uploading B002UZMUJW to the US blog."""

import asyncio
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from postulator import Post, ParagraphNode, TextNode, HeadingNode, AudiobookNode
from postulator.adapters.contentful import ContentfulClient

ASIN = "B002UZMUJW"
MARKETPLACE = "US"
LOCALE = "en-US"
SLUG = "test-asin-b002uzmujw"


async def main():
    post = Post(
        slug=SLUG,
        locale=LOCALE,
        title="Test ASIN Upload",
        date=datetime.now(timezone.utc),
        show_in_feed=False,
        body=[
            HeadingNode(level=2, children=[TextNode(value="Test")]),
            ParagraphNode(children=[TextNode(value="Testing ASIN upload.")]),
            AudiobookNode(asin=ASIN, marketplace=MARKETPLACE),
        ],
    )

    async with ContentfulClient(
        space_id=os.environ["CONTENTFUL_SPACE_ID"],
        environment=os.environ.get("CONTENTFUL_ENVIRONMENT", "master"),
        token=os.environ["CONTENTFUL_TOKEN"],
        on_progress=lambda e: print(f"  [{e['event']}] {e}"),
    ) as client:
        print(f"Creating post: {SLUG}")
        created = await client.create_post(post, publish=True)
        print(f"\nPublished post entry ID: {created.source_id}")


if __name__ == "__main__":
    asyncio.run(main())
