import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from postulator.adapters.contentful import ContentfulClient
from postulator.nodes import AudiobookListNode

ENTRY_ID = "40MYqBvfKTwCu1RbbDUc03"


async def main() -> None:
    async with ContentfulClient(
        space_id=os.environ["CONTENTFUL_SPACE_ID"],
        environment=os.getenv("CONTENTFUL_ENVIRONMENT", "master"),
        token=os.environ["CONTENTFUL_TOKEN"],
    ) as client:
        raw = await client.get_entry(ENTRY_ID)
        from postulator.adapters.contentful._reader import _parse_embed
        node = _parse_embed(raw, {}, {}, "en-US")

    assert isinstance(node, AudiobookListNode), f"Expected AudiobookListNode, got {type(node)}"

    print(f"title        : {node.title}")
    print(f"player_type  : {node.player_type}")
    print(f"descriptions : {node.descriptions}")
    print(f"asins_per_row: {node.asins_per_row}")
    print(f"options      : {node.options}")
    print(f"asin_items   : {len(node.asin_items)}")
    for item in node.asin_items:
        print(f"\n  asin       : {item.asin}")
        print(f"  title      : {item.title}")
        print(f"  cover_url  : {item.cover_url}")
        print(f"  summary    : {(item.summary or '')[:80]}...")
        print(f"  marketplace: {item.marketplace}")
        badge = item.editor_badge or {}
        print(f"  badge      : {badge.get('badgeLabel')} / {badge.get('badgeGradient')}")


if __name__ == "__main__":
    asyncio.run(main())
